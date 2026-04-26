"""26.1H 검토 코멘트 자동 생성 모듈.

입력: 신평사 의견서 PDF, NICE 표준 재무지표, DART 사업의 내용, Perplexity 뉴스.
출력: 신용평가 유니버스 엑셀 "26.1H 검토 코멘트" 셀에 들어갈 한국어 코멘트.

모델: Claude Sonnet 4.6 (1M 컨텍스트). Anthropic 공식 SDK 사용.
보안: API 키는 환경변수에서만 로드. 코드/로그에 노출 금지.

사용 예:
  python generate_comment.py \
    --company "다우기술" \
    --pdf ./inputs/credit_opinion.pdf \
    --nice ./inputs/nice_indicators.json \
    --dart-business ./inputs/business_section.txt \
    --news ./inputs/pplx_report.md \
    --env-file "../claude api.env" \
    --output ./out/dawootech_comment.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import anthropic

from prompt_template import SYSTEM_PROMPT


# 첫 줄 헤더 패턴: [AI 판단] {O|△|X} | 근거 → (기호, 근거)
# DOTALL 미사용. 첫 줄만 매칭하고 본문은 별도로 분리.
_JUDGMENT_HEADER_RE = re.compile(r"^\[AI 판단\]\s*([O△X])\s*\|\s*(.+?)\s*$")


def _parse_response(raw: str) -> tuple[str | None, str | None, str]:
    """응답에서 (judgment, judgment_reason, comment_body) 분리.

    형식: 첫 줄 = `[AI 판단] {O|△|X} | 근거`, 빈 줄 1, 이후 본문.
    파싱 실패 시 (None, None, raw) 반환 — 호출측이 경고를 띄움.
    """
    parts = raw.split("\n\n", 1)
    if len(parts) != 2:
        return None, None, raw
    header_line, body = parts[0].strip(), parts[1].strip()
    m = _JUDGMENT_HEADER_RE.match(header_line)
    if not m:
        return None, None, raw
    return m.group(1), m.group(2).strip(), body


# ----------------------------------------------------------------------------
# Env loading
# ----------------------------------------------------------------------------

def load_env_file(path: Path) -> None:
    """경량 .env 파서. 파일명에 공백이 들어간 'claude api.env'를 다루기 위해 자체 구현.

    이미 환경변수가 설정되어 있으면 덮어쓰지 않는다(우선순위: shell env > file).
    값에 따옴표가 있으면 벗긴다.
    """
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ----------------------------------------------------------------------------
# Input assembly
# ----------------------------------------------------------------------------

def read_text(path: Path | None, max_chars: int | None = None) -> str | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if max_chars is not None and len(text) > max_chars:
        # 1M 컨텍스트라도 입력당 상한을 두어 안전 마진 확보
        text = text[:max_chars] + f"\n\n[...truncated at {max_chars} chars...]"
    return text


def read_pdf_b64(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    data = path.read_bytes()
    if len(data) > 32 * 1024 * 1024:
        raise ValueError(
            f"PDF too large for base64 message attach (>32MB): {len(data)} bytes. "
            "Use Files API instead (not implemented in this minimal module)."
        )
    return base64.standard_b64encode(data).decode("ascii")


def build_user_content(
    company: str,
    pdf_b64: str | None,
    nice_text: str | None,
    dart_business: str | None,
    news_text: str | None,
    grade_info: str | None,
) -> list[dict[str, Any]]:
    """user 메시지의 content 블록 리스트를 조립한다.

    PDF는 document 블록, 나머지는 text 블록으로 구성. 빠진 자료는 [없음] 표기.
    """
    blocks: list[dict[str, Any]] = []

    header_lines = [f"[발행기관] {company}"]
    if grade_info:
        header_lines.append(f"[등급 정보] {grade_info}")
    blocks.append({"type": "text", "text": "\n".join(header_lines)})

    if pdf_b64:
        blocks.append(
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
                "title": f"{company} 신용평가 의견서",
            }
        )
    else:
        blocks.append({"type": "text", "text": "[신평사 의견서 PDF] 없음"})

    sections = [
        ("NICE 표준화 재무지표(연결 우선·없으면 별도)", nice_text),
        ("DART 최신 공시 — 사업의 내용", dart_business),
        ("주요 뉴스/매스컴 (Perplexity 리서치 결과)", news_text),
    ]
    for title, body in sections:
        blocks.append(
            {
                "type": "text",
                "text": f"=== {title} ===\n{body if body else '[자료 없음]'}",
            }
        )

    blocks.append(
        {
            "type": "text",
            "text": (
                "위 자료를 종합해 다음 형식으로 출력하라:\n"
                "  첫 줄: `[AI 판단] (O|△|X) | 근거 30~80자`\n"
                "  빈 줄 1칸\n"
                "  본문: 26.1H 검토 코멘트 **400~600자** (헤더 제외), "
                "목표 470~570자, 신평 보고서 톤.\n"
                "그 외 머리말·맺음말·메타 코멘트 금지. "
                "출력 직전 본문 글자 수를 카운트해 600자 초과면 무조건 압축."
            ),
        }
    )
    return blocks


# ----------------------------------------------------------------------------
# Anthropic API
# ----------------------------------------------------------------------------

def generate_comment(
    *,
    company: str,
    pdf_path: Path | None,
    nice_path: Path | None,
    dart_business_path: Path | None,
    news_path: Path | None,
    grade_info: str | None = None,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
    enable_cache: bool = True,
    enable_1m_context: bool = True,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Sonnet 4.6 호출하여 코멘트 1건 생성.

    반환 dict 스키마:
      {
        "company": str,
        "comment": str,
        "model": str,
        "stop_reason": str,
        "usage": {input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens},
      }
    """
    pdf_b64 = read_pdf_b64(pdf_path) if pdf_path else None
    # 입력당 상한(1M 컨텍스트 안에서 텍스트 입력 + PDF 마진 확보)
    nice_text = read_text(nice_path, max_chars=200_000)
    dart_business = read_text(dart_business_path, max_chars=300_000)
    news_text = read_text(news_path, max_chars=100_000)

    user_blocks = build_user_content(
        company=company,
        pdf_b64=pdf_b64,
        nice_text=nice_text,
        dart_business=dart_business,
        news_text=news_text,
        grade_info=grade_info,
    )

    # 시스템 프롬프트는 회사가 바뀌어도 동일하므로 캐싱 → 종목 다수 처리 시 비용↓
    system_blocks: list[dict[str, Any]] = [{"type": "text", "text": SYSTEM_PROMPT}]
    if enable_cache:
        system_blocks[-1]["cache_control"] = {"type": "ephemeral"}

    # API 키는 명시 인자 없으면 환경변수에서 로드(코드 박지 않음)
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    extra_headers: dict[str, str] = {}
    if enable_1m_context:
        # Sonnet 4 계열의 1M 컨텍스트 베타 헤더. 티어/계정 권한이 없으면 제거.
        extra_headers["anthropic-beta"] = "context-1m-2025-08-07"

    create_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_blocks,
        "messages": [{"role": "user", "content": user_blocks}],
    }
    if extra_headers:
        create_kwargs["extra_headers"] = extra_headers

    response = client.messages.create(**create_kwargs)

    # 첫 텍스트 블록만 추출. 시스템 프롬프트가 강제하는 형식:
    #   첫 줄: [AI 판단] (O|△|X) | 근거
    #   빈 줄
    #   본문(400~600자)
    raw = next(
        (b.text for b in response.content if getattr(b, "type", None) == "text"),
        "",
    ).strip()
    judgment, judgment_reason, comment_text = _parse_response(raw)
    if judgment is None:
        # 파싱 실패 — Stage 2가 None을 보수적으로 △ 처리하므로 본문은 그대로 보존
        print(
            f"[WARN] {company}: AI 판단 헤더 파싱 실패. 본문만 저장 (judgment=None).",
            file=sys.stderr,
        )

    return {
        "company": company,
        "comment": comment_text,
        "judgment_stage1": judgment,
        "judgment_stage1_reason": judgment_reason,
        "model": response.model,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ),
            "cache_read_input_tokens": getattr(
                response.usage, "cache_read_input_tokens", 0
            ),
        },
    }


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="26.1H 검토 코멘트 자동 생성 (Claude Sonnet 4.6, 1M context)"
    )
    p.add_argument("--company", required=True, help="발행기관명 (예: 다우기술)")
    p.add_argument("--pdf", type=Path, default=None, help="신평사 의견서 PDF 경로")
    p.add_argument("--nice", type=Path, default=None, help="NICE 표준 재무지표 파일(JSON/CSV/TXT)")
    p.add_argument("--dart-business", type=Path, default=None, help="DART 사업의 내용 텍스트 파일")
    p.add_argument("--news", type=Path, default=None, help="Perplexity 리서치 결과(report.md)")
    p.add_argument("--grade-info", default=None, help='등급/전망 정보 (예: "A0/Stable")')
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "claude api.env",
        help="API 키 env 파일 경로 (기본: ../claude api.env)",
    )
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--no-cache", action="store_true", help="프롬프트 캐싱 비활성화")
    p.add_argument(
        "--no-1m-context",
        action="store_true",
        help="1M 컨텍스트 베타 헤더 비활성화 (티어 권한 없을 때)",
    )
    p.add_argument("--output", type=Path, default=None, help="결과 JSON 저장 경로")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # 1) env 파일 로드 → ANTHROPIC_API_KEY 가 환경변수로 등록됨
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

    # 2) 생성
    try:
        result = generate_comment(
            company=args.company,
            pdf_path=args.pdf,
            nice_path=args.nice,
            dart_business_path=args.dart_business,
            news_path=args.news,
            grade_info=args.grade_info,
            model=args.model,
            max_tokens=args.max_tokens,
            enable_cache=not args.no_cache,
            enable_1m_context=not args.no_1m_context,
        )
    except anthropic.APIStatusError as e:
        # 메시지에 키가 절대 들어가지 않도록 status/type만 출력
        print(f"[API ERROR] status={e.status_code} type={type(e).__name__}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # 3) 출력
    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out_json, encoding="utf-8")
        print(f"saved: {args.output}", file=sys.stderr)
    print(out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
