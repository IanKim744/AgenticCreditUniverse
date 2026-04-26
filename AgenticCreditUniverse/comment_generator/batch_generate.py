"""26.1H 코멘트 일괄 생성 — Anthropic ITPM 한도 회피용 자동 sleep + 429 백오프.

종목 N개를 순차 처리하면서 호출 사이에 자동 sleep(기본 90초) 을 삽입한다.
호출 중 RateLimitError(429)가 발생하면 추가 60초 백오프 후 1회 재시도한다.

사용 예:
  python batch_generate.py \\
    --jobs jobs.json \\
    --output-dir _workspace/comments/ \\
    --env-file ../secrets.env

jobs.json 스키마:
  [
    {
      "company": "대한해운",
      "pdf": "_workspace/nice/대한해운/opinion.pdf",   # 선택
      "nice": "_workspace/nice/대한해운/indicators.json",
      "dart_business": "_workspace/dart/대한해운/business.txt",
      "news":          "_workspace/news/대한해운/대한해운/report.md",
      "grade_info":    "그룹사: SM"
    },
    ...
  ]

NOTE: DART 연결재무제표 주석(`dart_notes`)은 토큰 폭주 원인이라 코멘트 생성에서 제외.
      jobs.json 에 들어있더라도 무시한다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import anthropic

from generate_comment import generate_comment, load_env_file


def _build_kwargs(job: dict, max_tokens: int, enable_1m_context: bool) -> dict:
    """jobs.json 의 한 항목을 generate_comment 인자로 변환.

    `dart_notes` 키는 의도적으로 무시한다(토큰 폭주 원인 — 코멘트 생성에 미사용).
    """
    return dict(
        company=job["company"],
        pdf_path=Path(job["pdf"]) if job.get("pdf") else None,
        nice_path=Path(job["nice"]) if job.get("nice") else None,
        dart_business_path=Path(job["dart_business"]) if job.get("dart_business") else None,
        news_path=Path(job["news"]) if job.get("news") else None,
        grade_info=job.get("grade_info"),
        max_tokens=max_tokens,
        enable_1m_context=enable_1m_context,
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs", required=True, type=Path, help="jobs JSON 경로")
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "secrets.env",
        help="API 키 env 파일 (기본: ../secrets.env)",
    )
    p.add_argument(
        "--sleep-seconds",
        type=int,
        default=90,
        help="종목간 sleep (Anthropic ITPM 한도 회피, 기본 90s)",
    )
    p.add_argument(
        "--rate-limit-backoff",
        type=int,
        default=60,
        help="RateLimitError 발생 시 추가 백오프 (기본 60s)",
    )
    p.add_argument("--no-1m-context", action="store_true")
    p.add_argument("--max-tokens", type=int, default=4096)
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        load_env_file(args.env_file)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(args.jobs.read_text(encoding="utf-8"))
    if not isinstance(jobs, list) or not jobs:
        print("[ERROR] jobs.json must be a non-empty array", file=sys.stderr)
        return 2

    enable_1m = not args.no_1m_context
    results: list[dict] = []
    total_in = total_out = total_cache_read = total_cache_create = 0

    for i, job in enumerate(jobs):
        company = job.get("company")
        if not company:
            print(f"[WARN] job[{i}] missing 'company' — skipped", file=sys.stderr)
            continue

        if i > 0:
            print(
                f"[sleep {args.sleep_seconds}s — ITPM cooldown]", file=sys.stderr
            )
            time.sleep(args.sleep_seconds)

        out_path = args.output_dir / f"{company}.json"
        print(f"=== [{i + 1}/{len(jobs)}] {company} ===", file=sys.stderr)

        kwargs = _build_kwargs(job, args.max_tokens, enable_1m)
        retried = False
        try:
            res = generate_comment(**kwargs)
        except anthropic.RateLimitError:
            print(
                f"[rate limit — extra {args.rate_limit_backoff}s backoff]",
                file=sys.stderr,
            )
            time.sleep(args.rate_limit_backoff)
            retried = True
            try:
                res = generate_comment(**kwargs)
            except Exception as e:  # noqa: BLE001
                print(
                    f"[FAIL after retry] {company}: {type(e).__name__}: {e}",
                    file=sys.stderr,
                )
                results.append(
                    {
                        "company": company,
                        "ok": False,
                        "retried": True,
                        "error": f"{type(e).__name__}: {e}",
                    }
                )
                continue
        except anthropic.APIStatusError as e:
            # 키 노출 방지: status/type 만 출력
            print(
                f"[API ERROR] {company}: status={e.status_code} type={type(e).__name__}",
                file=sys.stderr,
            )
            results.append(
                {
                    "company": company,
                    "ok": False,
                    "error": f"APIStatusError(status={e.status_code})",
                }
            )
            continue
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {company}: {type(e).__name__}: {e}", file=sys.stderr)
            results.append(
                {
                    "company": company,
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
            continue

        out_path.write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        u = res.get("usage", {})
        total_in += u.get("input_tokens", 0)
        total_out += u.get("output_tokens", 0)
        total_cache_read += u.get("cache_read_input_tokens", 0)
        total_cache_create += u.get("cache_creation_input_tokens", 0)
        comment_len = len(res.get("comment", ""))
        judgment = res.get("judgment_stage1")
        results.append(
            {
                "company": company,
                "ok": True,
                "retried": retried,
                "len": comment_len,
                "len_in_range": 400 <= comment_len <= 600,
                "judgment_stage1": judgment,
                "judgment_parsed": judgment is not None,
                "usage": u,
            }
        )
        judgment_tag = f" judg={judgment}" if judgment else " judg=NONE"
        print(
            f"  → {comment_len}자{judgment_tag} | in={u.get('input_tokens')} "
            f"out={u.get('output_tokens')} "
            f"cache_read={u.get('cache_read_input_tokens', 0)}"
            f"{'  (RETRIED)' if retried else ''}",
            file=sys.stderr,
        )

    summary = {
        "results": results,
        "totals": {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cache_read_input_tokens": total_cache_read,
            "cache_creation_input_tokens": total_cache_create,
        },
        "ok_count": sum(1 for r in results if r.get("ok")),
        "fail_count": sum(1 for r in results if not r.get("ok")),
        "len_violations": [
            r["company"]
            for r in results
            if r.get("ok") and not r.get("len_in_range")
        ],
        "judgment_missing_count": sum(
            1 for r in results if r.get("ok") and not r.get("judgment_parsed")
        ),
        "judgment_missing": [
            r["company"]
            for r in results
            if r.get("ok") and not r.get("judgment_parsed")
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
