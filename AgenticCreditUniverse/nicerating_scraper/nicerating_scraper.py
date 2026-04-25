#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NICE신용평가(nicerating.com) 스크래퍼 — v2
==========================================

v1 대비 변경점
--------------
1. **최신 신용평가 PDF**: 더 이상 리서치 탭이 아니라 기업 상세 페이지
   (`/disclosure/companyGradeInfo.do`)의 **등급 히스토리 테이블들**에서
   “의견서” 컬럼의 docId(`fncFileDown('<uuid>')`)를 모두 모은 뒤,
   유형 상관없이(채권/기업어음/전자단기사채/기업신용등급 등) **등급확정일**
   이 가장 최근인 행의 PDF를 `/common/fileDown.do?docId=<uuid>` 로 내려받는다.
   응답 Content-Type/매직바이트(`%PDF-`)를 검증한다.
2. **JS 렌더링 의존성 처리**: 위 docId 매핑은 서버-사이드 HTML에는 없고 페이지
   로드 후 JS 가 채워넣는다. 따라서 기본 구현은 **Playwright** (headless
   Chromium) 를 사용한다. Playwright 미설치 시 `ImportError` 대신 친절한 안내
   메시지로 실패한다(자동 설치 명령까지 출력).
3. **로그인 + 재무부표 전체**: `.env` 또는 환경변수로 들어오는
   `NICERATING_USER_ID` / `NICERATING_USER_PW` 로 `/logInProc.do` 에 로그인.
   성공하면 `/company/companyChargeFinanceProc.do` (POST JSON) 에서
   **연결 기준 재무부표 전체** (재무상태표 BS, 손익계산서 IS, 현금흐름표 CF
   및 파생 지표) 를 수집해 `_CFS_full.json` 및 `_CFS_full.csv` 로 저장한다.
   자격 증명이 없을 때는 공개 CFS 요약 추출만 계속 동작한다.

보안 메모 — 자격 증명 취급
--------------------------
- 본 스크립트는 `NICERATING_USER_ID` / `NICERATING_USER_PW` 를 오직 메모리
  상에서만 사용한다. 파일/로그에 절대 기록하지 않는다.
- `.env` 파일 예시(`./.env.example`) 에는 값 없이 키만 둔다.
- 로그 핸들러는 `logging.Filter` 로 자격 증명 문자열을 자동 마스킹한다.

사용 예 (CLI)
-------------
    # 공개 정보(요약) + 최신 신용평가 PDF 다운로드
    python3 nicerating_scraper.py --cmpcd 1326874 --outdir ./out

    # 로그인해서 재무부표 전체까지 함께 저장 (.env 혹은 환경변수 필요)
    export NICERATING_USER_ID=...
    export NICERATING_USER_PW=...
    python3 nicerating_scraper.py --cmpcd 1326874 --outdir ./out --full-financials

    # 기업명으로 검색해서 cmpCd 자동 해석
    python3 nicerating_scraper.py --name "삼성전자(주)" --outdir ./out

프로그래밍 API (핵심 메서드)
---------------------------
    s = NiceRatingScraper()
    s.login()                                # 선택: env 있으면 자동, 없으면 ValueError
    cmpCd = s.resolve_cmpcd("삼성전자(주)")
    info  = s.get_company_info(cmpCd)
    summary_ft = s.get_financials(cmpCd, kind="CFS")              # 공개 요약 (로그인 無)
    full_ft    = s.get_full_financials(cmpCd, kind="CFS")         # 로그인 필요
    rating, pdf_path = s.download_latest_rating_pdf(cmpCd, outdir)

데이터 경로 요약 (확인됨)
-------------------------
- 검색: `GET /search/search.do?mainSType=CMP&mainSText=<이름>`
- 기업 개요: `GET /disclosure/companyGradeInfo.do?cmpCd=<cmpCd>`
- 등급 히스토리(JS-rendered): table[caption="목록"] × 다수 (채권/기업어음/전자단기사채/기업신용등급/보험지급능력)
  각 행의 의견서 anchor 에 JS 가 주입한 `href="javascript:fncFileDown('<UUID>')"`.
- PDF: `GET /common/fileDown.do?docId=<UUID>` → `application/pdf`, `%PDF-` 매직.
- 공개 주요재무지표: `POST /company/companyMajorFinanceProc.do` (body `{cmpCd,kind}`).
- **로그인**: `POST /logInProc.do` (form-urlencoded body `userId`, `userPw`).
  성공 시 302 로 이전 페이지(Referer) 로 리다이렉트, 세션쿠키 발급됨.
  로그아웃 링크 존재(‘로그아웃’) 여부로 성공 검증.
- 재무부표 전체(연결): `POST /company/companyChargeFinanceProc.do`
  body `{"cmpCd":"<cmpCd>", "kind":"CFS"}` → JSON.
  `list.SUMM11` = 재무상태표(BS), `list.SUMM12` = 손익계산서(IS),
  `list.SUMM16` = 현금흐름표(CF) + 파생 지표(colAfsClsCd=19).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:  # Optional: .env loader
    from dotenv import load_dotenv  # type: ignore
    _HAS_DOTENV = True
except ImportError:  # pragma: no cover
    _HAS_DOTENV = False

try:
    import pandas as pd  # type: ignore
    _HAS_PANDAS = True
except ImportError:  # pragma: no cover
    _HAS_PANDAS = False


BASE_URL = "https://www.nicerating.com"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": f"{BASE_URL}/main.do",
}

ENV_USER_ID = "NICERATING_USER_ID"
ENV_USER_PW = "NICERATING_USER_PW"


# ---------------------------------------------------------------------------
# Credential-aware logging (never leak PW/ID)
# ---------------------------------------------------------------------------
class _CredentialFilter(logging.Filter):
    """Scrub credential values from log records if they somehow appear."""

    def __init__(self):
        super().__init__()
        self._targets: List[str] = []

    def add_value(self, value: str) -> None:
        if value and value not in self._targets:
            self._targets.append(value)

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        msg = record.getMessage()
        scrubbed = msg
        for t in self._targets:
            if t and t in scrubbed:
                scrubbed = scrubbed.replace(t, "***")
        if scrubbed != msg:
            record.msg = scrubbed
            record.args = ()
        return True


_credential_filter = _CredentialFilter()
log = logging.getLogger("nicerating")
log.addFilter(_credential_filter)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class CompanyInfo:
    cmpCd: str
    cmpNm: Optional[str] = None
    representative: Optional[str] = None
    industry: Optional[str] = None
    type_scale: Optional[str] = None
    affiliate: Optional[str] = None
    fiscal_month: Optional[str] = None


@dataclass
class FinancialTable:
    cmpCd: str
    cmpNm: Optional[str]
    kind: str
    kind_label: str
    periods: List[str]
    indicators: List[Dict[str, str]] = field(default_factory=list)

    def to_dataframe(self):  # pragma: no cover
        if not _HAS_PANDAS:
            raise RuntimeError("pandas 미설치: `pip install pandas`")
        return pd.DataFrame(self.indicators)


@dataclass
class FullFinancialTable:
    cmpCd: str
    cmpNm: Optional[str]
    kind: str               # CFS | FLS
    kind_label: str         # 연결 | 개별
    periods: List[str]
    sections: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)

    def all_rows(self) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for section, items in self.sections.items():
            for row in items:
                r = dict(row)
                r["_section"] = section
                rows.append(r)
        return rows


@dataclass
class RatingEntry:
    rating_type: str        # "채권" | "기업어음" | "전자단기사채" | "기업신용등급" | "보험지급능력" | ...
    current_grade: str      # "AAA" / "A1" / ...
    outlook: str            # "안정적" / "Stable" / ""
    determined_date: str    # "YYYY.MM.DD" (등급확정일)
    decided_date: str       # "YYYY.MM.DD" (등급결정일/평가일) — 없으면 ""
    docId: Optional[str]    # PDF docId for /common/fileDown.do
    bond_series: str = ""   # 채권 전용: 회차 (예: "제224-4회")
    bond_rank: str = ""     # 채권 전용: 상환순위 (예: "선순위")
    bond_kind: str = ""     # 채권 전용: 종류 (예: "SB")
    row_order: int = 0      # 원 테이블 내 행 인덱스 (동일 일자 타이브레이커)
    raw_cells: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------
class NiceRatingScraper:
    def __init__(
        self,
        request_delay: float = 1.0,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        self.request_delay = request_delay
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._logged_in = False

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _get(self, path: str, *, allow_redirects: bool = True, **kw) -> requests.Response:
        url = path if path.startswith("http") else BASE_URL + path
        resp = self.session.get(url, timeout=self.timeout, allow_redirects=allow_redirects, **kw)
        time.sleep(self.request_delay)
        return resp

    def _post_json(self, path: str, payload: dict, **kw) -> requests.Response:
        url = BASE_URL + path
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/main.do",
        }
        resp = self.session.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers, timeout=self.timeout, **kw,
        )
        time.sleep(self.request_delay)
        return resp

    def _post_form(self, path: str, payload: dict, **kw) -> requests.Response:
        url = BASE_URL + path
        resp = self.session.post(url, data=payload, timeout=self.timeout, **kw)
        time.sleep(self.request_delay)
        return resp

    # ------------------------------------------------------------------
    # 1) Login (paid-member endpoints)
    # ------------------------------------------------------------------
    def login(self, user_id: Optional[str] = None, user_pw: Optional[str] = None) -> None:
        """Login via POST /logInProc.do. Credentials default to env vars.

        Raises ``ValueError`` if credentials missing or login verification fails.
        """
        if _HAS_DOTENV:
            load_dotenv(override=False)
        uid = user_id or os.environ.get(ENV_USER_ID)
        upw = user_pw or os.environ.get(ENV_USER_PW)
        if not uid or not upw:
            raise ValueError(
                f"자격 증명이 설정되지 않았습니다. 다음 두 값을 환경변수 또는 .env 로 제공하세요: "
                f"{ENV_USER_ID}, {ENV_USER_PW}  (공개 요약 추출만 필요하면 login() 을 호출하지 마세요.)"
            )
        # Register for log-scrubbing
        _credential_filter.add_value(uid)
        _credential_filter.add_value(upw)

        # 1) seed session (cookie)
        self._get("/logIn.do")

        # 2) submit credentials
        resp = self._post_form(
            "/logInProc.do",
            {"userId": uid, "userPw": upw},
            headers={"Referer": f"{BASE_URL}/logIn.do"},
        )
        # Expected: 302 redirect → follow → 200
        if resp.status_code != 200:
            raise ValueError(f"로그인 실패: HTTP {resp.status_code}")

        # 3) verify — /main.do should now contain a logout link
        if not self.verify_authenticated():
            raise ValueError("로그인 실패: 자격 증명이 잘못되었거나 세션이 생성되지 않았습니다.")
        self._logged_in = True
        log.info("로그인 성공 — 유료 회원 세션 활성화")

    def verify_authenticated(self) -> bool:
        """Check whether the current session is logged in.

        Indicator: `/main.do` contains a '로그아웃' anchor when authenticated.
        """
        resp = self._get("/main.do")
        html = resp.text or ""
        # On login pages the anchor class 'btn_log' is present regardless; the
        # logout label '로그아웃' only appears when a session is active.
        return "로그아웃" in html

    # ------------------------------------------------------------------
    # 2) Company name → cmpCd
    # ------------------------------------------------------------------
    def resolve_cmpcd(self, company_name: str) -> str:
        if not company_name or not company_name.strip():
            raise ValueError("company_name 이 비어 있습니다.")
        resp = self._get("/search/search.do",
                         params={"mainSType": "CMP", "mainSText": company_name.strip()})
        resp.raise_for_status()
        cmpCd = _extract_cmpcd_from_url(resp.url)
        if cmpCd:
            return cmpCd
        names = _extract_candidate_company_names(resp.text)
        raise ValueError(
            f"'{company_name}' 단일매칭 실패. 후보: {names[:15]} … cmpCd 를 직접 지정해서 호출하세요."
        )

    # ------------------------------------------------------------------
    # 3) Company overview
    # ------------------------------------------------------------------
    def get_company_info(self, cmpCd: str) -> CompanyInfo:
        resp = self._get("/disclosure/companyGradeInfo.do", params={"cmpCd": cmpCd})
        resp.raise_for_status()
        return parse_company_info(resp.text, cmpCd=cmpCd)

    # ------------------------------------------------------------------
    # 4) Public major-indicator financials (no login)
    # ------------------------------------------------------------------
    def get_financials(self, cmpCd: str, kind: str = "CFS") -> FinancialTable:
        kind = kind.upper()
        if kind not in ("CFS", "FLS"):
            raise ValueError("kind 는 'CFS' 또는 'FLS'")
        self._get("/company/companyMajorFinance.do", params={"cmpCd": cmpCd})
        resp = self._post_json(
            "/company/companyMajorFinanceProc.do",
            {"cmpCd": str(cmpCd), "kind": kind},
        )
        resp.raise_for_status()
        return parse_major_finance_json(resp.json(), cmpCd=cmpCd, kind=kind)

    def save_financials(self, cmpCd: str, *, outdir: str,
                        kinds: Sequence[str] = ("CFS",),
                        formats: Sequence[str] = ("json", "csv")) -> Dict[str, List[str]]:
        os.makedirs(outdir, exist_ok=True)
        written: Dict[str, List[str]] = {"json": [], "csv": []}
        for kind in kinds:
            ft = self.get_financials(cmpCd, kind=kind)
            base = os.path.join(outdir, f"nicerating_{cmpCd}_{kind}")
            if "json" in formats:
                path = base + ".json"
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({
                        "cmpCd": ft.cmpCd, "cmpNm": ft.cmpNm,
                        "kind": ft.kind, "kind_label": ft.kind_label,
                        "periods": ft.periods, "indicators": ft.indicators,
                    }, f, ensure_ascii=False, indent=2)
                written["json"].append(path)
            if "csv" in formats:
                path = base + ".csv"
                _write_indicator_csv(ft.periods, ft.indicators, path)
                written["csv"].append(path)
        return written

    # ------------------------------------------------------------------
    # 5) Full 재무부표 (login required)
    # ------------------------------------------------------------------
    def get_full_financials(self, cmpCd: str, kind: str = "CFS") -> FullFinancialTable:
        if not self._logged_in and not self.verify_authenticated():
            raise PermissionError(
                "재무부표 전체 조회는 유료 회원 로그인 필요. 먼저 login() 호출."
            )
        kind = kind.upper()
        if kind not in ("CFS", "FLS"):
            raise ValueError("kind 는 'CFS' 또는 'FLS'")
        # seed session on the wrapper page
        ms = int(time.time() * 1000) % 1000
        self._get("/company/companyChargeFinance.do", params={"cmpCd": cmpCd, "s": ms})
        resp = self._post_json(
            "/company/companyChargeFinanceProc.do",
            {"cmpCd": str(cmpCd), "kind": kind},
        )
        resp.raise_for_status()
        return parse_full_finance_json(resp.json(), cmpCd=cmpCd, kind=kind)

    def save_full_financials(self, cmpCd: str, *, outdir: str,
                             kinds: Sequence[str] = ("CFS",),
                             formats: Sequence[str] = ("json", "csv")) -> Dict[str, List[str]]:
        os.makedirs(outdir, exist_ok=True)
        written: Dict[str, List[str]] = {"json": [], "csv": []}
        for kind in kinds:
            ft = self.get_full_financials(cmpCd, kind=kind)
            base = os.path.join(outdir, f"nicerating_{cmpCd}_{kind}_full")
            if "json" in formats:
                p = base + ".json"
                with open(p, "w", encoding="utf-8") as f:
                    json.dump({
                        "cmpCd": ft.cmpCd, "cmpNm": ft.cmpNm,
                        "kind": ft.kind, "kind_label": ft.kind_label,
                        "periods": ft.periods, "sections": ft.sections,
                    }, f, ensure_ascii=False, indent=2)
                written["json"].append(p)
            if "csv" in formats:
                p = base + ".csv"
                _write_full_finance_csv(ft, p)
                written["csv"].append(p)
        return written

    # ------------------------------------------------------------------
    # 6) Latest rating PDF
    # ------------------------------------------------------------------
    def list_ratings(self, cmpCd: str) -> List[RatingEntry]:
        """Render the detail page (JS required) and extract all rating-history rows with docIds."""
        page_url = f"{BASE_URL}/disclosure/companyGradeInfo.do?cmpCd={cmpCd}&s=526"
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "최신 신용평가 PDF 를 내려받으려면 Playwright 가 필요합니다.\n"
                "  pip install playwright && playwright install chromium\n"
                "이미 렌더링된 HTML 이 있다면 parse_ratings_from_html() 를 직접 호출하세요."
            ) from e

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9"})
            # seed cookies from our requests.Session (may carry login)
            jar = []
            for ck in self.session.cookies:
                jar.append({
                    "name": ck.name, "value": ck.value,
                    "domain": ck.domain or "www.nicerating.com",
                    "path": ck.path or "/",
                })
            if jar:
                context.add_cookies(jar)
            page = context.new_page()
            page.goto(page_url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)
            rendered_html = page.content()
            browser.close()
        return parse_ratings_from_html(rendered_html)

    def download_latest_rating_pdf(self, cmpCd: str, *, outdir: str,
                                   filename_hint: Optional[str] = None
                                   ) -> Tuple[RatingEntry, str]:
        os.makedirs(outdir, exist_ok=True)
        ratings = self.list_ratings(cmpCd)
        top = pick_latest_rating(ratings)
        if top is None:
            raise RuntimeError(
                f"cmpCd={cmpCd} 에서 docId 가 노출된 의견서 행이 없습니다. "
                f"(유료 차단이거나 보고서 미등록)"
            )
        log.info(
            "최신 등급 선정: 유형=%s %s 등급=%s 확정일=%s (회차=%s, 종류=%s, 행인덱스=%d)",
            top.rating_type, top.bond_rank, top.current_grade, top.determined_date,
            top.bond_series, top.bond_kind, top.row_order,
        )

        resp = self._get("/common/fileDown.do", params={"docId": top.docId})
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "application/pdf" not in ctype and resp.content[:5] != b"%PDF-":
            raise RuntimeError(
                f"PDF 다운로드 실패: Content-Type={ctype!r}, magic={resp.content[:8]!r}"
            )
        default_name = _build_pdf_filename(cmpCd, top)
        out_path = os.path.join(outdir, filename_hint or default_name)
        with open(out_path, "wb") as f:
            f.write(resp.content)
        return top, out_path


# ---------------------------------------------------------------------------
# Latest-rating selection
# ---------------------------------------------------------------------------
# 타이브레이커 순서:
#   1) 등급확정일 (desc)
#   2) 등급결정일(평가일) (desc)
#   3) 유형 가중치: 채권 > 기업어음 > 전자단기사채 > 기업신용등급 > 보험지급능력 > 기타
#      (장기 채권 발행은 가장 상세한 평가의견서가 첨부되므로 우선)
#   4) 원 테이블 내 행 인덱스 (ascending — 서버가 이미 최신순 정렬)
_TYPE_WEIGHT = {
    "채권": 0, "기업어음": 1, "전자단기사채": 2, "기업신용등급": 3, "보험지급능력": 4,
}


def pick_latest_rating(ratings: List[RatingEntry]) -> Optional[RatingEntry]:
    with_doc = [r for r in ratings if r.docId]
    if not with_doc:
        return None

    def key(r: RatingEntry):
        return (
            _norm_date(r.determined_date),                         # 1) 등급확정일 desc
            _norm_date(r.decided_date or r.determined_date),       # 2) 등급결정일 desc
            -_TYPE_WEIGHT.get(r.rating_type, 99),                  # 3) type weight (negative so larger=better in reverse)
            -r.row_order,                                          # 4) row index (smaller=earlier on page=better)
        )

    with_doc.sort(key=key, reverse=True)
    return with_doc[0]


def _build_pdf_filename(cmpCd: str, r: RatingEntry) -> str:
    yyyymmdd = (r.determined_date or r.decided_date or "").replace(".", "")
    parts = [cmpCd, yyyymmdd]
    # Include 회차 + 종류 when present (채권 rows). Otherwise use rating_type.
    if r.bond_series:
        parts.append(r.bond_series)           # e.g. "제224-4회"
    if r.bond_kind:
        parts.append(r.bond_kind)             # e.g. "SB"
    if not r.bond_series and r.rating_type:
        parts.append(r.rating_type)           # e.g. "기업신용등급"
    if r.current_grade:
        parts.append(r.current_grade)         # e.g. "AA+"
    fname = "_".join(_safe_filename(p) for p in parts if p)
    return f"{fname}.pdf"


# ---------------------------------------------------------------------------
# Parsing helpers (module-level)
# ---------------------------------------------------------------------------
_CMPCD_RE = re.compile(r"[?&]cmpCd=(\d+)")


def _extract_cmpcd_from_url(url: str) -> Optional[str]:
    m = _CMPCD_RE.search(url or "")
    return m.group(1) if m else None


def _extract_candidate_company_names(html: str, limit: int = 30) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    names: List[str] = []
    for td in soup.select("td.cell_type01"):
        a = td.find("a")
        if a and a.get_text(strip=True):
            text = a.get_text(strip=True)
            if not text.startswith("[") and text not in names:
                names.append(text)
        if len(names) >= limit:
            break
    return names


def parse_company_info(html: str, cmpCd: str) -> CompanyInfo:
    soup = BeautifulSoup(html, "html.parser")
    info = CompanyInfo(cmpCd=cmpCd)
    div = soup.select_one("div.tbl_type99")
    if div:
        first_tbl = div.find("table")
        if first_tbl:
            cells = [td.get_text(strip=True) for td in first_tbl.select("tbody tr td")]
            if len(cells) >= 6:
                (info.cmpNm, info.representative, info.industry,
                 info.type_scale, info.affiliate, info.fiscal_month) = cells[:6]
    return info


def parse_major_finance_json(data: dict, *, cmpCd: str, kind: str) -> FinancialTable:
    listobj = data.get("list") or {}
    sttdate = listobj.get("STTDATE") or []
    mainfin = listobj.get("mainFinance") or []
    periods = [(r.get("view_STT") or "").strip() for r in sttdate]
    indicators: List[Dict[str, str]] = []
    for row in mainfin:
        item = {
            "계정명": (row.get("colb") or "").strip(),
            "NICE계정코드": row.get("cola") or "",
            "볼드표시": row.get("cole") or "N",
        }
        for i, p in enumerate(periods):
            item[p] = row.get(f"col{i}", "")
        indicators.append(item)
    kind_label = {"CFS": "연결", "FLS": "개별"}.get(kind.upper(), kind)
    return FinancialTable(cmpCd=cmpCd, cmpNm=data.get("cmpIfr"),
                          kind=kind.upper(), kind_label=kind_label,
                          periods=periods, indicators=indicators)


# --- 재무부표 (BS/IS/CF)
_SECTION_NAMES = {
    "11": "재무상태표(BS)",
    "12": "손익계산서(IS)",
    "16": "현금흐름표(CF)",
    "19": "재무비율(지표)",
}


def parse_full_finance_json(data: dict, *, cmpCd: str, kind: str) -> FullFinancialTable:
    listobj = data.get("list") or {}
    periods = [(r.get("view_STT") or "").strip() for r in listobj.get("STTDATE") or []]
    sections: Dict[str, List[Dict[str, str]]] = {}

    def _convert(rows):
        out = []
        for r in rows or []:
            item = {
                "계정명": (r.get("colb") or "").strip(),
                "NICE계정코드": r.get("cola") or "",
                "볼드표시": r.get("cole") or "N",
                "섹션코드": r.get("colAfsClsCd") or "",
            }
            for i, p in enumerate(periods):
                item[p] = r.get(f"col{i}", "")
            out.append(item)
        return out

    sections[_SECTION_NAMES["11"]] = _convert(listobj.get("SUMM11"))
    sections[_SECTION_NAMES["12"]] = _convert(listobj.get("SUMM12"))
    sections[_SECTION_NAMES["16"]] = _convert(listobj.get("SUMM16"))

    kind_label = {"CFS": "연결", "FLS": "개별"}.get(kind.upper(), kind)
    return FullFinancialTable(
        cmpCd=cmpCd, cmpNm=data.get("cmpIfr"),
        kind=kind.upper(), kind_label=kind_label,
        periods=periods, sections=sections,
    )


# --- 등급 히스토리
# Header variations per table. We want:
#   rating_type    (inferred from section heading, e.g. "채권", "기업어음")
#   current_grade  (column labelled "현재" or "현재등급")
#   outlook        (optional next cell after grade when header has "현재" spanning 2 cols)
#   determined_date  (column labelled "등급확정일")
#   decided_date     (column labelled "등급결정일(평가일)")
#   docId            (href fncFileDown(...) in "의견서" column)
_RATING_HEADINGS_RE = re.compile(r"(채권|기업어음|전자단기사채|기업신용등급|보험지급능력)")


def parse_ratings_from_html(html: str) -> List[RatingEntry]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[RatingEntry] = []
    for tbl in soup.find_all("table"):
        cap = tbl.find("caption")
        if not cap or cap.get_text(strip=True) != "목록":
            continue
        thead = tbl.find("thead")
        if not thead:
            continue
        header_cells = [th.get_text(strip=True) for th in thead.find_all("th")]

        def idx_of(label):
            return header_cells.index(label) if label in header_cells else -1

        i_date_determined = idx_of("등급확정일")
        i_date_decided = idx_of("등급결정일(평가일)")
        i_current = idx_of("현재")
        i_current_grade = idx_of("현재등급")
        i_series = idx_of("회차")
        i_rank = idx_of("상환순위")
        i_kind_bond = idx_of("종류")
        if i_date_determined < 0:
            continue
        rating_type = _find_preceding_section_heading(tbl)
        for row_idx, tr in enumerate(tbl.select("tbody tr")):
            tds = tr.find_all("td", recursive=False)
            if not tds:
                continue
            cells = [td.get_text(strip=True) for td in tds]
            if len(cells) < i_date_determined + 1:
                continue
            docId = None
            op_img = tr.find("img", alt="의견서")
            if op_img is not None:
                a = op_img.find_parent("a")
                if a:
                    href = a.get("href") or ""
                    m = re.search(r"fncFileDown\('([^']+)'\)", href)
                    if m:
                        docId = m.group(1)
            current_grade = ""
            outlook = ""
            if i_current_grade >= 0 and i_current_grade < len(cells):
                current_grade = cells[i_current_grade]
            elif i_current >= 0 and i_current < len(cells):
                current_grade = cells[i_current]
                if i_current + 1 < len(cells) and not re.match(r"\d{4}\.\d{2}\.\d{2}", cells[i_current + 1]):
                    outlook = cells[i_current + 1]
            determined = cells[i_date_determined] if i_date_determined < len(cells) else ""
            decided = cells[i_date_decided] if 0 <= i_date_decided < len(cells) else ""
            if not re.match(r"\d{4}\.\d{2}\.\d{2}", determined):
                continue
            bond_series = cells[i_series] if 0 <= i_series < len(cells) else ""
            bond_rank = cells[i_rank] if 0 <= i_rank < len(cells) else ""
            bond_kind = cells[i_kind_bond] if 0 <= i_kind_bond < len(cells) else ""
            results.append(RatingEntry(
                rating_type=rating_type,
                current_grade=current_grade,
                outlook=outlook,
                determined_date=determined,
                decided_date=decided,
                docId=docId,
                bond_series=bond_series,
                bond_rank=bond_rank,
                bond_kind=bond_kind,
                row_order=row_idx,
                raw_cells=cells,
            ))
    return results


def _find_preceding_section_heading(tbl) -> str:
    """Walk backward through siblings/ancestors to find the nearest '채권'/'기업어음'/etc heading."""
    # Walk the ancestors' earlier siblings until we find a matching text
    node = tbl
    for _ in range(6):  # safety depth
        sib = node.find_previous(["h2", "h3", "div"])
        steps = 0
        while sib is not None and steps < 30:
            text = sib.get_text(" ", strip=True) if sib else ""
            m = _RATING_HEADINGS_RE.search(text or "")
            if m:
                return m.group(1)
            sib = sib.find_previous(["h2", "h3", "div"])
            steps += 1
        node = node.parent if node.parent else node
        if node is None:
            break
    return ""


def _safe_filename(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣._\-+]+", "_", name or "").strip("_") or "unknown"


def _norm_date(s: str) -> str:
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", s or "")
    if not m:
        return "0000-00-00"
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _write_indicator_csv(periods: List[str], indicators: List[Dict[str, str]], path: str) -> None:
    cols = ["계정명", "NICE계정코드", "볼드표시"] + periods
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in indicators:
            w.writerow({k: row.get(k, "") for k in cols})


def _write_full_finance_csv(ft: FullFinancialTable, path: str) -> None:
    cols = ["섹션", "계정명", "NICE계정코드", "볼드표시"] + ft.periods
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for section, rows in ft.sections.items():
            for r in rows:
                w.writerow({
                    "섹션": section,
                    "계정명": r.get("계정명", ""),
                    "NICE계정코드": r.get("NICE계정코드", ""),
                    "볼드표시": r.get("볼드표시", ""),
                    **{p: r.get(p, "") for p in ft.periods},
                })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NICE신용평가 스크래퍼 v2")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--name", help="기업명 (예: '삼성전자(주)')")
    g.add_argument("--cmpcd", help="NICE 기업코드 (예: 1326874)")
    p.add_argument("--outdir", default="./out")
    p.add_argument("--kinds", nargs="+", default=["CFS"], choices=["CFS", "FLS"])
    p.add_argument("--formats", nargs="+", default=["json", "csv"], choices=["json", "csv"])
    p.add_argument("--no-pdf", action="store_true", help="최신 신용평가 PDF 다운로드 생략")
    p.add_argument("--full-financials", action="store_true",
                   help="로그인 후 재무부표 전체도 함께 저장 (.env 필요)")
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--verbose", "-v", action="store_true")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger().addFilter(_credential_filter)

    s = NiceRatingScraper(request_delay=args.delay)

    # optional login (only if user asked for full financials, or credentials set)
    if args.full_financials:
        s.login()

    # 1) resolve cmpCd
    if args.cmpcd:
        cmpCd = str(args.cmpcd)
    else:
        cmpCd = s.resolve_cmpcd(args.name)
    log.info("cmpCd=%s", cmpCd)

    # 2) company info
    try:
        info = s.get_company_info(cmpCd)
        log.info("기업: %s | 산업=%s | 계열=%s | 결산월=%s",
                 info.cmpNm, info.industry, info.affiliate, info.fiscal_month)
    except Exception as e:
        log.warning("기업 개요 실패: %s (계속)", e)

    # 3) public financials summary
    written = s.save_financials(cmpCd, outdir=args.outdir,
                                kinds=args.kinds, formats=args.formats)
    for fmt, paths in written.items():
        for pth in paths:
            log.info("[공개 요약] %s 저장: %s", fmt, pth)

    # 4) full financials (login required)
    if args.full_financials:
        written_full = s.save_full_financials(cmpCd, outdir=args.outdir,
                                              kinds=args.kinds, formats=args.formats)
        for fmt, paths in written_full.items():
            for pth in paths:
                log.info("[재무부표 전체] %s 저장: %s", fmt, pth)

    # 5) latest credit-rating PDF
    if not args.no_pdf:
        try:
            rating, path = s.download_latest_rating_pdf(cmpCd, outdir=args.outdir)
            log.info("최신 신용평가 PDF 저장: %s (유형=%s, 등급=%s, 등급확정일=%s)",
                     path, rating.rating_type, rating.current_grade, rating.determined_date)
        except Exception as e:
            log.warning("최신 신용평가 PDF 다운로드 실패: %s", e)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
