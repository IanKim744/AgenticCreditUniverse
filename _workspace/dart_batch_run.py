#!/usr/bin/env python3
"""19개 신규 매핑 종목의 DART 자료(사업의 내용 + 연결재무제표 주석) 일괄 수집.

기존 3종목(대한해운/한솔테크닉스/에스케이씨)은 캐시 보호 — 절대 건드리지 않는다.
24h 이내 metadata.json이 있는 종목은 자동 스킵.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/kim-youngbyeok/AgenticCreditUniverse/AgenticCreditUniverse")
VENV_PY = ROOT / ".venv" / "bin" / "python"
SCRAPER = ROOT / "AgenticCreditUniverse" / "dart_scraper" / "dart_scraper.py"
SECRETS_ENV = ROOT / "AgenticCreditUniverse" / "secrets.env"
DART_OUT_BASE = ROOT / "_workspace" / "dart"
LOG_PATH = DART_OUT_BASE / "_batch_run.log"

PROTECTED = {"대한해운", "한솔테크닉스", "에스케이씨"}

TARGETS: list[tuple[str, str]] = [
    ("다우기술", "00176914"),
    ("롯데물산", "00120483"),
    ("보령(구. 보령제약)", "00123143"),
    ("부산롯데호텔", "00124212"),
    ("씨제이프레시웨이", "00127954"),
    ("알씨아이파이낸셜서비스코리아", "00573551"),
    ("에스케이디스커버리", "00131832"),
    ("에스케이스페셜티(구. 에스케이머티리얼즈)", "01602124"),
    ("에스케이실트론", "00138020"),
    ("에스케이온", "01592447"),
    ("에이치라인해운", "01010660"),
    ("한솔제지", "01060744"),
    ("한솔케미칼", "00140955"),
    ("한일시멘트", "01319808"),
    ("한화리츠", "01669226"),
    ("현대로템", "00302926"),
    ("현대리바트", "00300548"),
    ("현대비앤지스틸", "00125743"),
    ("에스케이네트웍스서비스", "00636081"),
]


def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k.strip()] = v
    return env


def is_fresh(meta_path: Path, hours: int = 24) -> bool:
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    gen = meta.get("generated_at")
    if not gen:
        # 파일 mtime 기반 폴백
        age = time.time() - meta_path.stat().st_mtime
        return age < hours * 3600
    try:
        ts = datetime.fromisoformat(gen.replace("Z", "+00:00"))
    except Exception:
        return False
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age < hours * 3600


def file_size_label(path: Path) -> str:
    if not path.exists():
        return "0B"
    size = path.stat().st_size
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f}MB"
    if size >= 1024:
        return f"{size / 1024:.0f}KB"
    return f"{size}B"


def run_one(slug: str, corp_code: str, env: dict[str, str]) -> dict:
    out_dir = DART_OUT_BASE / slug
    meta_path = out_dir / "metadata.json"

    if slug in PROTECTED:
        return {"slug": slug, "status": "protected_skip", "msg": "보호 종목 — 건드리지 않음"}

    if is_fresh(meta_path, 24):
        return {"slug": slug, "status": "cache_hit", "msg": "metadata.json 24h 이내 — 스킵"}

    out_dir.mkdir(parents=True, exist_ok=True)

    # 사업보고서 우선 → 실패 시 any 폴백 (감사보고서 등은 dart_scraper가 정기보고서만 검색하므로
    # 비상장사면 report_type=any 로도 결과가 없을 수 있음. 단계 폴백.)
    attempts = [
        ["--report-type", "A001"],
        ["--report-type", "any"],
    ]

    last_stdout = ""
    last_stderr = ""
    last_rc = -1

    for extra in attempts:
        cmd = [
            str(VENV_PY),
            str(SCRAPER),
            "--corp-code", corp_code,
            "--outdir", str(out_dir),
            "--prefer", "consolidated",
            "--non-interactive",
            "-v",
        ] + extra
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(SCRAPER.parent),
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            last_rc = proc.returncode
            last_stdout = proc.stdout
            last_stderr = proc.stderr
        except subprocess.TimeoutExpired as exc:
            last_rc = -1
            last_stdout = ""
            last_stderr = f"Timeout after 300s: {exc}"
            continue

        if last_rc == 0 and meta_path.exists():
            break

    # business / notes 정규화 파일 (business.txt / notes.txt)
    if (out_dir / "business_section.txt").exists() and not (out_dir / "business.txt").exists():
        (out_dir / "business.txt").write_bytes((out_dir / "business_section.txt").read_bytes())
    if (out_dir / "notes_section.txt").exists() and not (out_dir / "notes.txt").exists():
        (out_dir / "notes.txt").write_bytes((out_dir / "notes_section.txt").read_bytes())

    if last_rc != 0 or not meta_path.exists():
        # 메타가 없으면 실패 메타 작성
        fail_meta = {
            "corp": {"corp_code": corp_code, "corp_name": slug},
            "status": "no_report",
            "report_type_name": None,
            "business_section": {"status": "fail"},
            "notes_section": {"status": "fail"},
            "errors": [
                {"rc": last_rc, "stderr_tail": (last_stderr or "")[-500:]},
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path.write_text(json.dumps(fail_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "slug": slug,
            "status": "fail",
            "msg": (last_stderr or last_stdout or "unknown error")[-300:],
        }

    # 성공 시 metadata 요약
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    report_nm = meta.get("report", {}).get("report_nm") or meta.get("report_type_name") or "?"
    rcept_dt = meta.get("report", {}).get("rcept_dt") or "?"
    biz_status = meta.get("business_section", {}).get("status")
    notes_status = meta.get("notes_section", {}).get("status")
    notes_variant = meta.get("notes_section", {}).get("variant")
    biz_size = file_size_label(out_dir / "business.txt")
    notes_size = file_size_label(out_dir / "notes.txt")

    return {
        "slug": slug,
        "status": "ok",
        "msg": (
            f"{report_nm} ({rcept_dt}), "
            f"business={biz_status}/{biz_size}, "
            f"notes={notes_status}({notes_variant})/{notes_size}"
        ),
    }


def main() -> int:
    if not VENV_PY.exists():
        print(f"FATAL: venv python not found: {VENV_PY}", file=sys.stderr)
        return 2
    if not SCRAPER.exists():
        print(f"FATAL: dart_scraper not found: {SCRAPER}", file=sys.stderr)
        return 2

    secrets = load_dotenv(SECRETS_ENV)
    if "DART_API_KEY" not in secrets or not secrets["DART_API_KEY"]:
        print("FATAL: DART_API_KEY not in secrets.env", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.update(secrets)

    DART_OUT_BASE.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    results: list[dict] = []

    print(f"=== DART 일괄 수집 시작 / 대상 {len(TARGETS)}종목 ===", flush=True)

    for idx, (slug, corp_code) in enumerate(TARGETS, start=1):
        t0 = time.time()
        res = run_one(slug, corp_code, env)
        dt = time.time() - t0
        line = f"[{idx:02d}/{len(TARGETS)}] {slug}: {res['status']} | {res['msg']} | {dt:.1f}s"
        print(line, flush=True)
        log_lines.append(line)
        results.append(res)
        # 캐시 히트나 보호 스킵은 sleep 불필요
        if res["status"] in ("ok", "fail"):
            time.sleep(random.uniform(0.5, 1.0))

    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    # 요약 출력
    ok = sum(1 for r in results if r["status"] == "ok")
    cached = sum(1 for r in results if r["status"] == "cache_hit")
    protected = sum(1 for r in results if r["status"] == "protected_skip")
    failed = [r for r in results if r["status"] == "fail"]

    print()
    print(f"=== 요약: 성공 {ok}/{len(TARGETS)} (캐시 {cached}, 보호 {protected}, 실패 {len(failed)}) ===")
    for r in results:
        print(f"  - {r['slug']}: {r['status']} | {r['msg']}")
    if failed:
        print()
        print("실패 종목:")
        for r in failed:
            print(f"  - {r['slug']}: {r['msg']}")

    summary_path = DART_OUT_BASE / "_batch_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total": len(TARGETS),
                "ok": ok,
                "cache_hit": cached,
                "protected_skip": protected,
                "fail": len(failed),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
