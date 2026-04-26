---
name: dart-collection
description: 종목별로 DART 최신 정기보고서에서 사업의 내용 + 연결재무제표 주석(별도 폴백)을 추출한다. "DART 자료 수집", "사업의 내용 가져와", "공시 주석 추출" 요청 시 사용한다.
---

# DART Collection

기존 모듈 `AgenticCreditUniverse/dart_scraper/dart_scraper.py` 를 호출하여 종목별 DART 산출물을 표준 디렉토리에 저장한다.

## 호출 방식

기본은 **CLI 호출**(스크래퍼는 argparse 기반 CLI 진입점을 가지고 있음).

```bash
cd AgenticCreditUniverse/dart_scraper
python dart_scraper.py \
  --corp-code 00139975 \
  --output-dir ../../_workspace/dart/다우기술/
```

> 실제 인자명은 모듈 README 또는 `--help` 출력으로 확인. 변형이 있으면 같은 의미의 인자로 매핑.

대안으로 import 호출:
```python
sys.path.insert(0, "AgenticCreditUniverse/dart_scraper")
import dart_scraper as ds
ds.collect(corp_code="00139975", output_dir="_workspace/dart/다우기술/")
```

## 출력 정규화 규약

종목 디렉토리 `_workspace/dart/{company}/` 에 다음 파일을 둔다:

| 파일 | 내용 |
|------|------|
| `business.txt` | 사업의 내용 정제 텍스트(헤더 제거, 표 → 탭 텍스트) |
| `notes.txt` | 연결재무제표 주석(연결 우선·없으면 별도) |
| `business.html` | 원본 HTML (선택) |
| `notes.html` | 원본 HTML (선택) |
| `metadata.json` | 메타정보 |
| `raw/` | 스크래퍼 원본 zip/xml (검증·재처리용) |

`metadata.json` 스키마:
```json
{
  "company": "다우기술",
  "corp_code": "00139975",
  "report_type": "사업보고서",
  "receipt_no": "20250515000123",
  "receipt_date": "2025-05-15",
  "business_extracted": true,
  "notes_basis": "consolidated",
  "extraction_failed": false,
  "collected_at": "2026-04-25T11:42:00+09:00",
  "errors": []
}
```

`notes_basis` ∈ `"consolidated" | "separate" | "none"`.

## 행동 규칙

1. **연결 우선.** 스크래퍼가 연결주석을 시도하고, 없으면 별도로 폴백한다(자체 정책 활용).
2. **최신 1건만.** 사업/반기/분기 보고서 중 가장 최근 접수 1건만 처리.
3. **빈 산출 OK.** 섹션 추출 실패 시 빈 파일 + `extraction_failed: true` 기록. 이후 단계가 누락 처리하도록 함.
4. **캐시 활용.** 동일 corp_code 산출물이 24시간 이내면 호출 생략(사용자 명시 시 강제 재수집).

## 환경변수

- `DART_API_KEY` 필수. `.env` 파일에서 로드. 코드 박지 않음.

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| API 429 | 백오프 1회 재시도 |
| API 5xx | 백오프 1회 재시도, 재실패 시 metadata.errors 기록 후 종료 |
| corpCode 매칭 0건 | 호출 자체 스킵(매핑 단계에서 걸러져야 함) |
| 정기보고서 미접수 | metadata에 `report_type: null` 기록, business/notes 빈 파일 |

## 호출 예 (오케스트레이터에서)

```
Agent(dart-collector, model="opus",
      prompt="company=롯데물산, corp_code=00266961, output_dir=_workspace/dart/롯데물산/
              스킬: dart-collection 사용
              산출: business.txt, notes.txt, metadata.json")
```
