"""NICE cmpcd 매핑 헬퍼.

`nicerating_scraper.NiceRatingScraper.resolve_cmpcd()` 가 다중 매칭 시
즉시 ValueError를 던지는 한계를 우회한다.
NICE 검색 결과 페이지의 onclick="goView('BOND', cmpcd)" 패턴에서
(정식 사명, cmpcd) 페어를 추출하여 정확 사명 매칭으로 자동 선택한다.

사용자 모듈(nicerating_scraper.py)은 변경하지 않는다.
"""
from __future__ import annotations

import re
import sys
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

_NICE_SCRAPER_DIR = (
    "/Users/kim-youngbyeok/AgenticCreditUniverse/AgenticCreditUniverse/"
    "AgenticCreditUniverse/nicerating_scraper"
)


def _import_nrs():
    if _NICE_SCRAPER_DIR not in sys.path:
        sys.path.insert(0, _NICE_SCRAPER_DIR)
    import nicerating_scraper as nrs  # noqa: WPS433
    return nrs


def resolve_cmpcd(
    scraper,
    query: str,
    exact_name: Optional[str] = None,
) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """NICE 검색 → cmpcd 결정.

    Args:
        scraper: `NiceRatingScraper` 인스턴스
        query: 검색어(부분 매칭 허용)
        exact_name: 정확 사명. 다중 매칭 시 이 이름과 일치하는 후보 우선 선택.

    Returns:
        (chosen_cmpcd_or_None, all_candidates)
        - chosen_cmpcd: 단일 redirect 매칭 / 정확 매칭 / 단일 후보 시 채택된 cmpcd
        - all_candidates: [(사명, cmpcd), ...] — unresolved 처리용
    """
    nrs = _import_nrs()

    resp = scraper._get(
        "/search/search.do",
        params={"mainSType": "CMP", "mainSText": query.strip()},
    )

    # 단일 매칭이면 NICE 가 자동 redirect → URL 에 cmpcd 가 박혀 있음
    direct = nrs._extract_cmpcd_from_url(resp.url)
    if direct:
        return direct, [(query, direct)]

    # 다중 매칭 페이지에서 goView('BOND', cmpcd) 패턴 파싱.
    # NICE 페이지는 항목별로 두 가지 형태를 섞어 사용:
    #   1) <element onclick="goView(...)">사명</element>
    #   2) <a href="javascript:goView(...)">사명</a>
    # 두 패턴 모두 잡아야 누락이 없다.
    soup = BeautifulSoup(resp.text, "html.parser")
    pat = re.compile(r"goView\s*\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]?(\d+)")
    pairs: list[tuple[str, str]] = []

    def _push(name: str, cmp: str) -> None:
        # "[기업상세]" 같은 액션 라벨은 사명이 아니므로 제외
        if not name or name.startswith("["):
            return
        pairs.append((name, cmp))

    for el in soup.find_all(attrs={"onclick": True}):
        m = pat.search(el.get("onclick", ""))
        if m:
            _push(el.get_text(strip=True), m.group(1))
    for a in soup.find_all("a", href=True):
        m = pat.search(a.get("href", ""))
        if m:
            _push(a.get_text(strip=True), m.group(1))

    # dedupe (이름·cmpcd 조합 기준)
    seen, candidates = set(), []
    for name, cmp in pairs:
        if (name, cmp) in seen:
            continue
        seen.add((name, cmp))
        candidates.append((name, cmp))

    # 1) 정확 사명 매칭이 있으면 그것 채택
    if exact_name:
        match = [c for n, c in candidates if n == exact_name]
        if match:
            return match[0], candidates

    # 2) 후보가 1개뿐이면 그것 채택
    if len(candidates) == 1:
        return candidates[0][1], candidates

    # 3) 다중 후보 + 정확 매칭 없음 → 호출자가 unresolved 처리
    return None, candidates


def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    import json

    nrs = _import_nrs()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True, help="NICE 검색어 (예: '에스케이씨')")
    ap.add_argument(
        "--exact-name",
        default=None,
        help="정식 사명 (예: '에스케이씨(주)'). 다중 매칭 시 이 이름과 일치하는 후보 자동 채택.",
    )
    args = ap.parse_args(argv)

    scraper = nrs.NiceRatingScraper()
    cmp, cands = resolve_cmpcd(scraper, args.query, args.exact_name)
    print(
        json.dumps(
            {"cmp_cd": cmp, "candidates": cands, "candidate_count": len(cands)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if cmp else 1


if __name__ == "__main__":
    sys.exit(main())
