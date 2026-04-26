#!/usr/bin/env python3
"""Perplexity risk-analyst report for a given company.

Default API: /v1/responses (agent mode) with google/gemini-3.1-pro-preview +
web_search/fetch_url tools. Pass --api sonar to fall back to /chat/completions
(Sonar 모델 단독, 도구 없음).
프롬프트 본문은 prompt_template.py 로 분리되어 있어 코드 변경 없이 튜닝 가능.

Env:
  PERPLEXITY_API_KEY   required

Example:
  python pplx_risk_analyst.py --name "에스케이씨" --outdir ./out
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

from prompt_template import PROMPT_TEMPLATE, AGENT_INSTRUCTIONS, DEFAULT_DENY_DOMAINS

SONAR_URL = "https://api.perplexity.ai/chat/completions"
AGENT_URL = "https://api.perplexity.ai/v1/responses"


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
               timeout=240, max_retries=4, backoff_base=1.7, deny_domains=None,
               recency_filter="year"):
    """Sonar API. recency_filter: 'hour' | 'day' | 'week' | 'month' | 'year' | None.

    기본값 'year' 로 검색 시점 기준 1년 이내 자료만 사용 (낡은 IR/뉴스 인용 방지).
    """
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests python-dotenv")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "pplx_risk_analyst/1.0",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "return_citations": True,
        "return_related_questions": False,
    }
    if recency_filter:
        body["search_recency_filter"] = recency_filter
    if deny_domains:
        body["search_domain_filter"] = list(deny_domains)[:20]
    return _post_with_retry(SONAR_URL, headers, body, timeout, max_retries, backoff_base)


def call_agent(prompt, api_key, model="google/gemini-3.1-pro-preview",
               max_output_tokens=6000, web_search=True, timeout=420,
               max_retries=3, backoff_base=2.0, deny_domains=None,
               search_after_date: str | None = None):
    """Agent API. search_after_date: 'YYYY-MM-DD' (web_search tool 의 결과를 그 날짜 이후로 제한).

    기본값으로 호출 시각 기준 1년 전 ISO 일자를 적용해 1년 이내 자료만 fetch.
    """
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests python-dotenv")
    if search_after_date is None:
        # 기본 1년 이내
        from datetime import datetime, timedelta, timezone as _tz
        search_after_date = (datetime.now(_tz.utc) - timedelta(days=365)).date().isoformat()
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
        ws_tool: dict[str, Any] = {"type": "web_search"}
        filters: dict[str, Any] = {}
        if deny_domains:
            filters["search_domain_filter"] = list(deny_domains)[:20]
        if search_after_date:
            filters["search_after_date_filter"] = search_after_date
        if filters:
            ws_tool["filters"] = filters
        body["tools"] = [ws_tool, {"type": "fetch_url"}]
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
    ap.add_argument("--name", required=True, help="기업명 (예: 에스케이씨)")
    ap.add_argument("--outdir", default="./out", help="저장 폴더")
    ap.add_argument("--api", choices=["sonar", "agent"], default="agent",
                    help="agent: /v1/responses (Gemini 등 + web_search/fetch_url, 기본). "
                         "sonar: /chat/completions (Sonar 모델 단독, 도구 없음)")
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
    ap.add_argument("--no-domain-filter", action="store_true",
                    help="search_domain_filter denylist 적용을 건너뜀(디버그)")
    ap.add_argument("--deny-extra", nargs="*", default=[],
                    help="1회용 추가 차단 도메인 (예: --deny-extra '-judal.co.kr')")
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

    deny = [] if args.no_domain_filter else (DEFAULT_DENY_DOMAINS + list(args.deny_extra))[:20]

    now = datetime.now(timezone.utc).isoformat()
    print(f"[1/2] Calling Perplexity {args.api} ({args.model}) for {args.name} "
          f"(deny={len(deny)}) …", file=sys.stderr)
    if args.api == "sonar":
        resp = call_sonar(
            prompt, api_key,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            deny_domains=deny,
        )
    else:
        resp = call_agent(
            prompt, api_key,
            model=args.model,
            max_output_tokens=max(args.max_tokens, 4000),
            web_search=not args.no_web_search,
            deny_domains=deny,
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
        "search_domain_filter": deny,
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
