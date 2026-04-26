---
name: nice-collection
description: 종목별로 NICE신용평가에서 표준 재무지표(연결 우선) + 최신 신평 의견서 PDF를 수집한다. "NICE 재무지표 가져와", "신평 의견서 다운로드", "표준 재무지표 수집" 요청 시 사용한다.
---

# NICE Collection

기존 모듈 `AgenticCreditUniverse/nicerating_scraper/nicerating_scraper.py` 를 호출하여 종목별 NICE 산출물을 표준 디렉토리에 저장한다.

## 환경 셋업

**공개 영역만 사용**하는 경우 별도 셋업 불필요. 표준 재무지표 + 메타정보 수집 가능.

**의견서 PDF 자동 다운로드**가 필요하면 Playwright 설치 필수 (NICE 의견서 docId 추출에 JS 렌더링 필요):

```bash
$ROOT/.venv/bin/pip install playwright
$ROOT/.venv/bin/playwright install chromium    # ~150MB
```

설치 후에는 호출 시 `--no-pdf` 옵션을 제거하면 PDF 가 함께 저장된다.
미설치 상태로 호출하면 PDF 만 누락되고(metadata에 `pdf_skipped: playwright_missing` 기록) 다른 산출물은 정상 생성됨.

## 호출 방식

CLI 호출 우선(모듈은 CLI 진입점 보유):

```bash
cd AgenticCreditUniverse/nicerating_scraper
python nicerating_scraper.py \
  --cmp-cd ABC1234 \
  --output-dir ../../_workspace/nice/다우기술/ \
  --save-pdf
```

로그인 자격증명이 있으면 전체 재무부표(157행)도 함께 받는다:
```bash
python nicerating_scraper.py --cmp-cd ABC1234 --output-dir ... --login --env-file ../nice.env
```

대안 import:
```python
sys.path.insert(0, "AgenticCreditUniverse/nicerating_scraper")
import nicerating_scraper as nrs
scraper = nrs.NiceRatingScraper()
scraper.collect(cmp_cd="ABC1234", output_dir="_workspace/nice/다우기술/", save_pdf=True)
```

## 출력 정규화 규약

종목 디렉토리 `_workspace/nice/{company}/` 에 다음 파일을 둔다:

| 파일 | 내용 |
|------|------|
| `indicators.json` | 표준 재무지표 (7년 × 18지표 공개 영역, 로그인 시 전체 재무부표 추가) |
| `indicators.csv` | 동일 데이터 표 형태(선택) |
| `opinion.pdf` | 최신 신평 의견서 PDF |
| `metadata.json` | 메타정보 |

`indicators.json` 스키마(예):
```json
{
  "company": "다우기술",
  "cmp_cd": "ABC1234",
  "basis": "consolidated",
  "currency": "KRW",
  "unit": "억원",
  "years": ["2019", "2020", ..., "2025"],
  "indicators": {
    "매출액": {"2019": 12345, "2020": 13456, ...},
    "영업이익": {...},
    "당기순이익": {...},
    "부채비율": {...},
    "차입금의존도": {...},
    "총차입금/EBITDA": {...},
    "EBITDA마진": {...}
  },
  "full_table_loaded": false
}
```

`metadata.json`:
```json
{
  "company": "다우기술",
  "cmp_cd": "ABC1234",
  "rating_doc_id": "RPT_20260315_001",
  "rating_confirmed_at": "2026-03-15",
  "rating": "A0",
  "outlook": "Stable",
  "indicators_basis": "consolidated",
  "paywalled": false,
  "login_used": false,
  "collected_at": "2026-04-25T11:43:00+09:00",
  "errors": []
}
```

## 행동 규칙

1. **연결 기준 우선.** 표준 재무지표는 연결 기준으로만(스크래퍼 정책).
2. **최신 의견서.** 등급 히스토리에서 확정일 기준 가장 최신 1건만 다운로드.
3. **PDF 무결성 확인.** 다운로드 직후 파일 크기 0바이트/HTML 응답이면 실패 처리(metadata.errors 기록).
4. **유료 영역 차단 시.** `paywalled: true` 기록 후 가능한 자료(공개 요약)만 산출.
5. **캐시 활용.** 동일 cmp_cd 산출물이 7일 이내면 호출 생략.

## 환경변수 / 자격증명

- 공개 영역만 사용 시: 환경변수 불필요.
- 로그인 사용 시: `nice.env` (별도 파일, .gitignore 처리됨)에 `NICE_USERNAME`, `NICE_PASSWORD` 저장. 코드 박지 않음.
- 의견서 docId 추출에 JS 렌더링 필요한 경우 Playwright 사용. 미설치면 자동 폴백 후 PDF 누락 처리.

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| 로그인 실패 | 공개 영역만 진행, `login_used: false` 기록 |
| 의견서 docId 추출 실패 | Playwright 폴백 → 그래도 실패면 PDF 없이 진행 |
| HTTP 5xx | 백오프 1회 재시도 |
| PDF 0바이트 / HTML 응답 | metadata.errors에 기록, 파일 삭제 |

## 호출 예

```
Agent(nice-collector, model="opus",
      prompt="company=보령, cmp_cd=XYZ7777, output_dir=_workspace/nice/보령/
              로그인 자격증명 nice.env 가 있으면 전체 재무부표까지 수집.
              스킬: nice-collection 사용
              산출: indicators.json, opinion.pdf, metadata.json")
```
