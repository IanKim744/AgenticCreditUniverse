---
name: comment-generation
description: 4개 입력(신평 의견서 PDF + NICE 재무지표 + DART 사업내용·연결주석 + 뉴스/리스크 리포트)을 종합해 26.1H 검토 코멘트(400~600자)를 Claude Sonnet 4.6으로 생성한다. "26.1H 코멘트 작성", "유니버스 코멘트 생성", "종합 코멘트 만들어" 요청 시 사용한다.
---

# Comment Generation

기존 모듈 `AgenticCreditUniverse/comment_generator/generate_comment.py` 를 호출하여 종목별 26.1H 검토 코멘트를 생성한다. 모델은 Claude Sonnet 4.6 (1M 컨텍스트), 시스템 프롬프트는 `comment_generator/prompt_template.py` 가 정의한 26.1H 형식 규약을 사용한다.

## 호출 방식

**다종목 일괄 호출이 기본** (Anthropic ITPM 한도 회피용 자동 sleep + 429 백오프). 단건 호출은 디버깅 용도로만.

### A. 다종목 일괄 (권장) — `batch_generate.py`

```bash
# jobs.json: 종목별 입력 경로 + grade_info 의 배열
$ROOT/.venv/bin/python AgenticCreditUniverse/comment_generator/batch_generate.py \
  --jobs /tmp/jobs.json \
  --output-dir _workspace/comments/ \
  --env-file AgenticCreditUniverse/secrets.env \
  --sleep-seconds 90 \
  --no-1m-context
```

**`jobs.json` 스키마**:
```json
[
  {
    "company": "대한해운",
    "pdf": "_workspace/nice/대한해운/opinion.pdf",
    "nice": "_workspace/nice/대한해운/nicerating_1766746_CFS.json",
    "dart_business": "_workspace/dart/대한해운/business.txt",
    "dart_notes":    "_workspace/dart/대한해운/notes.txt",
    "news":          "_workspace/news/대한해운/대한해운/report.md",
    "grade_info":    "그룹사: SM"
  }
]
```

옵션:
- `--sleep-seconds 90` : 종목간 sleep (Anthropic ITPM 한도 회피, 기본 90초)
- `--rate-limit-backoff 60` : 429 발생 시 추가 백오프 (기본 60초)
- `--no-1m-context` : 1M 베타 헤더 비활성화(티어 권한 없을 때)
- `--max-tokens 4096` : 출력 상한

표준 출력은 종목별 결과 + 합계 토큰 + 길이 위반 종목 리스트 JSON.

### B. 단건 호출 — `generate_comment.py`

```bash
$ROOT/.venv/bin/python AgenticCreditUniverse/comment_generator/generate_comment.py \
  --company "롯데물산" \
  --pdf _workspace/nice/롯데물산/opinion.pdf \
  --nice _workspace/nice/롯데물산/indicators.json \
  --dart-business _workspace/dart/롯데물산/business.txt \
  --dart-notes _workspace/dart/롯데물산/notes.txt \
  --news _workspace/news/롯데물산/report.md \
  --grade-info "AA-/Stable (이전: A+/Stable)" \
  --env-file AgenticCreditUniverse/secrets.env \
  --output _workspace/comments/롯데물산.json
```

옵션 동일. **2종목 이상이면 단건 호출 대신 `batch_generate.py` 사용**(429 회피).

## 입력 매핑 규약

오케스트레이터가 다음 경로 컨벤션을 따라 호출한다:

| 인자 | 경로 |
|------|------|
| `--pdf` | `_workspace/nice/{company}/opinion.pdf` |
| `--nice` | `_workspace/nice/{company}/indicators.json` |
| `--dart-business` | `_workspace/dart/{company}/business.txt` |
| `--dart-notes` | `_workspace/dart/{company}/notes.txt` |
| `--news` | `_workspace/news/{company}/report.md` |
| `--grade-info` | master.json + 사용자 등급 입력에서 결합 |
| `--output` | `_workspace/comments/{company}.json` |

**누락 처리:** 위 5개 파일 중 일부가 없어도 호출은 진행한다(스크립트 내에서 `[자료 없음]` 폴백). 단 4개 파일 이상 누락이면 오케스트레이터가 호출 자체를 스킵하고 `_workspace/failed/{company}.json` 기록.

## 출력 스키마

`_workspace/comments/{company}.json`:
```json
{
  "company": "롯데물산",
  "comment": "동사는 '82년 설립된 롯데그룹 부동산 핵심 계열사로 ...",
  "judgment_stage1": "O",
  "judgment_stage1_reason": "AA-/안정적 등급 + 그룹 신용도 견고, FCF 흑자 지속",
  "model": "claude-sonnet-4-6",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 12345,
    "output_tokens": 678,
    "cache_creation_input_tokens": 1024,
    "cache_read_input_tokens": 0
  }
}
```

**필드 설명:**
- `comment`: 첫 줄 `[AI 판단]` 헤더가 제거된 본문(400~600자).
- `judgment_stage1`: 종목 단위 1차 잠정 판단 (`"O"` / `"△"` / `"X"`). 모델 응답 첫 줄에서 파싱.
- `judgment_stage1_reason`: 판단 근거 30~80자.
- 응답 첫 줄이 `[AI 판단] (O|△|X) | 근거` 패턴을 위반하면 `judgment_stage1=null` + 본문은 raw 보존. 후속 단계(judgment-review)가 None 을 보수적으로 △ 처리.

## 행동 규칙 (모듈/프롬프트가 강제하는 것 + 스킬에서 추가 보장)

1. **자료 우선순위.** 정제 연결재무지표(별도 폴백) 1순위, 의견서·뉴스는 정성 보강. (DART 연결주석은 토큰 폭주 원인이라 본 모듈 입력에서 제외 — 시스템 프롬프트가 이미 규정.)
2. **환각 금지.** 입력에 없는 수치 창작 금지.
3. **포맷 엄수.** 첫 줄 `[AI 판단] (O|△|X) | 근거` 헤더 + 빈 줄 + 본문 400~600자, 4개 의미 단위. 본문은 "동사는…" 시작 권장.
4. **본문만 출력.** 머리말·맺음말 없음. 단, 첫 줄 AI 판단 헤더는 강제.
5. **AI 1차 판단 = 종목 단위.** 풀 단위 형평성·안정성 검수는 별도 단계(`judgment-review`)에서 수행. 본 단계는 종목 자체 자료만 보고 등급 비례 기본으로 잠정 분류.
6. **캐싱 활용.** 시스템 프롬프트에 ephemeral cache_control 적용되어 종목 다수 처리 시 입력 비용 ~90% 절감.

## 보안

- API 키는 `claude api.env` 에서만 로드. 코드/로그/메시지에 키 노출 금지.
- `APIStatusError` 발생 시 status/type만 출력(내부 메시지에 키 들어가지 않도록 모듈이 처리).
- 이번 세션에서 키가 외부에 노출된 사실이 확인되었으므로, 작업 완료 후 사용자에게 rotate 권장(오케스트레이터 보고에 포함).

## 환경변수

- `ANTHROPIC_API_KEY` 필수. `claude api.env` 에서 로드.

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| API 429 (단건) | SDK 자동 재시도(2회) |
| API 429 (일괄) | `batch_generate.py` 가 추가 60초 백오프 후 1회 재시도 |
| API 5xx | SDK 자동 재시도. 재실패 시 종목 스킵 |
| `stop_reason: "max_tokens"` | `--max-tokens 8192` 로 1회 재시도. 그래도 잘리면 종목 스킵 |
| `stop_reason: "refusal"` | 종목 스킵, failed에 기록 |
| 환경변수 누락 | 즉시 중단(`secrets.env` 또는 `claude api.env` 안내) |

## ITPM 정책

Anthropic 티어별 분당 input tokens 한도가 있다. 첫 빌드(2026-04-25) 관찰값:
- 종목 1건 호출당 input ≈ 110~130K tokens
- 75초 sleep 으로는 한도 회복 부족 (3종목 중 2건 429)
- 120초 sleep 또는 90초 + 60초 백오프로 안정 통과

`batch_generate.py` 기본값은 종목간 90초 + 429 시 60초 추가 백오프. 사용자 티어가 더 높으면 `--sleep-seconds` 를 줄여 호출 시간 단축 가능.

## 호출 예 (오케스트레이터에서)

```
Agent(comment-writer, model="opus",
      prompt="company=롯데물산
              inputs:
                pdf=_workspace/nice/롯데물산/opinion.pdf
                nice=_workspace/nice/롯데물산/indicators.json
                dart_business=_workspace/dart/롯데물산/business.txt
                dart_notes=_workspace/dart/롯데물산/notes.txt
                news=_workspace/news/롯데물산/report.md
                grade_info='AA-/Stable (이전: A+/Stable)'
              output=_workspace/comments/롯데물산.json
              스킬: comment-generation 사용")
```
