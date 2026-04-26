#!/usr/bin/env python3
"""Batch NICE 의견서 PDF collector.

For every company folder under `_workspace/nice/{slug}/` that doesn't already
have an `opinion.pdf`, this script:
  1) reads `cmp_cd` from `_workspace/master/master.json`,
  2) downloads the latest rating PDF via `nicerating_scraper.NiceRatingScraper`,
  3) copies/symlinks it as `opinion.pdf`,
  4) writes `opinion_meta.json` with agency / 공시일 / 유효기간 / 등급 / 채권 정보.

Usage:
    python scripts/collect_opinions.py
    python scripts/collect_opinions.py --slug 롯데물산   # single
    python scripts/collect_opinions.py --force          # re-download even if opinion.pdf exists
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE = ROOT / "_workspace"
NICE_DIR = WORKSPACE / "nice"
MASTER = WORKSPACE / "master" / "master.json"
SCRAPER_DIR = ROOT / "AgenticCreditUniverse" / "nicerating_scraper"

sys.path.insert(0, str(SCRAPER_DIR))
import nicerating_scraper as nrs  # noqa: E402

log = logging.getLogger("collect_opinions")


def load_master() -> dict[str, dict]:
    return json.loads(MASTER.read_text(encoding="utf-8"))["companies"]


def parse_iso_date(s: str | None) -> str | None:
    """'2026.01.29' or '2026-01-29' → '2026-01-29'."""
    if not s:
        return None
    s2 = s.replace(".", "-").strip()
    try:
        d = datetime.strptime(s2, "%Y-%m-%d").date()
        return d.isoformat()
    except ValueError:
        return None


def collect_one(slug: str, cmp_cd: str, *, force: bool = False) -> dict:
    folder = NICE_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    canonical = folder / "opinion.pdf"
    meta_path = folder / "opinion_meta.json"
    if canonical.exists() and not force:
        return {"slug": slug, "skipped": True, "reason": "already_exists"}

    scraper = nrs.NiceRatingScraper()
    try:
        rating, pdf_path = scraper.download_latest_rating_pdf(cmp_cd, outdir=str(folder))
    except Exception as e:
        return {"slug": slug, "error": str(e)}

    pdf_path = Path(pdf_path)
    # canonical 복사 (원본도 보존)
    if canonical.resolve() != pdf_path.resolve():
        shutil.copyfile(pdf_path, canonical)

    issued = parse_iso_date(rating.determined_date)
    valid_until = None
    if issued:
        try:
            d = datetime.fromisoformat(issued)
            valid_until = (d + timedelta(days=365)).date().isoformat()
        except ValueError:
            pass

    meta = {
        "agency": "NICE신용평가",
        "rating_type": rating.rating_type,
        "bond_series": rating.bond_series,
        "bond_kind": rating.bond_kind,
        "current_grade": rating.current_grade,
        "issued_date": issued,
        "valid_until": valid_until,
        "validity_note": "다음 정기평가 또는 등급 액션 시까지 유효 (공시일 +1년 표기)",
        "original_filename": pdf_path.name,
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slug": slug, "ok": True, "grade": rating.current_grade, "issued": issued}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", help="단일 종목만 처리")
    p.add_argument("--force", action="store_true", help="opinion.pdf 가 있어도 재다운로드")
    p.add_argument("--delay", type=float, default=1.5, help="종목 사이 대기(초)")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    master = load_master()

    targets: list[tuple[str, str]] = []
    if args.slug:
        info = master.get(args.slug)
        if not info or not info.get("cmp_cd"):
            log.error("master.json 에 %s 의 cmp_cd 가 없습니다", args.slug)
            sys.exit(2)
        targets.append((args.slug, info["cmp_cd"]))
    else:
        # 모든 nice 폴더 종목 중 master 에 cmp_cd 있는 것
        for d in sorted(NICE_DIR.iterdir()):
            if not d.is_dir():
                continue
            slug = d.name
            info = master.get(slug)
            if not info or not info.get("cmp_cd"):
                log.warning("skip %s: master 에 cmp_cd 없음", slug)
                continue
            targets.append((slug, info["cmp_cd"]))

    log.info("대상 종목 %d개", len(targets))
    results = []
    for i, (slug, cmp_cd) in enumerate(targets, 1):
        log.info("[%d/%d] %s (cmp_cd=%s)", i, len(targets), slug, cmp_cd)
        r = collect_one(slug, cmp_cd, force=args.force)
        results.append(r)
        if r.get("ok"):
            log.info("  ✓ 등급=%s 공시일=%s", r.get("grade"), r.get("issued"))
        elif r.get("skipped"):
            log.info("  · 건너뜀: %s", r.get("reason"))
        else:
            log.error("  ✗ 실패: %s", r.get("error"))
        if i < len(targets):
            time.sleep(args.delay)

    ok = sum(1 for r in results if r.get("ok"))
    skipped = sum(1 for r in results if r.get("skipped"))
    failed = sum(1 for r in results if r.get("error"))
    log.info("완료: 신규 %d / 건너뜀 %d / 실패 %d", ok, skipped, failed)
    if failed:
        for r in results:
            if r.get("error"):
                log.error("  - %s: %s", r["slug"], r["error"])


if __name__ == "__main__":
    main()
