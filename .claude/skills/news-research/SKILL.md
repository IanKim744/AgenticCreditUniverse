---
name: news-research
description: Perplexity API로 종목별 뉴스 + 리스크 정밀 검색을 수행해 신평 관점 4섹션 리포트를 생성한다. "뉴스 리서치", "특이사항 조사", "리스크 검색", "회사명 평판 조사" 요청 시 사용한다.
---

# News Research

모듈 `AgenticCreditUniverse/pplx_news/pplx_risk_analyst.py` 를 호출하여 종목별 Perplexity 리서치 산출물을 생성한다. 프롬프트 본문은 같은 폴더의 `prompt_template.py` (`PROMPT_TEMPLATE`, `AGENT_INSTRUCTIONS`) 에 분리되어 있다. 기본 호출은 `--api agent` (= `google/gemini-3.1-pro-preview` + web_search/fetch_url 도구).

## 호출 방식

CLI:
```bash
cd AgenticCreditUniverse/pplx_news
python pplx_risk_analyst.py \
  --name "롯데물산" \
  --outdir ../../_workspace/news/
```

대안 import:
```python
sys.path.insert(0, "AgenticCreditUniverse/pplx_news")
import pplx_risk_analyst as pra
pra.analyze(name="롯데물산", output_dir="_workspace/news/롯데물산/")
```

## 출력 정규화 규약

종목 디렉토리 `_workspace/news/{company}/` 에 다음 파일:

| 파일 | 내용 |
|------|------|
| `report.md` | 4섹션 구조 리포트 |
| `raw.json` | Perplexity 원본 응답(질의·시계열별) |
| `metadata.json` | 메타 |

`report.md` 표준 4섹션:
```markdown
# {회사명} — 신평 관점 리서치 (최근 6개월)

## Executive Summary
- 1~3 bullet, 핵심 발견 사항

## Critical Risk
- 검찰/금감원/감독당국 조사
- 경영진 횡령·배임·중대재해
- 주요 분쟁(소송, 무역분쟁 등)
- (없으면 "최근 6개월 내 특이사항 없음" 명시)

## Business & Financials
- 실적·전략·시장 흐름
- 인수합병·자회사 변동
- 신규 발행·자본 변동

## Conclusion
- 신평 관점 종합 (1~2 문장)

## 출처
1. https://...
2. https://...
```

`metadata.json`:
```json
{
  "company": "롯데물산",
  "model": "google/gemini-3.1-pro-preview",
  "queried_at": "2026-04-25T11:44:00+09:00",
  "general_query_count": 3,
  "risk_query_count": 5,
  "citation_count": 12,
  "errors": []
}
```

## 행동 규칙

1. **시계열 6개월.** 검색 프롬프트에 명시(`최근 6개월`).
2. **출처 인용 필수.** 사실 진술마다 출처 URL 포함.
3. **추정·소문 분리.** 본문에서 추정은 별도 표기 또는 제외.
4. **신평 관점 우선.** 사업·재무 영향, 등급 트리거 가능성을 상위 배치.
5. **0건 처리.** 검색 결과 0건이면 명시(빈 본문 금지).

## 환경변수

- `PERPLEXITY_API_KEY` 필수. `.env` 파일에서 로드.

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| API 429 | 1회 재시도 |
| API 5xx | 1회 재시도 후 종목 스킵 |
| 검색 결과 0건 | "특이사항 없음" 명시 후 정상 종료 |
| 환경변수 누락 | 즉시 중단 |

## 호출 예

```
Agent(news-collector, model="opus",
      prompt="company=롯데물산, output_dir=_workspace/news/롯데물산/
              스킬: news-research 사용
              산출: report.md (4섹션), raw.json, metadata.json")
```

## 캐시

- 동일 종목 산출물이 3일 이내면 캐시 활용. 등급 변동 의심·중대 사건 발생 시 사용자 명시로 강제 재수집.
