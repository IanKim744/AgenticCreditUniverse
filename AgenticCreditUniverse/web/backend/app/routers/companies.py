from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse, Response

from ..auth import require_session
from ..deps import get_db
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _rating_tier(r: str | None) -> str:
    if not r:
        return "nr"
    s = r.upper()
    if s.startswith("BBB"):
        return "mid"
    if s[0] in ("B", "C", "D"):
        return "low"
    if s[0] == "A":
        return "high"
    return "nr"


def _comment_preview(c: str | None, limit: int = 80) -> str | None:
    if not c:
        return None
    s = c.strip().replace("\n", " ")
    if len(s) <= limit:
        return s
    return s[:limit] + "…"


def _row_to_dict(r: sqlite3.Row, review_map: dict[str, dict]) -> dict[str, Any]:
    rs = review_map.get(r["slug"], {})
    return {
        "slug": r["slug"],
        "issuer": r["issuer"],
        "stock_code": r["stock_code"],
        "group_name": r["group_name"] or r["group_master"],
        "industry": r["industry"],
        "industry_2026": r["industry_2026"],
        "rating_prev": r["rating_prev"],
        "watch_prev": r["watch_prev"],
        "rating_curr": r["rating_curr"],
        "watch_curr": r["watch_curr"],
        "universe_prev": r["universe_prev"],
        "universe_curr_ai": r["universe_curr_ai"] or r["ai_judgment"],
        "reviewer_final": r["reviewer_final"],
        "movement": r["movement"],
        "comment_preview": _comment_preview(r["comment_curr"]),
        "comment_curr": r["comment_curr"],  # 매트릭스 행 펼침 시 전문 표시용
        "manager": r["manager"],
        "review_status": "done" if rs.get("status") == "done" or r["reviewer_final"] else "none",
        "unresolved": bool(r["unresolved"]),
        "last_updated_utc": r["last_updated_utc"],
    }


def _load_period(con: sqlite3.Connection) -> dict[str, Any]:
    rows = con.execute("SELECT k, v FROM period_config").fetchall()
    out: dict[str, Any] = {}
    for k, v in [(r["k"], r["v"]) for r in rows]:
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def _compute_kpis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    tier_count = Counter(_rating_tier(r["rating_curr"]) for r in rows)
    movement_count = Counter()
    for r in rows:
        m = (r["movement"] or "").strip()
        if m == "▲":
            movement_count["up"] += 1
        elif m == "▽" or m == "▼":
            movement_count["down"] += 1
        elif m == "-":
            movement_count["flat"] += 1
    done = sum(1 for r in rows if r["review_status"] == "done")
    return {
        "total": total,
        "rating_distribution": {
            "high": tier_count.get("high", 0),
            "mid": tier_count.get("mid", 0),
            "low": tier_count.get("low", 0),
            "nr": tier_count.get("nr", 0),
        },
        "movement": {
            "up": movement_count.get("up", 0),
            "down": movement_count.get("down", 0),
            "flat": movement_count.get("flat", 0),
        },
        "review": {
            "done": done,
            "none": total - done,
            "pct": (done / total) if total else 0.0,
        },
    }


@router.get("")
def list_companies(
    _sess: dict = Depends(require_session),
    con: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    review_rows = con.execute(
        "SELECT slug, status, universe, agree_with_ai, note, reviewed_by, reviewed_at FROM review_status"
    ).fetchall()
    review_map = {r["slug"]: dict(r) for r in review_rows}

    companies = con.execute(
        "SELECT * FROM companies ORDER BY excel_row"
    ).fetchall()
    rows = [_row_to_dict(r, review_map) for r in companies]
    return {
        "period": _load_period(con),
        "rows": rows,
        "kpis": _compute_kpis(rows),
    }


# ---- detail helpers ----

def _read_json(p: Path) -> Any:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _master_for(slug: str, s: Settings) -> dict[str, Any]:
    master = _read_json(s.master_path) or {}
    info = master.get("companies", {}).get(slug, {})
    return {
        "slug": slug,
        "official_name": info.get("official_name") or slug,
        "stock_code": info.get("stock_code"),
        "corp_code": info.get("corp_code"),
        "cmp_cd": info.get("cmp_cd"),
        "group": info.get("group"),
        "industry": info.get("industry"),
        "aliases": info.get("aliases") or [slug],
    }


def _stage2_for(slug: str, s: Settings) -> tuple[dict | None, dict | None]:
    j = _read_json(s.workspace_dir / "judgment" / "stage2_review.json") or {}
    stage2 = j.get("decisions", {}).get(slug)
    inv: dict | None = None
    for item in j.get("inversions", []):
        if item.get("high_grade_company") == slug or item.get("low_grade_company") == slug:
            inv = item
            break
    return stage2, inv


def _comment_for(slug: str, s: Settings) -> dict[str, Any] | None:
    p = s.workspace_dir / "comments" / f"{slug}.json"
    data = _read_json(p)
    if data is None:
        return None
    return data


def _nice_for(slug: str, s: Settings, cmp_cd: str | None) -> dict[str, Any]:
    folder = s.workspace_dir / "nice" / slug
    cfs = ofs = None
    if folder.exists() and cmp_cd:
        cfs_p = folder / f"nicerating_{cmp_cd}_CFS.json"
        ofs_p = folder / f"nicerating_{cmp_cd}_OFS.json"
        cfs = _read_json(cfs_p)
        ofs = _read_json(ofs_p)
    elif folder.exists():
        # cmp_cd 미상이지만 폴더에 파일이 있으면 첫 매치 사용
        for p in folder.glob("nicerating_*_CFS.json"):
            cfs = _read_json(p)
            break
        for p in folder.glob("nicerating_*_OFS.json"):
            ofs = _read_json(p)
            break

    timeline: list[dict[str, Any]] = []
    if cfs:
        long_row = next((i for i in cfs.get("indicators", []) if i.get("계정명", "").startswith("장기등급")), None)
        short_row = next((i for i in cfs.get("indicators", []) if i.get("계정명", "").startswith("단기등급")), None)
        for period in cfs.get("periods", []):
            timeline.append(
                {
                    "period": period[:7],
                    "long_grade": (long_row or {}).get(period) or None,
                    "short_grade": (short_row or {}).get(period) or None,
                }
            )

    opinion = folder / "opinion.pdf" if folder.exists() else None
    opinion_meta = _read_json(folder / "opinion_meta.json") if folder.exists() else None
    return {
        "cfs": cfs,
        "ofs": ofs,
        "opinion_pdf": f"/api/companies/{slug}/opinion.pdf" if opinion and opinion.exists() else None,
        "opinion_meta": opinion_meta,
        "rating_timeline": timeline,
    }


def _dart_for(slug: str, s: Settings) -> dict[str, Any]:
    folder = s.workspace_dir / "dart" / slug
    meta = _read_json(folder / "metadata.json") or {}
    rcept_no = (meta.get("report") or {}).get("rcept_no")
    report_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else None
    return {
        "metadata": meta,
        "report_url": report_url,
        "business_url": f"/api/companies/{slug}/dart/business.txt",
        "notes_url": f"/api/companies/{slug}/dart/notes.txt",
        "available": folder.exists(),
    }


def _is_within_one_year(date_str: str | None) -> bool:
    """ISO/YYYY-MM-DD 발행일이 오늘 기준 1년 이내인지. 파싱 실패 시 True (보수적)."""
    if not date_str:
        return True
    from datetime import date, datetime, timedelta
    s = str(date_str).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            d = datetime.strptime(s, fmt).date()
            return (date.today() - d) <= timedelta(days=365)
        except ValueError:
            continue
    return True


def _news_for(slug: str, s: Settings) -> dict[str, Any]:
    folder = s.workspace_dir / "news" / slug
    if not folder.exists():
        return {"search_key": None, "report_md": None, "metadata": None, "citations": []}
    # 이중 폴더 패턴: news/{slug}/{search_key}/...
    inner_dirs = [p for p in folder.iterdir() if p.is_dir()]
    inner = inner_dirs[0] if inner_dirs else folder
    report_md_path = inner / "report.md"
    raw_path = inner / "raw.json"
    meta_path = inner / "metadata.json"
    raw = _read_json(raw_path) or {}
    # Perplexity 응답에서 search_results 는 풍부한 메타(date/last_updated/title) 보유.
    # citations 는 URL 만 있는 경우가 많으므로, search_results 의 메타를 URL key 로 미리 인덱싱.
    sr_by_url: dict[str, dict[str, Any]] = {}
    for sr in raw.get("search_results", []) or []:
        if isinstance(sr, dict) and sr.get("url"):
            sr_by_url[sr["url"]] = sr

    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in raw.get("citations", []) or []:
        if isinstance(c, str):
            url = c
            sr = sr_by_url.get(url, {})
            citations.append(
                {
                    "url": url,
                    "title": sr.get("title") or url,
                    # last_updated 우선 (재발행/최신화 시점), 없으면 발행일
                    "date": sr.get("last_updated") or sr.get("date"),
                    "domain": _domain_of(url),
                }
            )
            seen.add(url)
        elif isinstance(c, dict):
            url = c.get("url") or ""
            sr = sr_by_url.get(url, {})
            citations.append(
                {
                    "url": url,
                    "title": c.get("title") or sr.get("title") or url,
                    "date": (
                        sr.get("last_updated")
                        or c.get("date")
                        or c.get("published_at")
                        or sr.get("date")
                    ),
                    "domain": _domain_of(url),
                }
            )
            seen.add(url)
    # citations 가 비었으면 search_results 만으로 구성
    if not citations:
        for url, sr in sr_by_url.items():
            citations.append(
                {
                    "url": url,
                    "title": sr.get("title") or url,
                    "date": sr.get("last_updated") or sr.get("date"),
                    "domain": _domain_of(url),
                }
            )
    # 1년 초과 인용은 제외 (날짜 없는 항목은 보존)
    citations = [c for c in citations if _is_within_one_year(c.get("date"))]
    return {
        "search_key": inner.name,
        "report_md": report_md_path.read_text(encoding="utf-8") if report_md_path.exists() else None,
        "metadata": _read_json(meta_path),
        "citations": citations,
    }


def _domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or url
    except Exception:
        return url


def _excel_dict(r: sqlite3.Row) -> dict[str, Any]:
    keys = [
        "issuer", "request_class", "industry_2026", "industry",
        "rating_prev", "watch_prev", "rating_curr", "watch_curr",
        "universe_prev", "universe_curr_ai", "manager",
        "comment_prev", "comment_curr", "movement",
        "group_name", "ai_judgment", "ai_rationale", "reviewer_final",
    ]
    out: dict[str, Any] = {}
    for i, k in enumerate(keys, start=1):
        out[f"c{i}"] = r[k]
    out.update({k: r[k] for k in keys})
    return out


def _review_status_for(slug: str, con: sqlite3.Connection) -> dict[str, Any]:
    row = con.execute(
        "SELECT status, universe, agree_with_ai, note, reviewed_by, reviewed_at FROM review_status WHERE slug=?",
        (slug,),
    ).fetchone()
    if not row:
        return {
            "status": "none",
            "universe": None,
            "agree_with_ai": None,
            "note": None,
            "reviewed_by": None,
            "reviewed_at": None,
        }
    return {
        "status": row["status"],
        "universe": row["universe"],
        "agree_with_ai": bool(row["agree_with_ai"]) if row["agree_with_ai"] is not None else None,
        "note": row["note"],
        "reviewed_by": row["reviewed_by"],
        "reviewed_at": row["reviewed_at"],
    }


@router.get("/{slug}")
def company_detail(
    slug: str,
    _sess: dict = Depends(require_session),
    s: Settings = Depends(get_settings),
    con: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    row = con.execute("SELECT * FROM companies WHERE slug=?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    if row["unresolved"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unresolved")

    period = _load_period(con)
    master = _master_for(slug, s)
    stage2, inversion = _stage2_for(slug, s)

    return {
        "period": period,
        "master": master,
        "excel": _excel_dict(row),
        "comment": _comment_for(slug, s),
        "stage2": stage2,
        "inversion": inversion,
        "nice": _nice_for(slug, s, master.get("cmp_cd")),
        "dart": _dart_for(slug, s),
        "news": _news_for(slug, s),
        "review_status": _review_status_for(slug, con),
        "history": [],
    }


@router.get("/{slug}/dart/{kind}.txt")
def dart_text(
    slug: str,
    kind: str,
    _sess: dict = Depends(require_session),
    s: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if kind not in {"business", "notes"}:
        raise HTTPException(status_code=400, detail="invalid_kind")
    folder = s.workspace_dir / "dart" / slug
    candidates = [folder / f"{kind}.txt", folder / f"{kind}_section.txt"]
    for p in candidates:
        if p.exists():
            return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind}_not_found")


def _dart_xml_to_html(raw: str) -> str:
    """
    DART scraper produces a wrapper HTML whose <pre> contains the original
    SECTION-1 XML, fully HTML-escaped. We extract that, unescape it, and map
    the non-standard tags (SECTION-1/-2/TITLE/LIBRARY/P) to standard HTML so
    the table structure renders as a real table in the browser.
    """
    import html
    import re

    # 1) Extract the body of <pre>...</pre> (case-insensitive)
    m = re.search(r"<pre[^>]*>(.*?)</pre>", raw, flags=re.DOTALL | re.IGNORECASE)
    inner = m.group(1) if m else raw
    # 2) Unescape entities (&lt; → <, &amp; → &, etc.)
    inner = html.unescape(inner)
    # 3) Map non-standard DART XML tags to HTML
    #    Lowercase + simple element rewrites. Attributes are preserved.
    tag_map = {
        "SECTION-1": "section",
        "SECTION-2": "section",
        "SECTION-3": "section",
        "TABLE-GROUP": "div",
        "LIBRARY": "div",
        "PGBRK": "div",
        "TU": "div",
        "TITLE": "h3",  # TITLE in DART is a section title, not <head><title>
        "TE": "td",     # DART의 TE는 표준 td 의미 — 누락 시 셀 자체가 사라져 텍스트가 표 밖으로 흘러나옴
        "SPAN": "span",
        "A": "span",    # DART의 A는 anchor지만 href가 없어 동작 안 함 → 인라인 span으로
    }
    for src, dst in tag_map.items():
        inner = re.sub(rf"<{src}\b", f"<{dst}", inner)
        inner = re.sub(rf"</{src}>", f"</{dst}>", inner)
    # 4) Lowercase remaining standard table/text tags so DOMPurify sees them as expected
    for std in ("TABLE", "TR", "TD", "TH", "THEAD", "TBODY", "TFOOT", "COLGROUP", "COL", "P"):
        inner = re.sub(rf"<{std}\b", f"<{std.lower()}", inner)
        inner = re.sub(rf"</{std}>", f"</{std.lower()}>", inner)
    # 5) Drop self-closing empty paragraphs (DART XML에 다수 존재 — 표·단락 사이 가짜 여백 유발)
    inner = re.sub(r"<p\s*/>", "", inner)
    inner = re.sub(r"<p>\s*</p>", "", inner)

    # 6) Split long <p> bodies on [topic] markers and "가./나./다." style sub-headings.
    #    DART 사업보고서는 한 <P> 안에 여러 토픽이 [...]로 인라인 구분되어 한 덩어리로 들어옴.
    #    각 [topic]을 새 단락의 시작으로 분리하고 굵게 표시한다.
    def _split_paragraph(match: "re.Match[str]") -> str:
        body = match.group(1)
        if "[" not in body and not re.search(r"(?:가|나|다|라|마|바|사|아)\.\s", body):
            return match.group(0)
        # 토픽 분리: 본문 시작이 아닌 위치의 "[..]" 앞에서 단락 분기
        parts = re.split(r"(?=(?<!^)\[(?:[^\[\]\n]{1,40})\])", body)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) <= 1:
            return match.group(0)
        rendered = []
        for p in parts:
            m2 = re.match(r"^\[([^\[\]\n]{1,40})\](.*)$", p, flags=re.DOTALL)
            if m2:
                head, rest = m2.group(1), m2.group(2).strip()
                rendered.append(
                    f'<p><strong>[{head}]</strong>{(" " + rest) if rest else ""}</p>'
                )
            else:
                rendered.append(f"<p>{p}</p>")
        return "\n".join(rendered)

    inner = re.sub(
        r"<p>(.*?)</p>",
        _split_paragraph,
        inner,
        flags=re.DOTALL,
    )

    # 7) Inline single-line breaks like "(*) note 1.(*) note 2." into separate lines.
    #    "(*) ...(*) ..." 패턴은 각 항목을 별 단락으로 분리.
    inner = re.sub(r"\(\*\)\s*", "<br/>(*) ", inner)
    return inner


@router.get("/{slug}/dart/{kind}.html")
def dart_html(
    slug: str,
    kind: str,
    _sess: dict = Depends(require_session),
    s: Settings = Depends(get_settings),
) -> Response:
    if kind not in {"business", "notes"}:
        raise HTTPException(status_code=400, detail="invalid_kind")
    folder = s.workspace_dir / "dart" / slug
    candidates = [folder / f"{kind}.html", folder / f"{kind}_section.html"]
    for p in candidates:
        if p.exists():
            raw = p.read_text(encoding="utf-8")
            return Response(
                content=_dart_xml_to_html(raw),
                media_type="text/html; charset=utf-8",
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind}_html_not_found")


@router.get("/{slug}/opinion.pdf")
def opinion_pdf(
    slug: str,
    _sess: dict = Depends(require_session),
    s: Settings = Depends(get_settings),
) -> FileResponse:
    p = s.workspace_dir / "nice" / slug / "opinion.pdf"
    if not p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="opinion_pdf_not_found")
    # inline 으로 반환해야 <object> / <iframe> 임베드가 동작.
    # 다운로드는 프론트의 <a download> 속성이 처리.
    return FileResponse(
        p,
        media_type="application/pdf",
        filename=f"{slug}_opinion.pdf",
        content_disposition_type="inline",
    )
