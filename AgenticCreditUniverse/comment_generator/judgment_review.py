"""26.1H 유니버스 포함여부 — Stage 2 (judgment-reviewer) 호출 모듈.

Stage 1 산출물(_workspace/comments/{회사}.json) + 기존 유니버스 엑셀을 입력으로,
풀 단위 형평성·안정성 가드레일을 적용한 최종 판단을 산출한다.

산출: _workspace/judgment/stage2_review.json

사용 예:
  python judgment_review.py \\
    --comments-dir _workspace/comments/ \\
    --xlsx "AgenticCreditUniverse/legacy version/26.1Q 유니버스_작업완료.xlsx" \\
    --grade-input _workspace/grade_input.json \\
    --env-file ../secrets.env \\
    --output _workspace/judgment/stage2_review.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import anthropic

from extract_existing_universe import extract as extract_existing
from generate_comment import load_env_file
from prompt_template_judgment import JUDGMENT_SYSTEM_PROMPT


_GUARDRAIL_LIMIT = 0.10
_MONITORING_RE = re.compile(r"모니터링\s*포인트[^\n]*[:：](.+?)$", re.DOTALL)


def _extract_monitoring(comment: str) -> str:
    """코멘트 본문에서 '모니터링 포인트:' 단락 추출. 없으면 마지막 200자."""
    m = _MONITORING_RE.search(comment)
    if m:
        text = m.group(1).strip()
    else:
        text = comment[-300:].strip()
    # Stage 2 입력 압축: 200자 제한
    return text[:200]


def _load_review_companies(
    comments_dir: Path,
    grade_input: dict[str, dict[str, str]],
    prior_lookup: dict[str, str | None],
) -> list[dict[str, Any]]:
    """comments/*.json 파일을 읽어 review_companies 리스트 구성."""
    rows: list[dict[str, Any]] = []
    for f in sorted(comments_dir.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        name = rec.get("company")
        if not name:
            continue
        grade_info = grade_input.get(name, {})
        rows.append(
            {
                "name": name,
                "grade": grade_info.get("rating"),
                "outlook": grade_info.get("outlook"),
                "stage1": rec.get("judgment_stage1"),
                "stage1_reason": rec.get("judgment_stage1_reason"),
                "monitoring": _extract_monitoring(rec.get("comment", "")),
                "prior_25_2h": prior_lookup.get(name),
            }
        )
    return rows


def _build_user_message(
    review_companies: list[dict],
    existing_universe: list[dict],
) -> str:
    """user 메시지 본문 — JSON 두 블록을 자연어 헤더로 감싼다."""
    return (
        "다음은 이번 빌드에서 검토할 종목들과 기존 유니버스 컨텍스트입니다.\n\n"
        "=== review_companies ===\n"
        + json.dumps(review_companies, ensure_ascii=False, indent=2)
        + "\n\n=== existing_universe ===\n"
        + json.dumps(existing_universe, ensure_ascii=False, indent=2)
        + "\n\n위 데이터에 system prompt 의 룰(R1~R6)과 가드레일 절차를 적용하여, "
        "지정된 JSON 스키마로만 출력하라."
    )


def _parse_json_response(raw: str) -> dict | None:
    """모델이 코드블록·앞말미를 붙였을 가능성에 대비하여 JSON만 추출."""
    s = raw.strip()
    # ```json ... ``` 또는 ``` ... ``` 제거
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    # 첫 { 부터 마지막 } 까지 절단
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    try:
        return json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return None


def _sanity_check_metrics(result: dict) -> list[str]:
    """metrics 가드레일 위반 검출. 위반 사유 리스트 반환(빈 리스트면 통과)."""
    breaches: list[str] = []
    metrics = result.get("metrics") or {}
    dpct = metrics.get("downgrade_pct")
    upct = metrics.get("upgrade_pct")
    if isinstance(dpct, (int, float)) and dpct > _GUARDRAIL_LIMIT:
        breaches.append(f"downgrade_pct={dpct:.3f} > {_GUARDRAIL_LIMIT:.2f}")
    if isinstance(upct, (int, float)) and upct > _GUARDRAIL_LIMIT:
        breaches.append(f"upgrade_pct={upct:.3f} > {_GUARDRAIL_LIMIT:.2f}")
    return breaches


def review_judgments(
    *,
    review_companies: list[dict],
    existing_universe: list[dict],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    enable_cache: bool = True,
    enable_1m_context: bool = True,
    api_key: str | None = None,
) -> dict:
    """Stage 2 검수 호출. 가드레일 위반 시 1회 재호출 후 그래도 위반이면 결과는 반환하되 breaches 기록.

    반환 dict 스키마:
      {
        "decisions": {...},
        "inversions": [...],
        "metrics": {..., "guardrail_breaches": [...]},
        "model": str,
        "stop_reason": str,
        "usage": {...},
        "_meta": { "retried": bool, "parse_failures": [...] }
      }
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    system_blocks: list[dict[str, Any]] = [
        {"type": "text", "text": JUDGMENT_SYSTEM_PROMPT}
    ]
    if enable_cache:
        system_blocks[-1]["cache_control"] = {"type": "ephemeral"}

    user_text = _build_user_message(review_companies, existing_universe)

    extra_headers: dict[str, str] = {}
    if enable_1m_context:
        extra_headers["anthropic-beta"] = "context-1m-2025-08-07"

    def _call(extra_user_msg: str | None = None) -> tuple[Any, dict | None]:
        messages: list[dict] = [{"role": "user", "content": user_text}]
        if extra_user_msg:
            messages.append({"role": "user", "content": extra_user_msg})
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": messages,
        }
        if extra_headers:
            kwargs["extra_headers"] = extra_headers
        resp = client.messages.create(**kwargs)
        raw = next(
            (b.text for b in resp.content if getattr(b, "type", None) == "text"),
            "",
        )
        return resp, _parse_json_response(raw)

    parse_failures: list[str] = []
    retried = False
    response, parsed = _call()
    if parsed is None:
        parse_failures.append("first_call_json_parse_failed")
        retried = True
        response, parsed = _call(
            "직전 응답이 JSON 파싱에 실패했다. 코드블록·머리말 없이 순수 JSON 만 다시 출력하라."
        )
    elif _sanity_check_metrics(parsed):
        breaches = _sanity_check_metrics(parsed)
        retried = True
        feedback = (
            "다음 가드레일이 위반되었다: " + ", ".join(breaches) + ". "
            "system prompt 의 R4/R5 절차에 따라 가장 약한 변동 사유 종목부터 "
            "직전 분류로 되돌려 한도 내로 맞춘 뒤 JSON 만 다시 출력하라."
        )
        response, parsed_retry = _call(feedback)
        if parsed_retry is not None:
            parsed = parsed_retry
        else:
            parse_failures.append("retry_call_json_parse_failed")

    if parsed is None:
        # 두 번 다 실패 시 빈 골격 반환
        parsed = {
            "decisions": {},
            "inversions": [],
            "metrics": {"guardrail_breaches": [], "downgrade_pct": None,
                        "upgrade_pct": None, "denominator": 0},
        }

    # 코드 측 최종 sanity check 결과를 metrics 에 흔적 남김
    final_breaches = _sanity_check_metrics(parsed)
    if final_breaches:
        parsed.setdefault("metrics", {}).setdefault("guardrail_breaches", []).extend(
            [{"type": "post_call_sanity", "detail": b} for b in final_breaches]
        )

    parsed["model"] = response.model
    parsed["stop_reason"] = response.stop_reason
    parsed["usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            response.usage, "cache_creation_input_tokens", 0
        ),
        "cache_read_input_tokens": getattr(
            response.usage, "cache_read_input_tokens", 0
        ),
    }
    parsed["_meta"] = {
        "retried": retried,
        "parse_failures": parse_failures,
    }
    return parsed


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comments-dir", required=True, type=Path)
    p.add_argument(
        "--xlsx",
        required=True,
        type=Path,
        help="기존 유니버스 엑셀 (25.2H 분류 추출용)",
    )
    p.add_argument(
        "--grade-input",
        type=Path,
        default=None,
        help="26.1H 등급/전망 JSON. {회사: {rating, outlook}} 형식. "
        "생략 시 기존 엑셀의 26.1H 컬럼(7,8) 값을 사용.",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "secrets.env",
        help="API 키 env 파일 (기본: ../../secrets.env)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("_workspace/judgment/stage2_review.json"),
    )
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--no-1m-context", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        load_env_file(args.env_file)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "[ERROR] ANTHROPIC_API_KEY 가 환경변수/env 파일에서 로드되지 않았습니다.",
            file=sys.stderr,
        )
        return 2

    # 1) 기존 엑셀 → existing_universe + prior_lookup
    existing = extract_existing(args.xlsx)
    existing_universe = existing["existing_universe"]
    prior_lookup = existing["prior_lookup"]

    # 2) grade_input 로드 (선택). 없으면 기존 엑셀의 26.1H 컬럼 값을 사용.
    if args.grade_input and args.grade_input.exists():
        grade_input = json.loads(args.grade_input.read_text(encoding="utf-8"))
    else:
        grade_input = {
            row["name"]: {
                "rating": row.get("grade_26_1h"),
                "outlook": row.get("outlook_26_1h"),
            }
            for row in existing_universe
        }

    # 3) review_companies 구성
    review_companies = _load_review_companies(
        args.comments_dir, grade_input, prior_lookup
    )
    if not review_companies:
        print(
            f"[ERROR] {args.comments_dir} 에 *.json 코멘트 산출물이 없습니다.",
            file=sys.stderr,
        )
        return 2

    # 4) Stage 2 호출
    try:
        result = review_judgments(
            review_companies=review_companies,
            existing_universe=existing_universe,
            model=args.model,
            max_tokens=args.max_tokens,
            enable_cache=not args.no_cache,
            enable_1m_context=not args.no_1m_context,
        )
    except anthropic.APIStatusError as e:
        print(
            f"[API ERROR] status={e.status_code} type={type(e).__name__}",
            file=sys.stderr,
        )
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # 5) 저장
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6) 요약 출력
    metrics = result.get("metrics", {})
    print(
        json.dumps(
            {
                "saved": str(args.output),
                "review_count": len(review_companies),
                "metrics": {
                    "denominator": metrics.get("denominator"),
                    "downgrade_pct": metrics.get("downgrade_pct"),
                    "upgrade_pct": metrics.get("upgrade_pct"),
                    "guardrail_breaches": metrics.get("guardrail_breaches", []),
                },
                "retried": result.get("_meta", {}).get("retried"),
                "usage": result.get("usage"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
