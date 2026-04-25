#!/usr/bin/env python3
"""Perplexity risk-analyst report for a given company.

Uses Perplexity's chat/completions endpoint (sonar-pro by default) to run the
"리스크 분석가" prompt and saves the LLM's synthesized markdown report plus the
raw API response (with citations).

Env:
  PERPLEXITY_API_KEY   required

Example:
  python pplx_risk_analyst.py --name "SK하이닉스" --outdir ./out
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SONAR_URL = "https://api.perplexity.ai/chat/completions"
AGENT_URL = "https://api.perplexity.ai/v1/responses"

PROMPT_TEMPLATE = """## 역할 부여
당신은 기업의 잠재적 위험을 발굴하는 전문 '리스크 분석가(Risk Analyst)'입니다.
단순한 뉴스 요약이 아니라, 투자자 관점에서 치명적일 수 있는 법적·재무적 리스크를 검증해야 합니다.

## 필수 수행 지침 (Step-by-Step)

1. [일반 검색]과 [리스크 정밀 검색]을 분리하여 수행하십시오.
   - 일반 검색: 실적, 경영 전략, 신사업 등
   - 리스크 정밀 검색: 아래 키워드를 조합하여 별도로 검색할 것 (단순 뉴스 검색 금지)

2. **리스크 정밀 검색 키워드 (반드시 포함)**
   - 기업명 + 검찰/경찰/금감원/공정위/국세청
   - 기업명 + 압수수색/소환조사/구속영장/고발/과징금
   - 기업명 + 횡령/배임/사기/자본시장법/분식회계/중대재해
   - 오너/경영진 이름 + 리스크/의혹/논란

3. 시계열 균형 유지
   - 가장 최근(1주일 이내) 뉴스뿐만 아니라, 6개월 기간 전체에 걸쳐 발생한 사건의 '진행 경과'를 추적하십시오.

## 출력 양식 (Report Format)
1. **Executive Summary**: 3줄 요약 (호재와 악재의 비중)
2. **Critical Risk (거버넌스/법적 리스크)**:
   - 금융당국/수사기관 조사 현황 (사건명, 진행 단계, 예상 파급력)
   - 주요 소송 및 분쟁 (소송 가액, 승소 가능성, 재무적 영향)
   - *특이사항이 없을 경우 '해당 기간 내 특이사항 없음'으로 명기*

3. **Business & Financials (영업/재무)**:
   - 실적 추이(실적 변동 요인 포함)및 특이사항

4. **Conclusion**: 종합 평가 (투자 주의 등급)

## 분석 대상
- 대상 기업: {name}
"""


def slugify(text: str, max_len: int = 60) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[\s/\\?%*:|\"<>.,;!#@$^&()\[\]{}=+`~']+", "-", s)
    s = "".join(ch for ch in s if ch.isalnum() or ch == "-" or ord(ch) > 127)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s or "company")[:max_len]


def _post_with_retry(url: str, headers: dict, body: dict,
                     timeout: int, max_retries: int, backoff_base: float) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff_base ** attempt)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            raise RuntimeError("401 Unauthorized — PERPLEXITY_API_KEY 확인")
        if r.status_code == 400:
            raise RuntimeError(f"400 Bad Request: {r.text[:500]}")
        if r.status_code == 429 or 500 <= r.status_code < 600:
            if attempt == max_retries - 1:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            ra = r.headers.get("Retry-After")
            try:
                delay = float(ra) if ra else (backoff_base ** attempt)
            except ValueError:
                delay = backoff_base ** attempt
            time.sleep(max(delay, 0.0))
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    raise RuntimeError(f"Exhausted retries: {last_err}")


def call_sonar(prompt, api_key, model="sonar-pro", temperature=0.1, max_tokens=4000,
               timeout=240, max_retries=4, backoff_base=1.7):
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests python-dotenv")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "pplx_risk_analyst/1.0",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "return_citations": True,
        "return_related_questions": False,
    }
    return _post_with_retry(SONAR_URL, headers, body, timeout, max_retries, backoff_base)


AGENT_INSTRUCTIONS = (
    "You have web_search and fetch_url tools. Run MULTIPLE targeted searches: "
    "one set for 일반(실적·전략·신사업), and separate sets for 리스크 정밀 검색 "
    "(검찰/경찰/금감원/공정위/국세청, 압수수색/소환조사/구속영장/고발/과징금, "
    "횡령/배임/사기/자본시장법/분식회계/중대재해, 오너/경영진 이름 + 의혹/논란). "
    "Include Korean-language queries. Cover 최근 6개월 with emphasis on the last 1 week. "
    "Use citations. Respond fully in Korean following the exact Report Format."
)


def call_agent(prompt, api_key, model="google/gemini-3.1-pro-preview",
               max_output_tokens=6000, web_search=True, timeout=420,
               max_retries=3, backoff_base=2.0):
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests python-dotenv")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "pplx_risk_analyst/1.0",
    }
    body: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }
    if web_search:
        body["tools"] = [{"type": "web_search"}, {"type": "fetch_url"}]
        body["instructions"] = AGENT_INSTRUCTIONS
    return _post_with_retry(AGENT_URL, headers, body, timeout, max_retries, backoff_base)


def extract_answer_and_citations(api: str, resp: dict) -> tuple[str, list[str], dict]:
    """Return (answer_markdown, citation_urls, usage_dict) for either API shape."""
    if api == "sonar":
        answer = ""
        try:
            answer = resp["choices"][0]["message"]["content"]
        except Exception:
            pass
        citations = resp.get("citations") or []
        if not citations:
            sr = resp.get("search_results") or []
            citations = [s.get("url") or s.get("title", "") for s in sr if isinstance(s, dict)]
        return answer, citations, resp.get("usage") or {}
    # agent
    answer = ""
    urls: list[str] = []
    seen: set[str] = set()
    for o in resp.get("output") or []:
        t = o.get("type")
        if t == "search_results":
            for r in o.get("results") or []:
                u = r.get("url")
                if u and u not in seen:
                    seen.add(u); urls.append(u)
        elif t == "message":
            for c in o.get("content") or []:
                if c.get("type") == "output_text":
                    answer += c.get("text", "")
    return answer, urls, resp.get("usage") or {}


def render_report_md(name: str, answer_md: str, citations: list[str], meta: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# 리스크 분석 리포트 — {name}\n")
    lines.append(f"- Model: `{meta.get('model')}`\n")
    lines.append(f"- Generated (UTC): {meta.get('generated_utc')}\n")
    lines.append(f"- Citations: {len(citations)}\n\n---\n")
    lines.append(answer_md.strip() + "\n")
    if citations:
        lines.append("\n---\n\n## 출처 (Perplexity citations)\n")
        for i, c in enumerate(citations, 1):
            lines.append(f"{i}. {c}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Perplexity risk-analyst report")
    ap.add_argument("--name", required=True, help="기업명 (예: SK하이닉스)")
    ap.add_argument("--outdir", default="./out", help="저장 폴더")
    ap.add_argument("--api", choices=["sonar", "agent"], default="sonar",
                    help="sonar: /chat/completions (Sonar 모델 전용). "
                         "agent: /v1/responses (Gemini/GPT/Claude 등 서드파티 + tools)")
    ap.add_argument("--model", default=None,
                    help="sonar-pro|sonar-reasoning-pro|sonar-deep-research (sonar api) "
                         "혹은 google/gemini-3.1-pro-preview, openai/gpt-5.4, "
                         "anthropic/claude-sonnet-4-6 등 (agent api). "
                         "기본: sonar→sonar-pro, agent→google/gemini-3.1-pro-preview")
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--max-tokens", type=int, default=4000,
                    help="sonar: max_tokens / agent: max_output_tokens")
    ap.add_argument("--no-web-search", action="store_true",
                    help="agent api에서 web_search 도구를 비활성화")
    args = ap.parse_args(argv)

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("ERROR: PERPLEXITY_API_KEY 환경변수 미설정. .env에 넣거나 export 하세요.", file=sys.stderr)
        return 2

    if args.model is None:
        args.model = "sonar-pro" if args.api == "sonar" else "google/gemini-3.1-pro-preview"

    prompt = PROMPT_TEMPLATE.format(name=args.name)
    slug = slugify(args.name)
    outdir = Path(args.outdir) / slug
    outdir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    print(f"[1/2] Calling Perplexity {args.api} ({args.model}) for {args.name} …", file=sys.stderr)
    if args.api == "sonar":
        resp = call_sonar(
            prompt, api_key,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    else:
        resp = call_agent(
            prompt, api_key,
            model=args.model,
            max_output_tokens=max(args.max_tokens, 4000),
            web_search=not args.no_web_search,
        )

    # Save raw
    (outdir / "raw.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    answer_md, citations, usage = extract_answer_and_citations(args.api, resp)

    meta = {
        "corp_name": args.name,
        "api": args.api,
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "endpoint": SONAR_URL if args.api == "sonar" else AGENT_URL,
        "generated_utc": now,
        "usage": usage,
        "n_citations": len(citations),
    }
    (outdir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_md = render_report_md(args.name, answer_md, citations, meta)
    (outdir / "report.md").write_text(report_md, encoding="utf-8")
    (outdir / "prompt.txt").write_text(prompt, encoding="utf-8")

    # Leak check
    leaked = []
    for p in outdir.rglob("*"):
        if p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
                if api_key and api_key in txt:
                    leaked.append(str(p))
            except Exception:
                continue
    if leaked:
        print(f"WARN: API key leaked into files: {leaked}", file=sys.stderr)

    print(f"[2/2] Saved → {outdir}", file=sys.stderr)
    print(f"  report.md  ({(outdir/'report.md').stat().st_size} B)")
    print(f"  raw.json   ({(outdir/'raw.json').stat().st_size} B)")
    print(f"  citations  {len(citations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
