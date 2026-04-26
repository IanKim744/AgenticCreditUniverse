---
name: judgment-review
description: 신규 종목 1차 판단(O/△/X)을 풀 단위로 검수하여 등급 간 형평성과 직전 반기 대비 변동 안정성(≤10%) 가드레일을 적용한 최종 판단을 산출한다. "판단 검수", "유니버스 분류 일관성 점검", "AI 판단 풀 검수" 요청 시 사용한다.
---

# Judgment Review

`AgenticCreditUniverse/comment_generator/judgment_review.py` 를 호출하여 Stage 1 잠정 판단을 풀 단위로 재평가한다. 모델은 Claude Sonnet 4.6 (1M 컨텍스트), 시스템 프롬프트는 `comment_generator/prompt_template_judgment.py` 가 정의한 9개 룰을 사용한다.

## 호출 방식

```bash
$ROOT/.venv/bin/python AgenticCreditUniverse/comment_generator/judgment_review.py \
  --comments-dir _workspace/comments/ \
  --xlsx "AgenticCreditUniverse/legacy version/26.1Q 유니버스_작업완료.xlsx" \
  --grade-input _workspace/grade_input.json \
  --env-file AgenticCreditUniverse/secrets.env \
  --output _workspace/judgment/stage2_review.json
```

옵션:
- `--grade-input` (선택): `{회사: {rating, outlook}}` JSON. 생략 시 엑셀의 26.1H 등급/전망 컬럼 사용.
- `--max-tokens 8192`: 풀 종목 수가 30~50개 정도면 충분. 100개 넘으면 16384로 상향.
- `--no-cache`: 시스템 프롬프트 캐싱 비활성화 (디버깅용).
- `--no-1m-context`: 1M 베타 헤더 비활성화 (티어 권한 없을 때).

표준 출력은 검토 종목 수 + 비중 metrics + 가드레일 위반 여부 + 토큰 사용량 JSON.

## 입력 데이터 구조

`judgment_review.py` 가 내부적으로 두 종류 데이터를 조립한다:

**A. `review_companies`** (이번 빌드에서 검토할 종목들, comments_dir 의 *.json 기반):
```json
{
  "name": "에스케이씨",
  "grade": "A",
  "outlook": "S",
  "stage1": "△",
  "stage1_reason": "FCF 4년 적자·부채비율 232% 부담",
  "monitoring": "①장기등급 A+→A 하향 ②26년 초 1조원 유증 추진...",
  "prior_25_2h": "O"
}
```

**B. `existing_universe`** (기존 풀의 (회사, 26.1H 등급/전망, 25.2H 분류) — 엑셀에서 추출):
```json
{
  "name": "다우기술",
  "grade_25_2h": "A0", "outlook_25_2h": "S",
  "grade_26_1h": "A0", "outlook_26_1h": "S",
  "universe_25_2h": "O"
}
```

## 출력 스키마

`_workspace/judgment/stage2_review.json`:
```json
{
  "decisions": {
    "에스케이씨": {
      "final": "△",
      "stage1": "△",
      "prior_25_2h": "O",
      "movement": "downgrade",
      "adjusted": false,
      "rationale": "..."
    },
    ...
  },
  "inversions": [
    {
      "high_grade_company": "에스케이씨",
      "high_grade": "A/S",
      "high_grade_decision": "△",
      "low_grade_company": "한솔테크닉스",
      "low_grade": "BBB+/S",
      "low_grade_decision": "O",
      "rationale": "에스케이씨는 등급 A이나 4년 연속 FCF 적자·전지박 손상 누적으로 추가 하향 압력. 한솔테크닉스는 BBB+이나 일회성 비용 제외 시 영업이익 흑자 유지, 신용도 하방 제한적."
    }
  ],
  "metrics": {
    "denominator": 24,
    "downgrade_count": 2,
    "downgrade_pct": 0.083,
    "upgrade_count": 1,
    "upgrade_pct": 0.042,
    "new_entries": 0,
    "guardrail_breaches": []
  },
  "model": "claude-sonnet-4-6",
  "stop_reason": "end_turn",
  "usage": { ... },
  "_meta": { "retried": false, "parse_failures": [] }
}
```

`movement` 값:
- `"stay"` — final = prior_25_2h
- `"downgrade"` — O→△, △→X, O→X
- `"upgrade"` — △→O (X→△, X→O는 풀 정상 흐름이 아님 — 발생 시 inversions 사유 필수)
- `"new"` — 신규 진입(prior_25_2h = null), 비중 분모 제외

## 행동 룰 (시스템 프롬프트 R1~R6 요약)

| ID | 룰 | 설명 |
|----|------|------|
| R1 | 등급 비례 기본 | 높은 등급일수록 분류 ≥ |
| R2 | 역전 허용 — 하향 | 등급 하향 + 재무 급격 악화 → 고등급도 △/X |
| R3 | 역전 허용 — 강건 | 추가 하향 가능성 낮음 + 업황·재무 양호 → 저등급도 O |
| R4 | 하향 비중 ≤ 10% | downgrade_count / denominator ≤ 0.10. 초과 시 약한 케이스 되돌림 |
| R5 | 상향 비중 ≤ 10% | △→O 비중 ≤ 0.10. 동일 절차 |
| R6 | 신규 진입 처리 | prior_25_2h=null → movement="new", 분모 제외 |

## 가드레일 적용 절차 (모델이 따르는 순서)

1. 모든 review_companies 에 대해 1차 final 산출 (R1~R3 적용)
2. downgrade/upgrade/stay 분류
3. downgrade_pct 계산 → > 0.10 이면 R4 적용 (약한 케이스 되돌림 + adjusted=true)
4. upgrade_pct 동일 절차 (R5)
5. metrics 기록

코드 측에서도 sanity check: 응답 후 `downgrade_pct`, `upgrade_pct` 가 0.10 초과면 1회 재호출. 재호출 후에도 위반이면 `metrics.guardrail_breaches` 기록 후 결과 반환 — 사용자 수기 검수에 위임.

**엑셀 머지 시 활용:**
- `decisions[name].final` → col 16 "AI 판단" 셀 (기호만)
- `decisions[name].rationale` → col 17 "AI 판단 사유" 셀 (조정/가드레일 사유 포함, wrap_text)
- `inversions`, `metrics` 는 엑셀 미반영 — 검수 보고용으로 JSON 에서만 확인.

## 환경변수

- `ANTHROPIC_API_KEY` 필수. `secrets.env` 에서 로드.

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| JSON 파싱 실패 | 1회 재호출 (피드백 메시지 포함). 2회 실패 시 빈 골격 반환 + `_meta.parse_failures` 기록 |
| 가드레일 위반 | 1회 재호출. 재호출 후도 위반이면 결과 반환 + breaches 기록 (실행 중단 안 함) |
| API 429 | SDK 자동 재시도(2회). 그래도 실패 시 즉시 중단(머지 단계 입력 부재) |
| API 키 미설정 | 즉시 중단 (`secrets.env` 안내) |

## 호출 예 (오케스트레이터에서)

```
Agent(judgment-reviewer, model="opus",
      prompt="comments_dir=_workspace/comments/
              xlsx='AgenticCreditUniverse/legacy version/26.1Q 유니버스_작업완료.xlsx'
              grade_input=_workspace/grade_input.json
              output=_workspace/judgment/stage2_review.json
              스킬: judgment-review 사용
              규칙: 직전 반기 대비 하향·상향 비중 ≤10%, 등급 역전 시 사유 필수")
```
