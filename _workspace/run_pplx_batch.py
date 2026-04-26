#!/usr/bin/env python3
"""Batch driver for pplx_risk_analyst across the 19 newly-mapped tickers.

- Skips any ticker whose metadata.json is < 3 days old (cache).
- Sequential to respect Perplexity rate limits.
- Sleeps ~75s between calls.
- Records per-ticker status in stdout.
- Default api: sonar (sonar-pro) per user instruction.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/Users/kim-youngbyeok/AgenticCreditUniverse/AgenticCreditUniverse")
VENV_PY = ROOT / ".venv" / "bin" / "python"
SCRIPT = ROOT / "AgenticCreditUniverse" / "pplx_news" / "pplx_risk_analyst.py"
NEWS_BASE = ROOT / "_workspace" / "news"
SECRETS = ROOT / "AgenticCreditUniverse" / "secrets.env"

# (folder_slug, search_key)
TARGETS = [
    ("다우기술", "다우기술"),
    ("롯데물산", "롯데물산"),
    ("보령(구. 보령제약)", "보령제약"),
    ("부산롯데호텔", "부산롯데호텔"),
    ("씨제이프레시웨이", "CJ프레시웨이"),
    ("알씨아이파이낸셜서비스코리아", "RCI Financial Services Korea"),
    ("에스케이디스커버리", "SK디스커버리"),
    ("에스케이스페셜티(구. 에스케이머티리얼즈)", "SK스페셜티"),
    ("에스케이실트론", "SK실트론"),
    ("에스케이온", "SK온"),
    ("에이치라인해운", "H-Line해운"),
    ("한솔제지", "한솔제지"),
    ("한솔케미칼", "한솔케미칼"),
    ("한일시멘트", "한일시멘트"),
    ("한화리츠", "한화리츠"),
    ("현대로템", "현대로템"),
    ("현대리바트", "현대리바트"),
    ("현대비앤지스틸", "현대비앤지스틸"),
    ("에스케이네트웍스서비스", "SK네트웍스서비스"),
]


def slugify(text: str, max_len: int = 60) -> str:
    """Mirror pplx_risk_analyst.slugify so we can locate {search_key} subdir."""
    import re

    s = (text or "").strip().lower()
    s = re.sub(r"[\s/\\?%*:|\"<>.,;!#@$^&()\[\]{}=+`~']+", "-", s)
    s = "".join(ch for ch in s if ch.isalnum() or ch == "-" or ord(ch) > 127)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s or "company")[:max_len]


def load_secrets() -> dict:
    env = os.environ.copy()
    if SECRETS.exists():
        for raw in SECRETS.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, v = raw.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def cache_fresh(meta_path: Path, days: int = 3) -> bool:
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        ts = meta.get("generated_utc")
        if not ts:
            return False
        gen = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - gen) < timedelta(days=days)
    except Exception:
        return False


def run_one(folder_slug: str, search_key: str, env: dict, sleep_after: int = 75) -> dict:
    out = {"folder": folder_slug, "search_key": search_key, "status": "", "msg": "",
           "tokens": 0, "cost": 0.0, "citations": 0}

    target_dir = NEWS_BASE / folder_slug / slugify(search_key)
    meta_path = target_dir / "metadata.json"

    if cache_fresh(meta_path):
        out["status"] = "skip-cache"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            usage = meta.get("usage") or {}
            out["tokens"] = usage.get("total_tokens", 0)
            cost = usage.get("cost") or {}
            out["cost"] = cost.get("total_cost", 0.0)
            out["citations"] = meta.get("n_citations", 0)
        except Exception:
            pass
        out["msg"] = f"cache fresh at {target_dir}"
        return out

    outdir = NEWS_BASE / folder_slug
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(VENV_PY),
        str(SCRIPT),
        "--name", search_key,
        "--outdir", str(outdir),
        "--api", "sonar",
        "--model", "sonar-pro",
        "--max-tokens", "4000",
    ]
    print(f"\n=== [{folder_slug}] search='{search_key}' ===", flush=True)
    print("  CMD:", " ".join(cmd), flush=True)

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(SCRIPT.parent),
            env=env,
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        out["status"] = "fail"
        out["msg"] = "timeout 600s"
        return out

    dt = time.time() - t0
    if proc.returncode != 0:
        out["status"] = "fail"
        # surface tail of stderr for diagnostics
        tail = (proc.stderr or "").strip().splitlines()[-5:]
        out["msg"] = f"rc={proc.returncode} dt={dt:.1f}s :: " + " | ".join(tail)
        return out

    # success — read metadata
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        usage = meta.get("usage") or {}
        out["tokens"] = usage.get("total_tokens", 0)
        cost = usage.get("cost") or {}
        out["cost"] = cost.get("total_cost", 0.0)
        out["citations"] = meta.get("n_citations", 0)
        out["status"] = "ok"
        out["msg"] = f"dt={dt:.1f}s"
    except Exception as e:
        out["status"] = "ok-no-meta"
        out["msg"] = f"dt={dt:.1f}s; meta read failed: {e}"

    # rate-limit cooldown
    print(f"  sleeping {sleep_after}s …", flush=True)
    time.sleep(sleep_after)
    return out


def main() -> int:
    env = load_secrets()
    if not env.get("PERPLEXITY_API_KEY"):
        print("ERROR: PERPLEXITY_API_KEY missing", file=sys.stderr)
        return 2

    results = []
    for folder, key in TARGETS:
        r = run_one(folder, key, env, sleep_after=75)
        results.append(r)
        print(f"[{r['status']}] {folder}: search='{r['search_key']}' "
              f"tokens={r['tokens']} cost=${r['cost']:.4f} cites={r['citations']} :: {r['msg']}",
              flush=True)

    # summary
    total_cost = sum(r["cost"] or 0 for r in results)
    ok = sum(1 for r in results if r["status"] in ("ok", "ok-no-meta"))
    skip = sum(1 for r in results if r["status"] == "skip-cache")
    fail = sum(1 for r in results if r["status"] == "fail")

    print("\n" + "=" * 60)
    print(f"SUMMARY: ok={ok} skip={skip} fail={fail} / {len(results)}")
    print(f"TOTAL COST: ${total_cost:.4f}")
    print("=" * 60)
    for r in results:
        print(f"  - {r['folder']}: {r['status']} (search='{r['search_key']}', "
              f"tokens={r['tokens']}, cost=${r['cost']:.4f}) :: {r['msg']}")

    # save summary
    summary_path = NEWS_BASE / "_batch_summary.json"
    summary_path.write_text(
        json.dumps({"results": results, "total_cost": total_cost,
                    "ok": ok, "skip": skip, "fail": fail,
                    "completed_at": datetime.now(timezone.utc).isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\nsummary saved → {summary_path}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
