# AgenticCreditUniverse

> **자율 AI 신용유니버스** — 반기적 신용평가 유니버스 점검 프로세스 자동화 및 품질 가드레일 구현
>
> 한화투자증권 디지털 혁신 AI 경진대회 출품작 (2026.04). 1인팀 · 리스크심사팀 · 김영벽

---

## 한 문장 정의

DART · 신평사 재무지표 · 뉴스를 자동 수집해 Claude가 코멘트 초안을 작성하고, **2-stage 가드레일**이 풀 단위 형평성·안정성을 검수하는 신용유니버스 점검 AI 에이전트. Claude Code의 **agents · skills · hooks** 시스템 위에서 7개 에이전트와 8개 스킬로 워크플로우를 구성한다.

## 왜 만들었나

| | AS-IS (수기) | TO-BE (ACU) |
|---|---|---|
| **인력 투입** | 10명 × 3주 ≈ **150 man-day/반기** | ≈ **2 man-day/반기** (검수만 사람) |
| **인건비 환산** | 약 1.5억원/반기 = 3억원/연 | 약 200만원/반기 |
| **종목당 시간** | 약 6 work-hour | 약 5분 |
| **형평성** | 심사역 10명 간 기준 편차 | Stage 2 가드레일이 흡수 |
| **안정성** | 반기마다 흔들림 | soft cap ≤10%로 변동 보존 |
| **본질 업무 비중** | 약 30% (페이퍼워크가 70%) | 절감된 시간 전체가 의사결정·현업 협의로 |

손실 회피 추정 (신평 3사 3년차 누적부도율 기반):
- 보수안: (1.5조 + 1조) × 5% × 1.22%p ≈ **약 15억원/3년**
- 낙관안: 동일 익스포져 × 10% × 5.93%p ≈ **약 148억원/3년**

---

## 시스템 구조

```
                    ┌─────────────────────── Claude Code harness ───────────────────────┐
                    │                                                                    │
   .claude/agents/  │  master-curator   dart-collector   nice-collector   news-collector │
                    │       │                │                 │                  │      │
   .claude/skills/  │  master-mapping   dart-collection   nice-collection   news-research│
                    │                            │                                       │
                    │                            ▼                                       │
                    │                     comment-writer  (Stage 1, Sonnet 4.6)          │
                    │                            │                                       │
                    │                            ▼                                       │
                    │                     judgment-reviewer  (Stage 2, Opus)             │
                    │                            │                                       │
                    │                            ▼                                       │
                    │                     universe-merger  (엑셀 18컬럼)                  │
                    └────────────────────────────┬───────────────────────────────────────┘
                                                 ▼
                                      output/26.1H 유니버스.xlsx
                                                 +
                                          웹 매트릭스 대시보드
                                          (Next.js + Tailwind)
```

7개 에이전트 + 8개 스킬은 모두 `.claude/{agents,skills}/` 안에 **선언적 markdown**으로 정의되어 외부 SDK·프레임워크 없이 표준 harness만으로 동작한다.

### 6 에이전트 매트릭스

| 에이전트 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `master-curator` | 발행기관 ↔ corpCode ↔ cmpCd 매핑 SSOT | 종목명 | `_workspace/master/master.json` |
| `dart-collector` | DART 사업의 내용 + 연결주석 | corpCode | `_workspace/dart/{종목}/` |
| `nice-collector` | 신평사 표준 재무 7년 + 의견서 PDF | cmpCd | `_workspace/nice/{종목}/` |
| `news-collector` | Perplexity 뉴스·리스크 정밀 검색 | 종목명 | `_workspace/news/{종목}/{검색키}/` |
| `comment-writer` | Stage 1 코멘트 (300~600자) + 잠정 O/△/X | 자료 4종 | `_workspace/comments/{종목}.json` |
| `judgment-reviewer` | Stage 2 풀 단위 가드레일 (R1~R6 + soft cap) | comments 일괄 | `_workspace/judgment/stage2_review.json` |
| `universe-merger` | 엑셀 18컬럼 머지 (자동/수기 분리) | 위 모든 산출물 | `output/26.1H 유니버스.xlsx` |

---

## 차별점

### 1. Claude Code harness × 도메인 지식 코드화

외부 벤더·컨설팅 발주 없이 **실무자가 harness · agents · skills를 직접 조립**. 단일 LLM 호출 대신 역할 분리(Sonnet 4.6 = 작성자 / Opus = 검수자), 자료원별 전용 collector. 심사역의 도메인 지식("수치 비교 표기 의무" / "명사형 종결어미 70%+" / "신평사 수치 우선" / "환각 금지")을 `prompt_template.py`로 코드화하여 **사람 의존성을 자산으로 전환**.

### 2. 2-stage 판단 가드레일

```
Stage 1  ·  comment-writer  →  종목별 잠정 O/△/X
                                       ↓
Stage 2  ·  judgment-reviewer  →  풀 단위 R1~R6 룰
                                  + 하향/상향 비중 ≤10% soft cap
                                  + 등급 역전 합리화 (R2)
                                       ↓
Final  →  엑셀 P열 "AI 판단" + Q열 "AI 판단 사유"
                              + R열 "심사역 최종 판단" (수기 절대 보존)
```

**실증 케이스 1 — 에스케이씨**: Stage 1에서 EBIT 3년 연속 적자·부채비율 233%·FCF 만성 적자로 'X' 제안 → Stage 2 가드레일이 하향 비중 한도 위반 감지 → 직전 반기 분류('△') 유지. 단기물 한정 편입 허용.

**실증 케이스 2 — 등급 역전 합리화**: 에스케이씨(A0 / 안정적)가 △인 반면 대한해운(A3+ 단기)이 O. 표면 등급만 보면 비논리적이지만, R2 룰("단기등급은 낮으나 재무건전성이 우월하면 편입 가능")을 명시적 룰로 반영하여 심사역 실제 분류와 일치.

상세 출처: [`_workspace/judgment/stage2_review.json`](./_workspace/judgment/stage2_review.json)

### 3. AI 코딩 도구 활용 흐름

```
①  V0 / Lovable          →  ②  DESIGN-GUIDE.md          →  ③  Claude Code (Cursor 병행)
프론트엔드 디자인 AI         16섹션 디자인 SSOT 정의            Next.js + Tailwind + shadcn/ui
초안 코드 생성              토큰 · 컴포넌트 · 레이아웃        본 구현 + 인터랙션
```

디자인부터 구현까지 풀 AI 협업. 외부 벤더 발주 시 6개월·억 단위 추정되는 작업을 1인 실무자가 단기간에 완성.

---

## 빠른 시작

### 환경 변수 (`AgenticCreditUniverse/secrets.env`)

```bash
ANTHROPIC_API_KEY=...           # Claude Sonnet 4.6 / Opus
DART_API_KEY=...                # https://opendart.fss.or.kr
PERPLEXITY_API_KEY=...          # 뉴스 수집 (또는 OpenRouter Gemini)
NICE_USERNAME=...  NICE_PASSWORD=...   # 선택 (의견서 PDF 자동 다운)
```

### 의존성

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r AgenticCreditUniverse/comment_generator/requirements.txt
# 선택: NICE PDF 자동 다운로드용
pip install playwright && playwright install chromium
```

### 종목 1건 End-to-end 실행

```bash
# 1. 마스터 매핑 (한 번만)
python AgenticCreditUniverse/scripts/resolve_nice.py 에스케이씨

# 2. 자료 수집 (DART + 신평 + 뉴스)
python AgenticCreditUniverse/dart_scraper/dart_scraper.py --co 에스케이씨
python AgenticCreditUniverse/nicerating_scraper/nicerating_scraper.py --co 에스케이씨
python AgenticCreditUniverse/pplx_news/pplx_risk_analyst.py --co 에스케이씨

# 3. Stage 1 코멘트 생성
python AgenticCreditUniverse/comment_generator/generate_comment.py --co 에스케이씨

# 4. Stage 2 풀 검수 (모든 종목 모인 뒤)
python AgenticCreditUniverse/comment_generator/judgment_review.py

# 5. 엑셀 머지
python _workspace/merge_run.py
```

또는 Claude Code 사용 시 `/universe-build` 슬래시 커맨드로 풀 파이프라인 실행.

### 웹 대시보드 기동

```bash
cd AgenticCreditUniverse/web
make backend    # FastAPI :8787
# 다른 터미널에서
make frontend   # Next.js :3000
```

`http://localhost:3000` 접속, 단일 계정 PoC 로그인 (`risk` / `1962`).

---

## 26.1H 시범 적용 결과 (22종목)

| 항목 | 값 |
|---|---|
| 처리 종목 | 22 종목 |
| Stage 2 가드레일 작동 | 1건 (에스케이씨 X→△) |
| 등급 역전 합리화 | 1건 (R2 룰) |
| 평균 input tokens / 종목 | 약 110~126K |
| 평균 코멘트 길이 | 700~735자 |

상세는 [`_workspace/batch_summary.json`](./_workspace/batch_summary.json) 및 [`_workspace/judgment/stage2_review.json`](./_workspace/judgment/stage2_review.json) 참조.

---

## 디렉토리 구조

```
AgenticCreditUniverse/
├─ .claude/                             # Claude Code harness 정의
│   ├─ agents/                          # 7 에이전트 (markdown frontmatter)
│   ├─ skills/                          # 8 스킬 (SKILL.md + scripts/)
│   └─ settings.json
├─ AgenticCreditUniverse/                # 핵심 모듈
│   ├─ comment_generator/               # Stage 1·2 + 프롬프트 템플릿
│   ├─ dart_scraper/                    # DART 사업의 내용 + 연결주석
│   ├─ nicerating_scraper/              # 신평사 7년 재무 + 의견서 PDF
│   ├─ pplx_news/                       # Perplexity 뉴스·리스크
│   ├─ scripts/                         # resolve_nice.py 등
│   ├─ web/                             # 매트릭스 + 종목 상세 (Next.js)
│   │   ├─ DESIGN-GUIDE.md              # 디자인 SSOT (16섹션)
│   │   ├─ PLAN.md                      # 정보 구조 SSOT
│   │   ├─ frontend/                    # Next.js + Tailwind v4 + shadcn/ui
│   │   └─ backend/                     # FastAPI + SQLite
│   └─ secrets.env                      # .gitignore (커밋 금지)
├─ _workspace/                          # 파일 산출물 SSOT
│   ├─ master/{master.json, watch_industries.json}
│   ├─ dart/{종목}/{business.txt, notes.txt}
│   ├─ nice/{종목}/{*_CFS.json, opinion.pdf}
│   ├─ news/{종목}/{검색키}/{report.md, raw.json}
│   ├─ comments/{종목}.json             # Stage 1 결과
│   └─ judgment/stage2_review.json      # Stage 2 풀 검수
├─ output/
│   └─ 26.1H 유니버스.xlsx              # 18컬럼 엑셀 (사용자 머지본)
├─ CLAUDE.md                            # 프로젝트 운영 원칙 + 변경이력
└─ README.md                            # 본 문서
```

---

## 핵심 디자인 원칙

자세한 정책은 [`CLAUDE.md`](./CLAUDE.md) 변경이력 표를 참조.

- **연결재무 우선·없으면 별도** 폴백 (NICE 표준 재무지표)
- **연결재무제표 주석 우선·없으면 별도** 폴백 (DART)
- **입력에 없는 수치는 만들지 않음** (환각 금지)
- **사용자 수기 셀 절대 보존** — 엑셀 머지 시 자동 갱신 컬럼만 덮어씀
- **수치 비교 의무 표기** — 전년 대비 증감은 괄호 또는 화살표 병기 (`(전년 100%)` / `100%→70%`)
- **명사형 종결어미 70%+** — `…함/임/됨` (신평 보고서 관행)
- **신평사 수치 우선** — PDF·뉴스 수치는 lag 가능성, 충돌 시 신평사 채택

---

## 라이선스 · 크레딧

| 영역 | 도구 |
|---|---|
| LLM | Anthropic Claude Sonnet 4.6 (1M ctx) · Opus |
| 검색·뉴스 | OpenRouter Gemini 3.1 Pro · Perplexity API |
| 웹 프레임워크 | Next.js 15 (App Router) + Tailwind v4 |
| 컴포넌트 | shadcn/ui + Recharts + TanStack Virtual v3 |
| 스크래핑 | requests + lxml + beautifulsoup4 + (선택) playwright |
| 엑셀 | openpyxl |
| PPTX | python-pptx |
| 폰트 | Pretendard + Geist Mono |
| 디자인 AI | V0 · Lovable (초안 단계) |
| 코딩 AI | Claude Code · Cursor |

본 저장소는 한화투자증권 디지털 혁신 AI 경진대회 1차 서류심사 출품을 위해 공개되었습니다.

---

## 변경 이력

[CLAUDE.md 변경 이력 섹션](./CLAUDE.md#변경-이력)을 참조하세요. 본 PoC 운영 중 6회 이상의 prompt 개선 사이클이 기록되어 있으며, 모두 22종목 시범 적용 → 검토자 피드백 → prompt_template 갱신 → 재생성의 흐름입니다.

---

> **출품자**: 김영벽 (Kim Youngbyeok)
> **소속**: 한화투자증권 리스크심사팀
> **연락**: youngbyeok.kim@hanwha.com · 010-4051-2902
> **출품**: 디지털 혁신 AI 경진대회 1차 서류심사 (2026.04.30)
