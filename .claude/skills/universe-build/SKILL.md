---
name: universe-build
description: 신용평가 유니버스(반기 단위)를 자동 작성·갱신한다. "유니버스 빌드", "26.1H 유니버스 작성", "유니버스 갱신/업데이트/재실행", "발행기관 리스트로 코멘트 일괄 생성", "유니버스 보강", "신규 종목 추가", "특정 종목만 다시", "이전 결과 기반으로 개선" 등 신용평가 유니버스 자동화 요청 시 반드시 사용한다. 단, 단일 모듈 동작 원리 설명·컬럼 의미 질문 등 단순 질의에는 사용하지 않는다.
---

# Universe Build — 신용평가 유니버스 오케스트레이터

발행기관 리스트를 받아 4개 자료원(DART·NICE·Perplexity·신평 의견서 PDF)을 수집하고, 26.1H 검토 코멘트를 생성하여 엑셀 유니버스에 머지하는 전체 워크플로우를 조율한다.

**실행 모드:** 서브 에이전트 (수집은 종목 단위 fan-out 병렬, 이후 파이프라인)

## Phase 0: 컨텍스트 확인

작업 시작 전 `_workspace/` 상태를 확인하여 실행 모드를 결정한다.

| 상태 | 모드 | 행동 |
|------|------|------|
| `_workspace/` 미존재 | **초기 실행** | 새로 생성 후 전체 Phase 수행 |
| `_workspace/` 존재 + 사용자가 신규 입력(새 종목 리스트, 새 엑셀) 제공 | **새 실행** | 기존 `_workspace/` 를 `_workspace_prev/` 로 이동, 처음부터 |
| `_workspace/` 존재 + 사용자가 부분 수정 요청 (예: "특정 종목만 다시", "코멘트만 다시") | **부분 재실행** | 해당 Phase부터 시작, 이전 산출물 캐시 활용 |

부분 재실행 트리거 키워드: "다시", "재실행", "업데이트", "수정", "보완", "{종목}만", "{단계}만".

## Phase 1: 입력 검증

사용자 입력에서 다음을 확정:

1. **발행기관 리스트** (`companies`): 한국어 정식 사명 리스트. 누락 시 사용자에게 요구.
2. **소스 엑셀** (`source_xlsx`): 직전 반기 유니버스(예: `legacy version/26.1Q 유니버스_작업완료.xlsx`). 없으면 빈 시트 + 컬럼 헤더로 시작.
3. **등급/전망 입력** (선택): 26.1H 신용등급/등급전망 표(CSV/JSON). 없으면 코멘트만 갱신하고 등급 셀은 빈칸.
4. **출력 엑셀** (`output_xlsx`): 기본값 `out/26.1H 유니버스.xlsx`.

환경변수 검증:
- `ANTHROPIC_API_KEY` (claude api.env)
- `DART_API_KEY`
- `PERPLEXITY_API_KEY`
- (선택) NICE 로그인 자격증명

하나라도 미설정이면 **즉시 사용자에게 안내하고 중단**한다. 코드/로그에 키 노출 금지.

## Phase 2: 마스터 매핑 (master-curator)

`master-curator` 에이전트를 호출하여 `_workspace/master/master.json` 생성·갱신.

**호출 시 인자:**
- `companies`: Phase 1 입력
- `existing_master_path`: 있으면 병합

**검증:**
- `unresolved.json` 에 종목이 있으면 사용자에게 보고하고 진행 여부 확인. 사용자가 "스킵 후 진행" 선택하면 unresolved 종목은 이후 단계에서 자동 제외.

## Phase 3: 자료 수집 (fan-out 병렬)

각 종목에 대해 3개 수집 에이전트를 **동시 실행**한다(`run_in_background=true`):

```
for company in companies (resolved):
    parallel:
      - Agent(dart-collector,  model=opus, run_in_background=true)
      - Agent(nice-collector,  model=opus, run_in_background=true)
      - Agent(news-collector,  model=opus, run_in_background=true)
```

**병렬도 제한:** 종목 단위로 한 번에 5개까지만 동시 실행(API rate limit 보호). 5개 종목씩 batch.

**실패 정책:**
- 각 에이전트는 자체적으로 1회 재시도. 그래도 실패하면 metadata에 `error` 필드 기록 후 종료.
- 한 종목의 일부 자료가 실패해도 다른 자료원은 계속. comment-writer 단계에서 누락 처리.
- 한 종목 전체가 실패하면 `_workspace/failed/{company}.json` 에 기록.

**진행 로그:** `_workspace/progress.jsonl` 에 종목별 단계 완료 시각을 append.

## Phase 4: 코멘트 생성 (일괄 호출 + 자동 sleep)

`batch_generate.py` 헬퍼로 **여러 종목을 한 번에** 호출한다. 종목간 자동 sleep(기본 90초)으로 Anthropic ITPM 한도를 회피하고, 429 발생 시 추가 60초 백오프 후 1회 재시도한다.

### Step 1 — jobs.json 자동 생성

마스터 매핑 + Phase 3 산출물 경로를 결합하여 jobs.json 을 작성한다. 컨벤션은 `comment-generation` 스킬에 정의됨.

```python
# 의사코드
import json, pathlib
ROOT = pathlib.Path("/Users/.../AgenticCreditUniverse")
master = json.loads((ROOT/"_workspace/master/master.json").read_text())
jobs = []
for company, info in master["companies"].items():
    cmp_cd = info.get("cmp_cd")
    if not cmp_cd:
        continue  # unresolved 종목 자동 제외
    nice_dir = ROOT/f"_workspace/nice/{company}"
    nice_json = next(nice_dir.glob(f"nicerating_{cmp_cd}_*.json"), None)
    news_dir = ROOT/f"_workspace/news/{company}"
    news_md = next(news_dir.glob("*/report.md"), None)
    jobs.append({
        "company": company,
        "pdf": str(nice_dir/"opinion.pdf") if (nice_dir/"opinion.pdf").exists() else None,
        "nice": str(nice_json) if nice_json else None,
        "dart_business": str(ROOT/f"_workspace/dart/{company}/business.txt"),
        "dart_notes":    str(ROOT/f"_workspace/dart/{company}/notes.txt"),
        "news":          str(news_md) if news_md else None,
        "grade_info":    f"그룹사: {info.get('group','')}".strip(),
    })
(ROOT/"_workspace/jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2))
```

### Step 2 — 일괄 호출

```bash
$ROOT/.venv/bin/python AgenticCreditUniverse/comment_generator/batch_generate.py \
  --jobs _workspace/jobs.json \
  --output-dir _workspace/comments/ \
  --env-file AgenticCreditUniverse/secrets.env \
  --sleep-seconds 90 \
  --no-1m-context
```

**누락 처리:** 입력 파일이 없으면 그대로 누락 표기로 진행(코멘트 생성기 자체가 `[자료 없음]` 폴백). 단, 4개 입력 중 3개 이상 누락이면 jobs.json 작성 단계에서 사전 제외하고 `_workspace/failed/{company}.json` 에 사유 기록.

**산출:**
- `_workspace/comments/{company}.json` (종목별)
- 표준 출력의 `summary` 에 합계 토큰·실패 종목·길이 위반(<400자 또는 >600자) 종목 목록

**길이 위반 처리:** `len_violations` 에 종목이 있으면 사용자에게 보고하고 해당 종목만 재호출 권장 (시스템 프롬프트가 400~600자 강제하지만 입력 자료가 매우 풍부한 경우 초과 가능).

**판단 누락 처리:** `judgment_missing` 에 종목이 있으면 (모델 응답 첫 줄 `[AI 판단] (O|△|X) | 근거` 패턴 위반) 사용자에게 보고. 후속 Phase 5(judgment-reviewer)가 None을 보수적으로 △ 처리하지만, 1차 판단 자체가 누락되면 풀 단위 형평성 검수에서 그 종목은 사실상 △로 고정됨 — 신뢰도 낮은 케이스라 재호출 권장.

## Phase 5: 판단 검수 (judgment-reviewer)

`judgment-reviewer` 에이전트를 호출하여 Stage 1 잠정 판단(O/△/X)을 풀 단위로 재평가한다. 등급 간 형평성 + 직전 반기 대비 변동 안정성 가드레일을 적용한 **최종** 판단을 산출한다.

**호출 시 인자:**
- `comments_dir`: `_workspace/comments/` (Stage 1 산출물)
- `xlsx`: 기존 유니버스 엑셀 (25.2H 직전 분류 추출용)
- `grade_input` (선택): Phase 1 등급 입력. 생략 시 엑셀의 26.1H 컬럼 사용.
- `output`: `_workspace/judgment/stage2_review.json`

**행동 룰 요약** (상세는 `judgment-review` 스킬 참고):
- R1 등급 비례 기본 / R2-R3 역전 허용(하향 추세, 강건 케이스) — 모든 역전에 사유 필수
- R4 하향 비중 ≤ 10% / R5 △→O 상향 비중 ≤ 10% — 직전 분류 보유 종목이 분모, 신규 진입은 분모 제외
- 한도 초과 시 가장 약한 케이스부터 직전 분류로 되돌림(`adjusted=true`)

**산출:**
- `_workspace/judgment/stage2_review.json` — `{decisions, inversions, metrics, ...}`

**가드레일 위반 처리:**
- `metrics.guardrail_breaches` 가 비어있지 않으면 사용자에게 보고. 모델이 1회 재호출 후에도 한도를 못 맞춘 케이스 — 머지는 진행하되 사용자 수기 검수에서 우선 점검 필요.
- 인버전(등급 역전) 케이스가 많으면(예: 풀의 20% 초과) 사용자에게 사유 일괄 검토 권장.

## Phase 6: 엑셀 머지 (universe-merger)

`universe-merger` 에이전트를 호출하여 최종 엑셀 생성.

**호출 시 인자:**
- `source_xlsx`: Phase 1 입력 (또는 in-place output 자체)
- `comments_dir`: `_workspace/comments/`
- `judgment_path`: `_workspace/judgment/stage2_review.json` (Phase 5 산출)
- `master_path`: `_workspace/master/master.json`
- `grade_input`: Phase 1 등급 입력
- `output_xlsx`: Phase 1 지정 경로

**보존 정책 (필수 강조):**
- 사용자 수기 작성 셀(25.2H 검토 코멘트, 그룹사, 26.1H 담당, 25.2H 등급/전망, **심사역 최종 판단(col 18)**)은 절대 덮어쓰지 않는다.
- **자동 갱신 컬럼 7개**: `26.1H 신용등급`(col 7), `26.1H 등급전망`(col 8), `26.1H 유니버스`(col 10), `26.1H 검토 코멘트`(col 13), `26.1H 유니버스 의견변동`(col 14, 수식), `AI 판단`(col 16, 기호), `AI 판단 사유`(col 17, rationale wrap_text).
- "AI 판단" 컬럼(col 16) = Stage 2 `decisions[name].final` (O/△/X 기호만).
- "AI 판단 사유" 컬럼(col 17) = Stage 2 `decisions[name].rationale` (조정/가드레일 사유 포함, wrap_text=True, 폭 50).
- "심사역 최종 판단" 컬럼(col 18) = 수기 보존 영역, 절대 미갱신.
- 의견변동(col 14)은 정적 값이 아닌 **엑셀 수식** — I열(25.2H)↔J열(26.1H) 비교, O>△>X 순위로 ▲/▽/-. 자세한 수식은 `excel-merge` 스킬 참고.

**산출:**
- `out/26.1H 유니버스.xlsx`
- `out/backup/{timestamp}_원본.xlsx` (입력 백업)
- `_workspace/merge/report.json` (갱신 좌표 + 누락 사유)

## Phase 7: 보고

사용자에게 최종 보고:

```
완료. 출력: out/26.1H 유니버스.xlsx

종목 통계:
  - 입력 발행기관: N개
  - 매핑 성공: N개 / unresolved: N개
  - 자료 수집 성공: N개 / 일부 실패: N개 / 전체 실패: N개
  - 코멘트 생성 성공: N개 / 1차 판단 누락: N개
  - 엑셀 신규 행: N개 / 갱신 행: N개

AI 판단 결과 (Stage 2 검수 후):
  - O 편입: N개 / △ 조건부: N개 / X 미편입: N개
  - 직전 반기 대비 변동: 하향 N개 ({pct}%) / 상향 N개 ({pct}%) / 신규 N개
  - 등급 역전 케이스: N개 (사유는 stage2_review.json 의 inversions 참고)
  - 가드레일 위반: {empty 또는 사유}

토큰 사용 (Claude Sonnet 4.6):
  - Stage 1 (코멘트 생성): in/out/cache_read 합계
  - Stage 2 (판단 검수): in/out/cache_read 합계

누락/실패 종목 (검토 필요):
  - {company}: {사유}
  ...

⚠️ claude api.env 의 API 키가 이번 세션에 노출되었습니다.
   작업 완료 후 https://console.anthropic.com 에서 키를 회수(rotate)해 주세요.
```

## Phase 8: 피드백 수집 (선택)

사용자에게 다음 중 1~2개를 묻는다(부담 없게):
- 코멘트 톤·길이 조정 필요?
- 추가/제외할 종목?
- 머지 정책 보정 필요(어떤 셀을 보존/갱신)?

피드백이 들어오면 변경 대상을 분류하여(스킬 / 에이전트 정의 / 오케스트레이터) 적절한 곳을 수정한다.

## 데이터 전달 컨벤션

작업 디렉토리: 프로젝트 루트 기준 `_workspace/` (상대 경로).

```
_workspace/
├── master/
│   ├── master.json          # 발행기관 매핑
│   └── unresolved.json
├── dart/{company}/
│   ├── business.txt
│   ├── notes.txt
│   ├── metadata.json
│   └── raw/
├── nice/{company}/
│   ├── indicators.json
│   ├── opinion.pdf
│   └── metadata.json
├── news/{company}/
│   ├── report.md
│   ├── raw.json
│   └── metadata.json
├── comments/
│   └── {company}.json
├── judgment/
│   └── stage2_review.json
├── merge/
│   └── report.json
├── failed/
│   └── {company}.json
├── progress.jsonl
└── cache/                    # corpCode.xml 등 외부 자원 캐시
```

최종 산출은 사용자 지정 경로(`out/26.1H 유니버스.xlsx` 기본). `_workspace/` 는 사후 검증·재실행을 위해 보존.

## 에러 핸들링 (오케스트레이터 단)

| 에러 | 정책 |
|------|------|
| API 429/5xx (수집/생성) | 에이전트 자체 1회 재시도 → 실패 시 종목 스킵 후 진행 |
| 환경변수 누락 | 즉시 중단, 사용자에게 안내 |
| 매핑 실패 | unresolved.json 분리, 사용자 확인 후 진행 |
| 엑셀 컬럼 스키마 불일치 | 즉시 중단, 자동 보정 금지 |
| comment-writer 토큰 한도 초과 | max_tokens 늘리기 1회 시도, 그래도 실패면 종목 스킵 |

**재시도 후 실패 시:** 해당 종목/단계는 결과에서 제외하고 보고서에 누락 명시. 상충 데이터는 삭제하지 않고 출처 병기.

## 보안

- 모든 API 키는 `*.env` 파일에서만 로드(`.gitignore` 처리됨).
- 메시지/로그/에러 메시지에 키 노출 금지.
- `claude api.env` 의 키는 사용자가 한 번 노출했으므로 작업 후 rotate 권장 메시지를 보고에 포함.

## 테스트 시나리오

**정상 흐름:**
입력: 3개 발행기관(다우기술, 롯데물산, 보령). 모두 매핑 성공, 자료 수집 성공.
기대: `out/26.1H 유니버스.xlsx` 에 3개 행이 26.1H 코멘트와 함께 채워짐. 25.2H 코멘트는 보존.

**에러 흐름:**
입력: 5개 발행기관 중 1개는 신생법인(NICE 미수록), 1개는 DART 보고서 미접수.
기대: 매핑 1건 unresolved 보고 + 사용자 확인 → 4개 진행. 그중 1개는 NICE 누락 명시 코멘트로 생성. 머지 후 누락 사유가 `merge/report.json` 에 기록.
