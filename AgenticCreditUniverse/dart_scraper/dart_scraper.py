#!/usr/bin/env python3
"""
DART OpenAPI scraper.

Given a Korean listed-company name (or corp_code), find the most recent
periodic report (사업/반기/분기보고서) on DART, download the original
document bundle, and extract the "사업의 내용" section and the "연결재무제표 주석"
(falling back to "재무제표 주석") section.

Outputs written to the chosen outdir:
  - metadata.json
  - business_section.html / business_section.txt
  - notes_section.html   / notes_section.txt
  - raw/document.zip     (original DART document zip)
  - raw/<member>.xml     (each extracted member of the zip)

Usage:
  python dart_scraper.py --name "SK하이닉스"
  python dart_scraper.py --corp-code 00164779 --report-type A001

Requires:
  DART_API_KEY in environment or .env file.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import random
import re
import sys
import time
import unicodedata
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional, Sequence

import requests
from lxml import etree

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    def load_dotenv(*_a, **_kw):
        return False


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DART_BASE = "https://opendart.fss.or.kr/api"
CORP_CODE_URL = f"{DART_BASE}/corpCode.xml"
LIST_URL = f"{DART_BASE}/list.json"
DOCUMENT_URL = f"{DART_BASE}/document.xml"

# Periodic-report subtypes
PERIODIC_TYPES: dict[str, str] = {
    "A001": "사업보고서",
    "A002": "반기보고서",
    "A003": "1분기보고서",
    "A004": "3분기보고서",
}

# Preference order when report_type == "any":
#   annual (사업보고서) > half (반기) > Q3 > Q1
#   ... but overall we pick by most-recent rcept_dt; ties broken by this order.
REPORT_TYPE_RANK = {"A001": 4, "A002": 3, "A004": 2, "A003": 1}

# Section patterns ------------------------------------------------------------
# Titles in DART documents look like "Ⅱ. 사업의 내용", "II. 사업의 내용",
# "5. 연결재무제표 주석", "재무제표에 대한 주석" etc.  Patterns search anywhere
# in the title text (after normalising whitespace).

BUSINESS_SECTION_PATTERN = re.compile(r"사업의\s*내용")

# Consolidated notes: "연결재무제표 주석" or "연결재무제표에 대한 주석"
CONSOLIDATED_NOTES_PATTERN = re.compile(r"연결재무제표(?:에\s*대한)?\s*주석")

# Standalone notes: "재무제표 주석" but NOT preceded by "연결".
# We'll use a post-filter instead of a lookbehind so that both narrow
# (financial-statements notes) and wider (just "주석") cases are handled.
STANDALONE_NOTES_PATTERN = re.compile(r"재무제표(?:에\s*대한)?\s*주석")

# Cache for corpCode.xml (24h)
DEFAULT_CACHE_DIR = Path.home() / ".cache"
CACHE_FILE = DEFAULT_CACHE_DIR / "dart_corp_codes.json"
CACHE_MAX_AGE = timedelta(hours=24)

USER_AGENT = "dart-scraper/1.0 (+https://github.com/user/dart-scraper)"

logger = logging.getLogger("dart_scraper")


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------

@dataclass
class Corp:
    corp_code: str
    corp_name: str
    corp_eng_name: str
    stock_code: str
    modify_date: str

    @property
    def is_listed(self) -> bool:
        return bool((self.stock_code or "").strip())


@dataclass
class Report:
    corp_code: str
    corp_name: str
    report_nm: str
    rcept_no: str
    rcept_dt: str  # YYYYMMDD
    pblntf_detail_ty: str

    @property
    def rcept_date(self) -> datetime:
        return datetime.strptime(self.rcept_dt, "%Y%m%d")


# -----------------------------------------------------------------------------
# HTTP client with retry / rate-limit
# -----------------------------------------------------------------------------

class DartApiError(RuntimeError):
    pass


class DartClient:
    """Thin wrapper over DART endpoints with retries and throttling."""

    def __init__(
        self,
        api_key: str,
        *,
        user_agent: str = USER_AGENT,
        min_delay: float = 0.5,
        max_delay: float = 1.0,
        max_retries: int = 4,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key:
            raise DartApiError(
                "DART_API_KEY not configured. "
                "Sign up at https://opendart.fss.or.kr/ and set DART_API_KEY "
                "in your environment or .env file."
            )
        self.api_key = api_key
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    # ------------------------------------------------------------------ utils
    def _sleep(self) -> None:
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _get(self, url: str, params: dict, *, binary: bool = False):
        params = {"crtfc_key": self.api_key, **params}
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    self._sleep()
                    return resp.content if binary else resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt + random.random()
                    logger.warning(
                        "DART %s returned %s; retrying in %.1fs",
                        url, resp.status_code, wait,
                    )
                    time.sleep(wait)
                    continue
                raise DartApiError(
                    f"DART API {url} returned HTTP {resp.status_code}: "
                    f"{resp.text[:200]}"
                )
            except requests.RequestException as e:
                last_exc = e
                wait = 2 ** attempt + random.random()
                logger.warning("DART request error (%s); retry in %.1fs", e, wait)
                time.sleep(wait)
        raise DartApiError(
            f"Exhausted retries for {url}: {last_exc}"
        )

    # --------------------------------------------------------------- endpoints
    def fetch_corp_codes_zip(self) -> bytes:
        return self._get(CORP_CODE_URL, {}, binary=True)

    def fetch_list(
        self,
        corp_code: str,
        *,
        bgn_de: str,
        end_de: str,
        pblntf_ty: str = "A",  # 정기공시
        pblntf_detail_ty: Optional[str] = None,
        page_no: int = 1,
        page_count: int = 100,
    ) -> dict:
        params = {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "pblntf_ty": pblntf_ty,
            "page_no": page_no,
            "page_count": page_count,
        }
        if pblntf_detail_ty:
            params["pblntf_detail_ty"] = pblntf_detail_ty
        resp = self._get(LIST_URL, params)
        data = resp.json()
        status = data.get("status")
        # 000 = OK, 013 = 조회된 데이터가 없음(treated as empty list)
        if status not in ("000", "013"):
            raise DartApiError(
                f"DART list.json status={status} message={data.get('message')}"
            )
        if status == "013":
            data["list"] = []
        return data

    def fetch_document_zip(self, rcept_no: str) -> bytes:
        return self._get(DOCUMENT_URL, {"rcept_no": rcept_no}, binary=True)


# -----------------------------------------------------------------------------
# corpCode parsing + cache
# -----------------------------------------------------------------------------

def parse_corp_codes(xml_bytes: bytes) -> list[Corp]:
    """Parse the CORPCODE.xml body into a list of Corp objects."""
    # Recover from any minor malformation; DART is usually clean.
    parser = etree.XMLParser(recover=True, huge_tree=True)
    root = etree.fromstring(xml_bytes, parser=parser)
    corps: list[Corp] = []
    for node in root.findall("list"):
        corps.append(
            Corp(
                corp_code=(node.findtext("corp_code") or "").strip(),
                corp_name=(node.findtext("corp_name") or "").strip(),
                corp_eng_name=(node.findtext("corp_eng_name") or "").strip(),
                stock_code=(node.findtext("stock_code") or "").strip(),
                modify_date=(node.findtext("modify_date") or "").strip(),
            )
        )
    return corps


def extract_corpcode_xml(zip_bytes: bytes) -> bytes:
    """The corpCode endpoint returns a zip containing CORPCODE.xml."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Filename is usually CORPCODE.xml; fall back to first .xml member.
        for name in zf.namelist():
            if name.lower().endswith(".xml"):
                with zf.open(name) as f:
                    return f.read()
    raise DartApiError("corpCode zip did not contain an XML file")


def _normalise_name(s: str) -> str:
    """Lowercase + strip whitespace + NFKC for robust name matching."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"\s+", "", s)
    return s.casefold()


def search_corps(corps: Iterable[Corp], name: str) -> list[Corp]:
    """Exact match first; otherwise substring match. Listed first."""
    target = _normalise_name(name)
    if not target:
        return []
    exact: list[Corp] = []
    partial: list[Corp] = []
    for c in corps:
        n = _normalise_name(c.corp_name)
        en = _normalise_name(c.corp_eng_name)
        if n == target or en == target:
            exact.append(c)
        elif target in n or target in en:
            partial.append(c)
    hits = exact or partial

    def sort_key(c: Corp):
        # Listed corps first; then shorter (closer) name; then corp_code.
        return (0 if c.is_listed else 1, len(c.corp_name), c.corp_code)

    return sorted(hits, key=sort_key)


def load_cached_corp_codes(
    cache_path: Path = CACHE_FILE,
    max_age: timedelta = CACHE_MAX_AGE,
) -> Optional[list[Corp]]:
    if not cache_path.exists():
        return None
    age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
    if age > max_age:
        return None
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        return [Corp(**row) for row in raw]
    except Exception as e:  # pragma: no cover
        logger.warning("Cache read failed (%s); ignoring.", e)
        return None


def save_cached_corp_codes(corps: Sequence[Corp], cache_path: Path = CACHE_FILE) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps([asdict(c) for c in corps], ensure_ascii=False),
        encoding="utf-8",
    )


# -----------------------------------------------------------------------------
# Report selection
# -----------------------------------------------------------------------------

def parse_reports(list_items: Iterable[dict]) -> list[Report]:
    out: list[Report] = []
    for item in list_items:
        try:
            out.append(
                Report(
                    corp_code=item.get("corp_code", ""),
                    corp_name=item.get("corp_name", ""),
                    report_nm=item.get("report_nm", ""),
                    rcept_no=item.get("rcept_no", ""),
                    rcept_dt=item.get("rcept_dt", ""),
                    pblntf_detail_ty=item.get("pblntf_detail_ty", ""),
                )
            )
        except Exception:
            continue
    return out


def filter_periodic(reports: Iterable[Report]) -> list[Report]:
    """정기보고서 필터.

    - DART list API 응답에 `pblntf_detail_ty` 가 결측인 경우가 있어 (2026-04 관찰),
      `report_nm` 패턴으로 보강 분류한다 (사업/반기/분기보고서).
    - 정정 보고서(`[기재정정]`/`[첨부정정]`/`[정정]`)는 본문 zip 누락으로 BadZipFile
      을 자주 유발하므로 사전 제외한다.
    """
    import re as _re
    keep: list[Report] = []
    for r in reports:
        nm = r.report_nm or ""
        if any(t in nm for t in ("[기재정정]", "[첨부정정]", "[정정]")):
            continue
        if r.pblntf_detail_ty in PERIODIC_TYPES:
            keep.append(r)
            continue
        if "사업보고서" in nm:
            r.pblntf_detail_ty = "A001"
            keep.append(r)
        elif "반기보고서" in nm:
            r.pblntf_detail_ty = "A002"
            keep.append(r)
        elif "분기보고서" in nm:
            m = _re.search(r"\((\d{4})\.(\d{2})\)", nm)
            r.pblntf_detail_ty = "A003" if (m and m.group(2) == "03") else "A004"
            keep.append(r)
    return keep


def select_latest_report(
    reports: Iterable[Report],
    report_type: str = "any",
) -> Optional[Report]:
    """Pick the most-recent periodic report.

    `report_type` is one of 'A001', 'A002', 'A003', 'A004', or 'any'.
    If 'any', we consider the union of periodic reports; ties broken by
    REPORT_TYPE_RANK (annual > semi > Q3 > Q1).
    """
    if report_type == "any":
        candidates = filter_periodic(reports)
    elif report_type in PERIODIC_TYPES:
        candidates = [r for r in reports if r.pblntf_detail_ty == report_type]
    else:
        raise ValueError(
            f"report_type must be 'any' or one of {list(PERIODIC_TYPES)}"
        )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda r: (
            r.rcept_dt,
            REPORT_TYPE_RANK.get(r.pblntf_detail_ty, 0),
        ),
    )


# -----------------------------------------------------------------------------
# Document extraction
# -----------------------------------------------------------------------------

def unzip_document(zip_bytes: bytes) -> dict[str, bytes]:
    """Return {member_name: bytes}. DART packages one or more XML files."""
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            with zf.open(info) as f:
                out[info.filename] = f.read()
    return out


def _title_text(title_elem: etree._Element) -> str:
    text = "".join(title_elem.itertext())
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _is_title_element(tag: str) -> bool:
    # Titles in DART docs: <TITLE>. Some variants use <TITLE-2>, etc.
    t = tag.upper() if isinstance(tag, str) else ""
    return t == "TITLE" or t.startswith("TITLE-")


def _section_ancestor(title_elem: etree._Element) -> etree._Element:
    """Nearest ancestor of the TITLE that looks like a SECTION-* wrapper.

    Fall back to the TITLE's immediate parent if no SECTION ancestor is found.
    """
    node = title_elem.getparent()
    while node is not None:
        tag = node.tag.upper() if isinstance(node.tag, str) else ""
        if tag.startswith("SECTION") or tag == "BODY" or tag == "LIBRARY":
            # LIBRARY/BODY are too broad; only return SECTION-*.
            if tag.startswith("SECTION"):
                return node
        node = node.getparent()
    return title_elem.getparent() if title_elem.getparent() is not None else title_elem


def find_sections_by_title(
    xml_bytes: bytes,
    pattern: re.Pattern[str],
    *,
    exclude: Optional[re.Pattern[str]] = None,
) -> list[etree._Element]:
    """Return section elements whose title matches `pattern` (and not `exclude`)."""
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(xml_bytes, parser=parser)
    except etree.XMLSyntaxError:
        return []
    if root is None:
        return []
    matches: list[etree._Element] = []
    seen: set[int] = set()
    for elem in root.iter():
        tag = elem.tag if isinstance(elem.tag, str) else ""
        if not _is_title_element(tag):
            continue
        title = _title_text(elem)
        if not pattern.search(title):
            continue
        if exclude is not None and exclude.search(title):
            continue
        section = _section_ancestor(elem)
        if id(section) in seen:
            continue
        seen.add(id(section))
        matches.append(section)
    return matches


def serialise_section(elem: etree._Element) -> tuple[str, str]:
    """Serialise a section element to (html_like, text).

    The DART XML schema is HTML-ish (TABLE/TBODY/ROW/ENTRY etc.). We emit:
      * `html` — the XML serialised with pretty-printing (safe to open in
        a browser via the wrapper below).
      * `text` — whitespace-collapsed plain-text of the whole subtree.
    """
    xml_str = etree.tostring(elem, pretty_print=True, encoding="unicode")
    # Wrap in a minimal HTML shell so browsers can display it.
    html_doc = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<title>DART section</title></head><body><pre>"
        + _escape_for_pre(xml_str)
        + "</pre></body></html>"
    )
    # Plain text: preserve paragraph breaks.
    parts: list[str] = []
    for node in elem.iter():
        tag = node.tag.upper() if isinstance(node.tag, str) else ""
        if tag in {"P", "TITLE", "TE", "TU", "LI", "ENTRY"}:
            txt = "".join(node.itertext()).strip()
            if txt:
                parts.append(txt)
    text = "\n\n".join(parts) if parts else "".join(elem.itertext()).strip()
    return html_doc, text


def _escape_for_pre(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def extract_business_section(
    documents: dict[str, bytes],
) -> Optional[tuple[str, str, str]]:
    """Return (member_name, html, text) or None."""
    for name, xml in documents.items():
        sections = find_sections_by_title(xml, BUSINESS_SECTION_PATTERN)
        if sections:
            html, text = serialise_section(sections[0])
            return name, html, text
    return None


def extract_notes_section(
    documents: dict[str, bytes],
    *,
    prefer: str = "consolidated",
) -> Optional[tuple[str, str, str, str]]:
    """Return (member_name, variant, html, text) or None.

    `variant` is 'consolidated' or 'standalone' depending on which was found.
    If `prefer == 'consolidated'` we scan all members for 연결 notes first,
    and only fall back to standalone if none was found.  If prefer='standalone',
    scan for standalone first, then consolidated.
    """
    order = (
        [("consolidated", CONSOLIDATED_NOTES_PATTERN, None),
         ("standalone", STANDALONE_NOTES_PATTERN, CONSOLIDATED_NOTES_PATTERN)]
        if prefer == "consolidated"
        else
        [("standalone", STANDALONE_NOTES_PATTERN, CONSOLIDATED_NOTES_PATTERN),
         ("consolidated", CONSOLIDATED_NOTES_PATTERN, None)]
    )
    for variant, pat, exclude in order:
        for name, xml in documents.items():
            sections = find_sections_by_title(xml, pat, exclude=exclude)
            if sections:
                html, text = serialise_section(sections[0])
                return name, variant, html, text
    return None


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------

def get_corps(client: DartClient, *, force_refresh: bool = False) -> list[Corp]:
    if not force_refresh:
        cached = load_cached_corp_codes()
        if cached is not None:
            logger.info("Using cached corpCode list (%d entries)", len(cached))
            return cached
    logger.info("Downloading corpCode.xml from DART ...")
    zip_bytes = client.fetch_corp_codes_zip()
    xml_bytes = extract_corpcode_xml(zip_bytes)
    corps = parse_corp_codes(xml_bytes)
    save_cached_corp_codes(corps)
    logger.info("Cached %d corps to %s", len(corps), CACHE_FILE)
    return corps


def resolve_corp(
    client: DartClient,
    *,
    name: Optional[str],
    corp_code: Optional[str],
    interactive: bool = True,
    force_refresh: bool = False,
) -> Corp:
    corps = get_corps(client, force_refresh=force_refresh)
    if corp_code:
        for c in corps:
            if c.corp_code == corp_code:
                return c
        raise DartApiError(f"corp_code {corp_code} not found in corpCode.xml")

    assert name is not None
    hits = search_corps(corps, name)
    if not hits:
        raise DartApiError(f"No corp matches name={name!r}")
    if len(hits) == 1:
        return hits[0]

    # Disambiguate.
    print(f"\nFound {len(hits)} matches for {name!r}:", file=sys.stderr)
    for i, c in enumerate(hits, 1):
        tag = "[상장]" if c.is_listed else "[비상장]"
        print(
            f"  {i:>2}. {c.corp_name}  {tag}  "
            f"corp_code={c.corp_code}  stock_code={c.stock_code or '-'}  "
            f"modify={c.modify_date}",
            file=sys.stderr,
        )
    if not interactive:
        raise DartApiError(
            "Ambiguous match; re-run with --corp-code <8자리>."
        )
    try:
        choice = input("Select number (or press Enter to abort): ").strip()
    except EOFError:
        raise DartApiError("Ambiguous match; re-run with --corp-code <8자리>.")
    if not choice:
        raise DartApiError("Aborted by user.")
    try:
        idx = int(choice)
    except ValueError:
        raise DartApiError(f"Invalid selection: {choice!r}")
    if not 1 <= idx <= len(hits):
        raise DartApiError(f"Selection {idx} out of range")
    return hits[idx - 1]


def fetch_latest_report(
    client: DartClient,
    corp: Corp,
    *,
    report_type: str = "any",
    lookback_days: int = 365 * 3,
) -> Report:
    end_de = datetime.now()
    bgn_de = end_de - timedelta(days=lookback_days)
    pblntf_detail_ty = None if report_type == "any" else report_type
    data = client.fetch_list(
        corp.corp_code,
        bgn_de=bgn_de.strftime("%Y%m%d"),
        end_de=end_de.strftime("%Y%m%d"),
        pblntf_ty="A",
        pblntf_detail_ty=pblntf_detail_ty,
        page_count=100,
    )
    reports = parse_reports(data.get("list", []))
    picked = select_latest_report(reports, report_type=report_type)
    if picked is None:
        raise DartApiError(
            f"No periodic reports found for {corp.corp_name} "
            f"({corp.corp_code}) in the last {lookback_days} days."
        )
    return picked


def run(
    *,
    name: Optional[str],
    corp_code: Optional[str],
    report_type: str,
    outdir: Path,
    prefer: str,
    api_key: Optional[str] = None,
    interactive: bool = True,
    force_refresh: bool = False,
) -> dict:
    api_key = api_key or os.environ.get("DART_API_KEY")
    client = DartClient(api_key)

    corp = resolve_corp(
        client,
        name=name,
        corp_code=corp_code,
        interactive=interactive,
        force_refresh=force_refresh,
    )
    logger.info("Selected corp: %s (%s)", corp.corp_name, corp.corp_code)

    report = fetch_latest_report(client, corp, report_type=report_type)
    logger.info(
        "Latest report: %s [%s] rcept_no=%s rcept_dt=%s",
        report.report_nm, report.pblntf_detail_ty,
        report.rcept_no, report.rcept_dt,
    )

    logger.info("Downloading document.xml bundle ...")
    zip_bytes = client.fetch_document_zip(report.rcept_no)
    documents = unzip_document(zip_bytes)
    logger.info("Document bundle members: %s", list(documents))

    # Persist
    outdir.mkdir(parents=True, exist_ok=True)
    raw_dir = outdir / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "document.zip").write_bytes(zip_bytes)
    for member_name, data in documents.items():
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", member_name)
        (raw_dir / safe).write_bytes(data)

    # Extract sections
    biz = extract_business_section(documents)
    notes = extract_notes_section(documents, prefer=prefer)

    business_status = "ok" if biz else "missing"
    notes_status = "missing"
    notes_variant = None
    if biz:
        _, html, text = biz
        (outdir / "business_section.html").write_text(html, encoding="utf-8")
        (outdir / "business_section.txt").write_text(text, encoding="utf-8")
    else:
        logger.warning("'사업의 내용' section NOT found in document bundle.")

    if notes:
        _, variant, html, text = notes
        notes_status = "ok"
        notes_variant = variant
        (outdir / "notes_section.html").write_text(html, encoding="utf-8")
        (outdir / "notes_section.txt").write_text(text, encoding="utf-8")
    else:
        logger.warning("Notes section (연결/재무제표 주석) NOT found.")

    meta = {
        "corp": asdict(corp),
        "report": asdict(report),
        "report_type_name": PERIODIC_TYPES.get(
            report.pblntf_detail_ty, report.pblntf_detail_ty
        ),
        "document_members": list(documents),
        "business_section": {
            "status": business_status,
            "source_member": biz[0] if biz else None,
            "html_path": "business_section.html" if biz else None,
            "txt_path": "business_section.txt" if biz else None,
        },
        "notes_section": {
            "status": notes_status,
            "variant": notes_variant,
            "source_member": notes[0] if notes else None,
            "html_path": "notes_section.html" if notes else None,
            "txt_path": "notes_section.txt" if notes else None,
        },
        "raw_dir": "raw/",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    (outdir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Download the most recent DART periodic report for a "
        "Korean company and extract the 사업의 내용 and 주석 sections."
    )
    sel = p.add_mutually_exclusive_group(required=True)
    sel.add_argument("--name", help="회사명 (한글 또는 영문). 동명이인 발생 시 대화식으로 선택.")
    sel.add_argument("--corp-code", help="DART 8자리 corp_code로 직접 지정")

    p.add_argument(
        "--report-type", default="any",
        choices=["any", "A001", "A002", "A003", "A004"],
        help="A001=사업, A002=반기, A003=1Q, A004=3Q. 기본 any (가장 최근 정기보고서)",
    )
    p.add_argument("--outdir", type=Path, default=Path("./out"))
    p.add_argument(
        "--prefer", choices=["consolidated", "standalone"], default="consolidated",
        help="주석 우선순위. 기본 consolidated(연결재무제표 주석). 폴백 자동.",
    )
    p.add_argument("--non-interactive", action="store_true")
    p.add_argument("--force-refresh", action="store_true",
                   help="corpCode 캐시를 무시하고 재다운로드")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )

    try:
        meta = run(
            name=args.name,
            corp_code=args.corp_code,
            report_type=args.report_type,
            outdir=args.outdir,
            prefer=args.prefer,
            interactive=not args.non_interactive,
            force_refresh=args.force_refresh,
        )
    except DartApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
