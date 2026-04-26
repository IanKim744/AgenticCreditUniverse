# 크레딧 유니버스 웹 대시보드 — 설계 제안

## Context

현재 시스템은 CLI/스킬 기반 자동화로 4종 자료(DART·NICE·News·신평PDF)를 수집해 `_workspace/` 캐시에 적재하고, Claude Sonnet 4.6으로 26.1H 코멘트를 생성한 뒤 `output/26.1H 유니버스.xlsx` (15컬럼)에 머지하는 구조다. 데이터 자산은 이미 종목 단위로 정형화되어 있으나, 사용자는 매번 엑셀을 열어 비교·검토해야 한다. 본 제안은 **이미 쌓여 있는 산출물을 그대로 활용**하여 (1) 매트릭스 화면 (2) 종목별 상세 대시보드를 구성하기 위한 데이터 매핑·UI 구성·기술 스택을 정리한 것이다. 데이터 모델을 새로 만드는 게 아니라 **기존 파일 산출물에 얇은 인덱스/뷰 레이어를 얹는 것**이 핵심 원칙이다.

---

## 1. 활용 가능한 데이터 자산 정리

| 자산 | 경로 패턴 | 형식 | 화면 활용 |
|---|---|---|---|
| 종목 마스터 | `_workspace/master/master.json` (+ `unresolved.json`) | JSON | 매트릭스 행 키, 그룹사·aliases·식별자 |
| 엑셀 유니버스 | `output/26.1H 유니버스.xlsx` | XLSX **17col** | 매트릭스 컬럼의 SSOT (자동/수기 분리 규칙) |
| NICE 재무지표 | `_workspace/nice/{co}/nicerating_*_{CFS\|OFS}.json` | JSON 7년 시계열 | 대시보드 차트(매출·EBITDA·차입금·부채비율) |
| NICE 의견서 | `_workspace/nice/{co}/opinion.pdf` | PDF | PDF 임베드/다운로드 |
| DART 사업의 내용 | `_workspace/dart/{co}/business.txt` (+ `business_section.{txt,html}` 변종) | 평문 TXT | 검색·하이라이트, 원공시 링크 |
| DART 연결주석 | `_workspace/dart/{co}/notes.txt` (+ `notes.html` 변종) | 평문 TXT | 동일 |
| 뉴스/리스크 | `_workspace/news/{co}/{검색키}/report.md` (+ raw.json) | MD 4섹션 | 호재/악재 카드, 인용 링크 |
| **Stage 1 코멘트·판단** | `_workspace/comments/{co}.json` | JSON `{comment, judgment_stage1, judgment_stage1_reason, model, usage}` | 종목 대시보드 코멘트 본문 + 잠정 판단 표시 |
| **Stage 2 풀 검수** (신규) | `_workspace/judgment/stage2_review.json` | JSON `{decisions[co]: {final, movement, adjusted, reason}, inversions[], metrics}` | 매트릭스 26.1H 유니버스·AI 판단 컬럼, 가드레일 적용 여부 표시 |
| 배치 진행 | `_workspace/batch_summary.json`, `jobs.json` | JSON | (PoC UI 미노출, 백엔드 진행률 추적용) |
| 백업/이전 반기 | `output/backup/`, `AgenticCreditUniverse/legacy version/26.1Q 유니버스_작업완료.xlsx`, 엑셀 L컬럼(25.2H 코멘트) | XLSX | 반기 비교 |

> **불변 원칙:** 엑셀의 자동 갱신 4컬럼(G/H/J/M)과 절대 보존 컬럼(B~F, I, K, L, O)의 분리 규칙은 웹 UI에서도 그대로 강제한다. 자동 컬럼은 락 아이콘, 수기 컬럼은 인플레이스 편집 가능.

---

## 2. 화면 1 — 매트릭스 (전체 종목 테이블)

> **v2 갱신 (2026-04-26):** 외부 시안과 자체 프롬프트 결과물 두 개를 비교한 뒤, 각각의 강점만 합쳐 컬럼/KPI/분포 차트를 보강했다. 변경점: ① 상단에 등급·업종 분포 차트 2개 도입(외부 시안), ② 평가사 3사(KIS/KR/NICE) 등급 컬럼 추가(외부 시안), ③ 인라인 재무지표 4개 컬럼 토글로 도입(외부 시안), ④ 25.2H 등급/전망 비교 컬럼 추가(둘 다 누락이었음), ⑤ 자동/수기 컬럼 시각 구분(🔒/✏️) 명문화.

> **v3 갱신 (2026-04-26):** 사용자 피드백 — "개발관리자 화면 같다"는 인상을 제거하고 **신용 분석가용 도구로 톤 재정렬**. 변경점: ① 매트릭스의 수집상태 5배지 컬럼·캐시 만료·토큰 사용 컬럼 **전부 삭제**, ② KPI에서 "데이터 수집 완료율" 카드 제거, ③ 헤더 "전체 빌드 실행" 버튼 제거, ④ 종목 대시보드 우상단 "재실행 버튼 4개 + 전체 재실행" 제거, ⑤ Tab 6 "작업·이력" 통째로 삭제(탭 6→5), ⑥ 운영성 정보(파이프라인 상태·작업 로그·토큰 비용)는 UI에서 숨기고 백엔드 cron/CLI로만 관리.

> **v4 갱신 (2026-04-26) — PoC 확정 사양:** ① **단일 계정 로그인** (id `risk` / pw `1962`), ② 매트릭스/대시보드는 **읽기 전용 뷰어**로 한정 — 수기 컬럼(그룹사/담당/25.2H 등) 인라인 편집 제거, 편집은 엑셀에서만, ③ **심사역 검수 워크플로우** 추가 — 종목 대시보드에서 유니버스 분류 최종 확정 시 "검수완료" 처리, 매트릭스에 **검수여부 컬럼** 노출, ④ 평가사 3사 컬럼을 **유효신용등급 단일 컬럼**으로 통합 (출처 신평사명은 종목 대시보드에서 표기), ⑤ 스냅샷 비교는 **전기(25.2H) ↔ 당기(26.1H) 2-스냅샷**으로 확정, ⑥ 인라인 재무지표 4개는 **컬럼 토글(default off)**.

> **v6 갱신 (2026-04-26) — 디자인 가이드 정합:** `AgenticCreditUniverse/AgenticCreditUniverse/AgenticCreditUniverse/web/DESIGN-GUIDE.md` v3과의 충돌을 plan 우선으로 해소. ① 매트릭스 KPI 4번 "수집률" → "검수 진행 현황", ② 헤더의 Refresh·Edit Toggle 제거, ③ 종목 상세 "심사역 코멘트 편집 모드" 제거(읽기 전용 유지), ④ Bulk Action은 엑셀 export만, ⑤ 종목 상세 "변경 이력/백업" → "반기 히스토리"로 톤다운, ⑥ 로그인 페이지 명세 plan/가이드 양쪽 보강. 동시에 가이드의 강점 수용: ⓐ 종목 상세 5탭 → **단일 세로 스크롤 + 우측 floating TOC**(가이드 §4.6) + 인쇄/PDF 친화, ⓑ 신평사 의견서 **등급 변동 타임라인** 시그니처 차트(§11.3) 도입, ⓒ TanStack Virtual 1,000행 가상화 명시.

> **v7 갱신 (2026-04-26) — 매트릭스 KPI 재구성 + 분포 차트 행 + 유의업종 컬럼 구현:** ① **KPI 카드 ②**를 "등급 분포 미니바" → **"부정적 전망 N (X.X%)"**으로 교체, ② **KPI 카드 ①**에 가능/조건부/미편입 가로 카운트 추가, ③ **KPI 카드 아래 분포 차트 행 신설** — 좌측 신용등급 막대(`RatingDistChart`, 당기 기준) + 우측 업종 도넛(`IndustryDistChart`, 동적 카테고리), ④ **유의업종 컬럼 신규** — 매트릭스 "업종" 옆에 ○/— 칩 (Col 3 `industry_2026`), ⑤ **유의업종 자동 판정 SSOT** — `_workspace/master/watch_industries.json` (사용자 운영, 매 반기 갱신; 26.1H 기준 7개: 2차전지·석유화학·철강·상영관·건설·저축은행·부동산신탁) → `build_index.py` 가 industry 매칭 시 자동 ○ 부여 (사용자 명시 'O'는 보존), ⑥ **22종목 업종 백필** — `_workspace/scripts/seed_industries.py` 로 master.json + Excel Col 4 동시 갱신.

> **v5 갱신 (2026-04-26) — 백엔드 동기화:** 대화 중 진화한 에이전트/스킬·산출물·엑셀 구조를 plan에 정합. 변경점:
> - **2-stage 판단 구조 신설**: ① Stage 1 (`comment-writer`, 종목 자료만으로 잠정 O/△/X) → `_workspace/comments/{co}.json` 에 `judgment_stage1` 필드, ② **신규** Stage 2 (`judgment-reviewer`, 풀 단위 형평성·안정성 검수 — R1~R6 룰 + 하향/상향 비중 ≤10% soft cap) → `_workspace/judgment/stage2_review.json`.
> - **신규 에이전트**: `judgment-reviewer` (모델 Opus, 내부에서 Sonnet 4.6 호출). **신규 스킬**: `judgment-review`.
> - **엑셀 15컬럼 → 17컬럼**: Col 16 **"AI 판단"**(Stage 2 final, 자동) + Col 17 **"심사역 최종 판단"**(수기, **절대 보존**). 매트릭스 v3의 "검수여부" 컬럼은 Col 17 입력 여부로 산출.
> - **폴더 리네임**: `pplx_risk_skhynix_gemini/` → `pplx_news/`. **신규 폴더**: `AgenticCreditUniverse/comment_generator/`(수집·판단 모듈 통합), `AgenticCreditUniverse/legacy version/`(이전 반기 엑셀 보관).
> - **신규 스크립트**: `comment_generator/{judgment_review.py, extract_existing_universe.py, prompt_template_judgment.py}`, `.claude/skills/master-mapping/scripts/resolve_nice.py`.
> - **DART 산출 파일명**: 표준 입력은 `_workspace/dart/{co}/business.txt`, `notes.txt` (확장자 `_section.txt`/`.html` 변종도 공존). **News 경로**: `_workspace/news/{co}/{검색키}/` 이중 폴더 패턴.

### 2.1 컬럼 구성

엑셀 15컬럼 + 보강 컬럼(평가사 3사·재무지표·종목코드) = **약 18컬럼**. 기본은 핵심 10컬럼만 표시, 나머지는 컬럼 토글. 운영 메타(수집상태·캐시·토큰)는 UI에서 노출하지 않음.

★ = 기본 노출 / 모든 컬럼은 **읽기 전용** (편집은 엑셀에서만). 헤더 라벨의 "전기/당기"는 `period_config.json` 동적 로드. 아래는 "당기 = 26.2H, 전기 = 26.1H" 가정.

| # | 컬럼 | 타입 | 출처 / 비고 |
|---|------|------|------|
| 1 ★ | 발행기관 (+종목코드 회색 작게) | 링크 (키) | 엑셀 Col 1 + master.json `stock_code` |
| 2 ★ | 그룹사 | 텍스트 | 엑셀 Col 15 |
| 3 ★ | 업종 | 태그 | 엑셀 Col 4 (전 종목 백필 완료, master.json `industry` SSOT) |
| 4 ★ | **유의업종** | ○ / — 칩 | 엑셀 Col 3 `industry_2026`. `watch_industries.json` 카테고리와 자동 매칭(빌드 시 build_index.py) — 사용자 수기 'O' 우선 보존. |
| 5 ★ | 전기({previous}) 등급/전망 | 배지 2개 | 엑셀 Col 5/6 |
| 6 ★ | **당기({current}) 등급/전망** | 배지 2개 (전기 대비 ▲▼ 인디케이터) | 엑셀 Col 7/8 |
| 7 ★ | **유효신용등급** | 단일 배지 | NICE 우선, 출처 신평사는 종목 대시보드에서만 표기 |
| 8 | 전기({previous}) 유니버스 | O/△/X 칩 | 엑셀 Col 9 |
| 8b (옵션) | 전기({previous}) 심사역 최종 판단 | O/△/X 칩 (보존, 분모용) | 엑셀 Col 16 — 컬럼 토글 default off |
| 9 ★ | **당기({current}) 유니버스 (AI 판단)** | O/△/X 칩 + Stage 2 가드레일 적용 시 ⚙ 표식 | 엑셀 Col 10 / `judgment/stage2_review.json.decisions[co].final` |
| 9b ★ | **당기({current}) 심사역 최종 판단** | O/△/X 칩 (미입력 시 회색 "—") | 엑셀 Col 17 / 종목 대시보드 검수 패널 산출 |
| 10 ★ | **의견변동** ({previous}→{current}) | ▲ green / ▼ red / - gray | 엑셀 Col 14 |
| 11 (옵션) | 매출액 | 단위 억원, 간략 표기(3.0K억) | NICE indicator 최신연도 |
| 12 (옵션) | 영업이익률 | % | NICE 산출 |
| 13 (옵션) | 부채비율 | % | NICE 산출 |
| 14 (옵션) | 이자보상배율 | x배 | NICE 산출 |
| 15 ★ | **당기({current}) 코멘트** | 1줄 미리보기 + 호버 풀팝 | 엑셀 Col 13 / comments/{co}.json |
| 16 | 전기({previous}) 코멘트 | 호버 풀팝 | 엑셀 Col 12 |
| 17 ★ | 담당 | 칩 | 엑셀 Col 11 (반기 롤오버 시 carry forward) |
| 18 ★ | **검수여부** | "검수완료"(녹색) / "미검수"(회색) 칩 | 엑셀 Col 17 입력 여부 = 심사역 최종 판단 채워짐 = 검수완료. PoC 운영 중에는 `_workspace/review_status.json` 미러링 가능. |
| 19 | 마지막 갱신 | 상대시간 (작은 회색) | 각 metadata.json `generated_utc` 최신값 |

**편집 정책 (PoC):** 매트릭스/대시보드의 모든 컬럼은 **읽기 전용**. 그룹사·담당·전기 보존 컬럼 등 수기 데이터는 **엑셀에서 수정** → 빌드 사이클에 반영. UI에서 변경 가능한 것은 오직 종목 대시보드의 **"유니버스 분류 확정"** 액션(=검수여부 토글).

**컬럼 토글:** 인라인 재무지표 4개(11~14)는 default off, 컬럼 설정에서 on/off.

### 2.1.5 상단 분포 차트 영역 (KPI 카드 아래 신설)

KPI 4카드 바로 아래 한 줄 — `DistributionRow.tsx` 가 `RatingDistChart` + `IndustryDistChart` 마운트 (각각 `lg:grid-cols-2`).

- **좌:** 당기({current}) **유효신용등급 분포** — 세로 막대차트(`RatingDistChart`). X축 = AAA / AA / A / BBB / BB / B↓ (당기 `rating_curr`의 1차 그룹). Y축 = 종목 수. 막대 색상 = `ratingColorVar()` (DESIGN-GUIDE §2.3 시맨틱 컬러). 우상단에 "단위: 종목 수" 보조 라벨.
- **우:** **업종 분포 도넛**(`IndustryDistChart`) — `industry` 동적 카테고리, 8색 순환(`var(--chart-1..8)`, DESIGN-GUIDE §7.2). 우측에 라벨·카운트 범례 리스트.
- 클릭 필터링은 후속 작업.

### 2.2 인터랙션

- **검색/필터:** 발행기관·그룹사 자유검색 / 업종·등급·유니버스·의견변동(▲▼)·담당자·수집 상태 멀티 필터
- **정렬:** 등급(매핑 테이블 기반), 의견변동, 갱신일자
- **행 클릭:** 종목 대시보드로 라우팅 (`/company/{slug}`)
- **일괄 액션:** 선택 행 → "코멘트만 재생성" / "News 강제 재수집" / "엑셀 export"
- **신규 종목 추가:** 모달 → master-curator 백엔드 호출 → 매핑 실패 시 unresolved 처리 화면
- **수기 셀 편집:** 인라인 편집 → 저장 시 엑셀 머지 키와 동일 규칙으로 sticky 보관 (재머지에도 보존)

### 2.3 상단 KPI 패널 (4카드 가로) — v7

1. **{current} 검토** — 큰 숫자(전체 종목 수) + 가로 인라인 카운트 `O 가능 N · △ 조건부 N · X 미편입 N` (심사역 최종 우선, 없으면 AI 판단 집계)
2. **부정적 전망** — 큰 숫자 + sub: "X.X% (N/total)" — `parseWatch(watch_curr)==='negative'` 카운트
3. **의견 변동** — ▲N 녹색 / ▼N 적색 / -N 회색 가로 정렬
4. **검수 진행 현황** — `검수완료 N / 전체 N` + 진행률 바

> v7: 분포(등급·업종)는 KPI 카드에서 빠져 §2.1.5 분포 차트 행으로 분리. KPI는 모두 "행동가능한 단일 숫자" 톤으로 통일.

### 2.4 헤더 액션바

- 좌: "신용등급 유니버스 · 26.1H 검토"
- 우: `엑셀 다운로드`(outline) + 우측 끝에 사용자 표시("risk") + 로그아웃
- 빌드 실행/신규 종목 추가는 UI에서 제외. 마스터 갱신/재빌드는 백엔드 cron 또는 CLI에서 처리.

### 2.5 좌측 필터 패널

- 발행기관·그룹사 자유검색
- 그룹사 / 업종 (multi-select)
- 26.1H 등급, 26.1H 유니버스 (multi-select chips)
- 의견변동 (▲/▼/-)
- 담당 (multi-select)
- **검수여부 (검수완료 / 미검수)** ← PoC 핵심 필터

---

## 3. 화면 2 — 종목 상세 대시보드 (`/company/{slug}`)

> **v6 구조 변경**: 디자인 가이드 §4.6에 따라 **5탭 구조 폐기 → 단일 세로 스크롤 + 우측 floating TOC**로 전환. 인쇄/PDF 친화 + 신용 보고서 톤. 본 섹션의 "Tab N." 표기는 "§ N."(섹션)으로 재해석.

레이아웃: `grid-cols-1 lg:grid-cols-[1fr_180px]` — 좌측 본문 세로 스크롤, 우측 TOC sticky.

상단에 **헤더 카드** (발행기관 / 종목코드 / 그룹사 / 업종 / 당기 등급·전망 / 의견변동 / 담당). 우상단에는 **검수 액션 패널**과 **마지막 갱신일**만 노출.

### 3.0 검수 액션 패널 (우상단, 핵심)

심사역 검수 워크플로우 — PoC의 유일한 사용자 쓰기 액션. AI 2-stage 판단을 출발점으로 삼고, 심사역이 최종 확정.

- **AI 판단 표시 (읽기 전용)**:
  - Stage 1 잠정: `comments/{co}.json.judgment_stage1` + 한 줄 사유 (`judgment_stage1_reason`)
  - **Stage 2 final**: `judgment/stage2_review.json.decisions[co]`
    - `final`(O/△/X), `movement`(stay/downgrade/upgrade/new)
    - `adjusted: true` 면 ⚙ 가드레일 적용 표식 + 사유 노출
    - 등급 역전(`inversions[]`) 케이스면 사유 강조 표시
- **현재 상태 배지**: "미검수"(회색) 또는 "검수완료"(녹색)
- **유니버스 분류 확정 폼**: O / △ / X 라디오 (**default = Stage 2 final**)
- **AI 동의 체크박스**: "AI 판단에 동의" (체크 시 라디오 자동 = Stage 2 final, 변경 시 자동 해제)
- **확정 코멘트(선택)**: 짧은 메모 입력 (1~2줄, AI와 다른 결정을 내린 경우 권장)
- **`검수 확정` primary 버튼** → `POST /review` 호출 → Col 17(심사역 최종 판단) 채워짐 → 매트릭스 18번 컬럼이 "검수완료"로 변경
- **`확정 해제` 보조 버튼** → 검수완료 상태에서만 노출 → Col 17 비움 → 미검수
- 확정 이력(이전 결정 시각·사용자 `risk`·이전 값·AI 판단과의 일치 여부)을 패널 하단에 작게 표시

### 섹션 구조 (단일 세로 스크롤, 우측 TOC로 점프) — v6 재구성

순서: 개요 → 재무 → 신평사 의견 → AI 코멘트 → 뉴스/리스크 → DART 공시(접힘) → 반기 히스토리

> 가이드 §4.6 + plan v4 검수 워크플로우를 결합. 모든 영역 읽기 전용. DART처럼 본문이 매우 긴 영역만 부분적으로 collapsible/Tabs 허용(가이드 §13 Don't 예외).

#### § 1. 개요
- **반기 비교 카드 2장:** 전기({previous}) ↔ 당기({current}) (등급·전망·유니버스)
- **유효신용등급 출처 표기**: 등급 옆에 "NICE 신용평가 · 발행일 2025-12-15" 식 작은 캡션
- **AI 판단 요약 카드** (Stage 1 잠정 + Stage 2 final, movement, adjusted/inversion 표식)
- 우측 검수 액션 패널과 정보 짝꿍 — 분석가가 §1만 읽고도 판단 가능하도록

#### § 2. 재무 추이 (NICE)
- **연결/별도 토글** (CFS/OFS)
- **시계열 차트 4개** (2019~2025): 매출·OP·EBITDA / 부채비율·차입금의존도 / FCF / 이자보상배율
- 가이드 §7.2 표준 패턴 적용 (chart-1/chart-2 듀얼 라인, 임계선 ReferenceLine)
- **지표 테이블** (NICE 원본 그대로, bold 행은 강조, tabular-nums)
- **CSV 다운로드 버튼**

#### § 3. 신평사 의견 (PDF + 시그니처 타임라인) — v6 추가
- **NICE PDF 임베드** (react-pdf), 평정사·발행일 명시
- **등급 변동 타임라인 차트** (가이드 §11.3 시그니처 모션):
  - x축: 시간(연·반기), y축: 등급 매핑 인덱스
  - 등급 변동 지점에 큰 마커(반지름 6px) + 변동 방향 색상(`--watch-positive`/`--watch-negative`)
  - 첫 진입 시 0.4s scale 애니메이션(0.7→1.0) 1회 — 그 외 위치에는 모션 금지
- 데이터 출처: NICE indicator의 등급 라인 시계열 (없는 분기는 보간 없이 점만 표시)

#### § 4. AI 코멘트
- **당기({current}) 코멘트 본문** (마크다운 렌더, 인용 강조, "AI 생성" 미니 라벨 — 가이드 §8 패턴)
- **전기({previous}) 코멘트** (접힘, 펼치면 diff 비교)
- ❌ 편집 모드 없음. 분석가가 추가 메모를 남기려면 우측 검수 패널의 "확정 코멘트(선택)" 필드를 사용

#### § 5. 뉴스/리스크
- `report.md` 4섹션을 **카드로 분리**: Executive Summary / Critical Risk / Business & Financials / Conclusion
- **인용 링크 패널:** raw.json의 citations → 발행일·도메인·title (favicon 동반)
- **리스크 등급 태그** (Low/Medium/High) — 향후 분류 모델 추가 예정
- ❌ "다시 검색" 버튼 없음 (운영 액션 미노출)

#### § 6. DART 공시 (collapsible)
- **상단:** 보고서명 + 접수번호 + 접수일 + DART 원공시 외부링크 (`https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}`)
- **사업의 내용** 본문 (검색/하이라이트, 내부 TOC 자동 생성)
- **연결재무제표 주석** 본문
- 가이드 §13 Don't의 "탭 분할 금지" 예외 — 본 영역만 짧게 Tabs 허용 가능

#### § 7. 반기 히스토리 (분석가용 시계열, 운영 메타 아님)
- snapshots/{전기, 전전기}/에서 조회 — 이 종목의 등급·유니버스·심사역 판단 변천
- 표 형태: 반기 / 등급 / 전망 / AI 판단 / 심사역 최종 판단 / 변동 사유
- "백업"이 아니라 **분석가의 시계열 비교 자료** 톤으로

> v3에서 삭제된 운영 정보(파이프라인 상태/작업 로그/토큰/캐시)는 본 화면에서 노출 금지. 가이드의 PipelineProgress·JobBadge 컴포넌트는 정의만 유지(향후 운영자 화면용).

---

## 4. 권장 기술 스택 (PoC 확정)

### 4.1 인증 — 단일 계정
- 로그인 화면 1장 (`/login`)
- 단일 자격: id `risk` / pw `1962` (서버 측 ENV 또는 settings.json에 보관, 클라이언트 노출 금지)
- 인증 방식: HTTP-only 세션 쿠키 (또는 단순 JWT). 미인증 접근은 모두 `/login`으로 리다이렉트
- 로그아웃 버튼은 매트릭스 헤더 우측에 작게

### 4.2 백엔드 — FastAPI
기존 파이썬 모듈을 그대로 import. **읽기 + 검수 토글만** 노출.

- `POST /api/auth/login` — 단일 계정 인증
- `POST /api/auth/logout`
- `GET /api/companies` — 매트릭스 행 리스트(검수상태 포함)
- `GET /api/companies/{slug}` — 상세 패키지 (코멘트·등급·출처 신평사 등)
- `GET /api/companies/{slug}/financials?kind=CFS` — NICE indicators
- `GET /api/companies/{slug}/disclosure` — DART business/notes
- `GET /api/companies/{slug}/news` — report.md + citations
- `GET /api/companies/{slug}/judgment` — Stage 1(코멘트 JSON) + Stage 2(stage2_review.json.decisions[co]) 통합 조회. `final`, `movement`, `adjusted`, `reason`, `inversion_note?`
- `POST /api/companies/{slug}/review` — 검수 확정 (body: `{universe: "O|△|X", agree_with_ai: bool, note?: string}`) → 엑셀 Col 17 + `_workspace/review_status.json` 동시 갱신
- `DELETE /api/companies/{slug}/review` — 확정 해제

> 그룹사/담당/25.2H 등 수기 컬럼 PATCH 엔드포인트는 **제공하지 않음** (편집은 엑셀에서만). 신규 종목 추가도 UI 미노출 (백엔드 CLI에서만).

### 4.3 데이터 저장
- 원본 산출물: `_workspace/` 그대로 (SSOT)
- **AI 판단**: `_workspace/comments/{co}.json` (Stage 1) + `_workspace/judgment/stage2_review.json` (Stage 2). 둘 다 백엔드 정기 빌드의 산출물 — 분석가 UI는 읽기만.
- 검수 상태: 엑셀 Col 17(심사역 최종 판단)이 SSOT. 추가로 `_workspace/review_status.json` — `{[slug]: {status: "done|none", universe?: "O|△|X", agree_with_ai: bool, note?, reviewed_by: "risk", reviewed_at: ISO8601}}`. 둘은 백엔드가 항상 동기화.
- 인덱스: SQLite 1개 (`_workspace/index.sqlite`) — 매트릭스 검색·정렬 가속용. master + 엑셀 17컬럼 + Stage 2 + comments 메타를 단일 뷰로 결합.

### 4.4 프론트 — Next.js
Next.js (App Router) + TypeScript + **Tailwind v4** (`@theme inline` 토큰) + shadcn/ui + TanStack Table v8 + **TanStack Virtual v3** (1,000행 가상화) + Recharts + react-pdf + lucide-react + Pretendard(셀프호스팅) + Geist Mono. **시각 명세는 `AgenticCreditUniverse/AgenticCreditUniverse/AgenticCreditUniverse/web/DESIGN-GUIDE.md` 단일 출처**. plan은 정보 구조·기능·데이터 흐름만 정의하고, 색·여백·컴포넌트 prop은 가이드 우선.

### 4.5 재빌드/마스터 갱신
- 분석가 UI에서 트리거 불가
- 야간 cron 또는 사용자가 CLI에서 `universe-build` 스킬 호출

---

## 5. 단계별 구현 권장 순서 (PoC)

1. **인덱스 레이어 (1~2일):** `_workspace/index.sqlite` 빌더 — master.json + 엑셀 + comments + nice/dart/news metadata 결합. 파일 mtime 기반 증분 리프레시.
2. **인증 + 읽기 API (1~2일):** FastAPI 단일 계정 로그인 + `/api/companies` + 상세 4개 엔드포인트.
3. **매트릭스 화면 (3~4일):** TanStack Table + 필터(검수여부 포함)·정렬·검색·컬럼 토글, KPI 4카드, 분포 차트 2개.
4. **종목 대시보드 (4~5일):** 5탭 구현. NICE 차트, DART 텍스트 뷰어, News 카드, PDF 임베드.
5. **검수 워크플로우 (1~2일):** 종목 대시보드 우상단 검수 패널 + `POST /review` + 매트릭스 18번 컬럼 갱신 + KPI 4번 카드 갱신.
6. **(선택) 시각 다듬기 (2~3일):** 디자인 시안 받은 후 Pretendard·색감·여백 폴리싱.

> v4에서 "수기 셀 편집" 단계 삭제 — 편집은 엑셀에서만. "검수 워크플로우" 단계가 그 자리를 대체.

---

## 6. 핵심 파일 / 재사용 포인트

- 데이터 인덱싱은 `AgenticCreditUniverse/scripts/` 신설 폴더에 `build_index.py`로. 기존 `.claude/skills/master-mapping/scripts/resolve_nice.py` 패턴 차용.
- 매트릭스 머지 키·자동/수기 규칙은 **universe-merger 에이전트의 머지 코드와 동일 사양**을 백엔드 모델로 옮긴다 (단일 진실의 원천 유지). 엑셀 17컬럼 중 자동 컬럼(7·8·10·13·14·**16**)과 절대 보존 컬럼(2~6·9·11·12·**17**·15) 분리 규칙은 그대로 강제.
- Stage 2 판단 로드는 `comment_generator/judgment_review.py`의 출력 스키마 (`stage2_review.json`)를 그대로 파싱. `extract_existing_universe.py`는 직전 반기 분류 추출에 재사용 — 안정성 분모 산정에 동일 함수 사용.
- DART 원공시 URL 빌더는 `_workspace/dart/{co}/metadata.json`의 `rcept_no` → 표준 DART URL 패턴.
- NICE indicator 차트 시리즈 매핑은 `nicerating_scraper`의 컬럼 정의 재사용.
- 뉴스 경로는 `_workspace/news/{co}/{검색키}/` 이중 폴더이므로 백엔드는 `glob` 또는 `metadata.json`에서 latest를 선택.

---

## 7. 검증 (End-to-End)

1. SQLite 인덱스 빌드 후 매트릭스 API에 종목 999개가 모두 노출되는지 확인.
2. 엑셀 자동 컬럼(G/H/J/M)을 강제로 변경한 뒤 universe-merger 재실행 → 수기 컬럼이 1셀도 변경되지 않는지 diff 확인.
3. NICE CFS/OFS 토글 시 시계열 차트 데이터가 뒤섞이지 않는지 검증.
4. 25.2H 코멘트(L컬럼)는 어떤 UI 액션을 해도 절대 변경되지 않음을 회귀 테스트.
5. 신규 종목 추가 → master-curator 매핑 실패 시 unresolved 처리 → CLI에서 수동 매핑 후 다음 빌드 사이클에 반영 확인.
6. 분석가 화면에서 작업 트리거·파이프라인 상태·토큰 정보가 일체 노출되지 않는지 시각 검수.

---

## 7.5 반기 전환 운영 (A안 + 롤오버 자동화)

### 7.5.1 운영 정책 — A안 확정

| 작업 | 자동/수기 | 위치 |
|---|---|---|
| 반기 컬럼 시프트·헤더 갱신·snapshots freeze | 자동 (결정론) | 새 스킬 `half-rollover` |
| 신규 종목 등록 (종목명·그룹사·업종·담당) | 수기 | input 엑셀에 행 추가 |
| 매핑(corp_code/cmp_cd) | 자동 | `master-curator` |
| 빌드 실행 (수집·코멘트·Stage1/2·머지) | 운영자 명시 트리거 | CLI(`universe-build`) — UI 미노출 유지 |
| 결과 반영 | 자동 | 파일 mtime 감지 → SQLite 인덱스 리프레시 |

### 7.5.2 새 스킬 — `half-rollover`

**에이전트는 추가하지 않는다.** 컬럼 시프트는 결정론적이라 LLM 추론 불필요.

- **위치**: `.claude/skills/half-rollover/SKILL.md`
- **트리거**: "26.2H 작업 엑셀 만들어줘" / "반기 롤오버" / "다음 반기 시작" / "{half} 유니버스 시작"
- **내부 구현**: `AgenticCreditUniverse/scripts/half_rollover.py` (순수 Python: openpyxl + JSON I/O)
- **인자**: `--current 26.2H` (필수), `--previous 26.1H` (선택, period_config에서 자동 추론)
- **동작 순서**:
  1. `period_config.json` 로드 + 새 current 기준으로 갱신
  2. 직전 빌드 완료 검증 (검수율, 누락 종목 등 — 경고만, 강제 중단 안 함)
  3. `_workspace/*` 전체를 `_workspace/snapshots/{previous}/`로 freeze (read-only)
  4. 전전전기 이상은 `snapshots/_archive/`로 이동 (3-tier 유지)
  5. `output/{current} 유니버스.xlsx` 생성 — 직전 17컬럼 매핑 적용 (아래 표)
  6. 새 빈 자동 컬럼·헤더 라벨은 동적 갱신
  7. 마이그레이션 보고서 출력 (`output/rollover_report.txt` — freeze 대상 수, 시프트 컬럼 매핑, 신규 빈 컬럼 수)

### 7.5.3 컬럼 시프트 매핑 (확정안)

**원칙**: 전전기(25.2H)는 새 input에서 모두 drop, snapshots에서만 조회. 직전 AI 판단(Stage 2)도 drop. 직전 심사역 최종 판단은 보존(분모 안정성).

#### 시프트 매핑 (예: 26.1H → 26.2H 롤오버)

| 직전 26.1H Col | 새 input 26.2H Col | 처리 |
|---|---|---|
| 1 발행기관 | 1 발행기관 | preserve |
| 2 현업 요청 분류 | 2 현업 요청 분류 | preserve |
| 3 26년 유의업종 | 3 26년 유의업종 | preserve (헤더는 연 단위 사용자 갱신) |
| 4 업종 | 4 업종 | preserve |
| 5 25.2H 신용등급 | — | **drop** |
| 6 25.2H 등급전망 | — | **drop** |
| 7 26.1H 신용등급 | **5 26.1H 신용등급(전기)** | shift |
| 8 26.1H 등급전망 | **6 26.1H 등급전망(전기)** | shift |
| 9 25.2H 유니버스 | — | **drop** |
| 10 26.1H 유니버스 | **9 26.1H 유니버스(전기)** | shift |
| 11 26.1H 담당 | **11 26.2H 담당** | **carry forward** (확정) |
| 12 25.2H 검토 코멘트 | — | **drop** |
| 13 26.1H 검토 코멘트 | **12 26.1H 검토 코멘트(전기)** | shift |
| 14 26.1H 의견변동 | — | **drop** (당기 빌드 시 재산출) |
| 15 그룹사 | **15 그룹사** | preserve |
| 16 AI 판단(Stage 2) | — | **drop** (확정) |
| 17 심사역 최종 판단 | **16 26.1H 심사역 최종 판단(전기 보존)** | **shift** (확정, 분모 안정성용) |

#### 새 input 26.2H 엑셀 — 17컬럼 최종 구조

| # | 헤더 | 자동/수기 | 출처 |
|---|---|---|---|
| 1 | 발행기관 | 키 | 직전 보존 |
| 2 | 현업 요청 분류 | 수기 | 직전 보존 |
| 3 | 26년 유의업종 | 수기 | 직전 보존 |
| 4 | 업종 | 수기 | 직전 보존 |
| 5 | 26.1H 신용등급 (전기) | 보존 | 직전 Col 7 시프트 |
| 6 | 26.1H 등급전망 (전기) | 보존 | 직전 Col 8 시프트 |
| 7 | **26.2H 신용등급 (당기)** | 자동, 빈칸 | new (빌드 시 채움) |
| 8 | **26.2H 등급전망 (당기)** | 자동, 빈칸 | new |
| 9 | 26.1H 유니버스 (전기) | 보존 | 직전 Col 10 시프트 |
| 10 | **26.2H 유니버스 (당기, AI 판단)** | 자동, 빈칸 | new |
| 11 | 26.2H 담당 | 수기, **carry forward** | 직전 Col 11 그대로 |
| 12 | 26.1H 검토 코멘트 (전기) | 보존 | 직전 Col 13 시프트 |
| 13 | **26.2H 검토 코멘트 (당기)** | 자동, 빈칸 | new |
| 14 | **26.2H 의견변동** ({prev}→{curr}) | 자동, 빈칸 | new |
| 15 | 그룹사 | 수기 | 직전 보존 |
| 16 | 26.1H 심사역 최종 판단 (전기 보존) | 보존 (분모용) | 직전 Col 17 시프트 |
| 17 | **26.2H 심사역 최종 판단 (당기)** | 수기, 빈칸 | new (검수 시 채움) |

### 7.5.4 반기 표기 추상화 — `period_config.json`

**위치**: `_workspace/period_config.json` (단일 진실의 원천)

```json
{
  "current": "26.2H",
  "previous": "26.1H",
  "previous_previous": "25.2H",
  "history": ["25.2H", "26.1H", "26.2H"],
  "frozen_at": {
    "25.2H": "2026-04-25T10:00:00Z",
    "26.1H": "2026-10-31T17:00:00Z"
  }
}
```

**영향 받는 모듈 (모두 이 파일에서 동적 로드로 변경)**:
- `comment_generator/prompt_template.py` — "26.1H 검토 코멘트" → "{current} 검토 코멘트"
- `comment_generator/prompt_template_judgment.py` — Stage 2 분모 산정 시 "25.2H 유니버스" → "{previous} 유니버스"
- `comment_generator/extract_existing_universe.py` — 직전 분류 추출 컬럼명을 동적
- `.claude/skills/excel-merge/` — 머지 키 자동 컬럼·보존 컬럼 인덱스 매핑을 동적
- 웹 매트릭스 헤더 라벨 — `period_config`에서 읽어 표시
- 종목 대시보드 비교 카드 — `current ↔ previous` 라벨

### 7.5.5 백업/스냅샷 체계 (3-tier)

```
_workspace/
├── period_config.json
├── master/, dart/, nice/, news/, comments/, judgment/    ← 당기 작업 영역
└── snapshots/
    ├── 25.2H/         (전전기, read-only)
    │   ├── master.json
    │   ├── comments/
    │   ├── judgment/stage2_review.json
    │   ├── nice/, dart/, news/  (선택, 용량 부담 시 메타만)
    │   └── universe.xlsx
    ├── 26.1H/         (전기, read-only)
    └── _archive/      (전전전기 이상, 압축 .tar.gz)
```

**보존 정책**:
- **당기**: `_workspace/` 본체에서 작업 중. 빌드 시작 전 mtime 백업.
- **전기, 전전기**: `snapshots/{half}/` 에 read-only로 동결. 분석가 종목 대시보드의 "전기 비교 카드"가 여기서 읽음.
- **전전전기 이상**: `snapshots/_archive/{half}.tar.gz` 압축 보관. 일상 조회 대상 아님.
- **freeze 액션**: 롤오버 스킬 내부에서 자동 실행. 검수 진행 중에 freeze 되면 검수율 경고.

### 7.5.6 사용자 발화 → 시스템 응답 예시

```
사용자: "26.2H 작업을 위한 엑셀 만들어줘"

시스템(half-rollover 스킬):
  ✓ period_config 갱신: 26.1H(current) → 26.2H(current), 26.1H(previous), 25.2H(previous_previous)
  ✓ _workspace/* → _workspace/snapshots/26.1H/ 로 freeze (1,012개 파일)
  ✓ snapshots/_archive/ 정리 (전전전기 이상 압축, 해당 없음)
  ✓ output/26.2H 유니버스.xlsx 생성 (999행, 17컬럼, 자동 컬럼 비어있음)
  ✓ 매핑: 7→5(등급), 8→6(전망), 10→9(유니버스), 13→12(코멘트), 17→16(전기 심사역 보존), 11→11(담당 carry forward)
  ✓ Drop: 5/6/9/12(전전기), 14(의견변동 재산출), 16(직전 AI 판단)
  ✓ 마이그레이션 보고서: output/rollover_report.txt
  
  → 신규 종목을 output/26.2H 유니버스.xlsx 에 행 추가하신 뒤,
    "26.2H 유니버스 빌드 실행"을 요청해 주세요.
```

---

## 8. PoC 확정 사양 요약

대화에서 확정된 사항을 한 곳에 정리.

| 항목 | 확정안 |
|---|---|
| 사용 범위 | PoC, 단일 계정 (id `risk` / pw `1962`) |
| 개발 경로 | Next.js + FastAPI 정식 (Streamlit 스킵) |
| 편집 정책 | UI는 읽기 전용. 수기 컬럼(그룹사/담당/25.2H 등)은 **엑셀에서만 편집** |
| 사용자 쓰기 액션 | 종목 대시보드에서 **유니버스 분류 확정 = 검수완료** 토글 1종 → 엑셀 Col 17 갱신 |
| AI 판단 흐름 | **2-stage 자동**: Stage 1 종목별(comment-writer) → Stage 2 풀 검수(judgment-reviewer, R1~R6 + ≤10% 가드레일) → 엑셀 Col 16 |
| 매트릭스 판단 컬럼 | Col 9 "26.1H 유니버스(AI 판단)" + Col 9b "심사역 최종 판단" + Col 18 "검수여부" |
| 매트릭스 검수 컬럼 | 18번에 **검수여부**(검수완료/미검수) 칩 노출 |
| 검수 진행 KPI | 4번 KPI 카드 = "검수완료 N / 미검수 N + 진행률" |
| 스냅샷 비교 | **2-스냅샷** (25.2H ↔ 26.1H) — 누적 시계열 미사용 |
| 평가사 처리 | 매트릭스는 **유효신용등급 단일 컬럼**, 종목 대시보드에서 출처 신평사명 표기 |
| 인라인 재무지표 | 컬럼 토글, default **off** |
| 수집상태/캐시/토큰 | UI 미노출 (운영 메타 분리) |
| 재빌드/신규 종목 추가 | UI 미노출, cron/CLI에서 수행 |
| 엑셀 컬럼 수 | **17컬럼** (Col 16 "AI 판단" 자동 + Col 17 "심사역 최종 판단" 수기 보존) |
| 신규 산출물 경로 | `_workspace/judgment/stage2_review.json` (Stage 2 출력) |
| 신규 에이전트/스킬 | `judgment-reviewer` 에이전트 + `judgment-review` 스킬 |
| 반기 전환 | A안 + 신규 스킬 `half-rollover` (에이전트 추가 없음). 결정론적 시프트 + freeze 자동화 |
| 반기 표기 추상화 | `_workspace/period_config.json` 단일 진실의 원천. 모든 모듈 동적 로드 |
| 백업 체계 | 3-tier (`_workspace/snapshots/{전기, 전전기}/` read-only + `_archive/` 압축) |
| 디자인 가이드 | `AgenticCreditUniverse/AgenticCreditUniverse/AgenticCreditUniverse/web/DESIGN-GUIDE.md` **v4** (시각/인터랙션 단일 출처, plan v6과 정합 완료) |
| 종목 상세 구조 | 단일 세로 스크롤 + 우측 floating TOC (5탭 구조 폐기) |

---

## 9. 디자인 가이드 갱신 결과 (2026-04-26 처리 완료, v3 → v4)

`web/DESIGN-GUIDE.md`에 다음 변경 직접 반영 완료. 가이드 위치는 현재 그대로 유지(`AgenticCreditUniverse/AgenticCreditUniverse/AgenticCreditUniverse/web/DESIGN-GUIDE.md`) — 모듈 폴더와 동급에 위치해 백엔드 import에 자연스럽기 때문.

| # | 적용 내역 | 상태 |
|---|---|---|
| 9.1 | §4.5 매트릭스 헤더에서 `Edit Toggle`·`Refresh` 제거, KPI 4번 "수집률" → "검수 진행 현황" | ✅ |
| 9.2 | §4.5 Sidebar Bulk Action 범위 "엑셀 export 전용"으로 축소 | ✅ |
| 9.3 | §4.6 종목 상세 §4 "심사역 코멘트(편집 모드)" → "AI 코멘트(읽기 전용)" + 검수 액션 패널 명시 | ✅ |
| 9.4 | §4.6 §7 "변경 이력 / 백업" → "반기 히스토리(스냅샷 시계열)" | ✅ |
| 9.5 | §4.6 §3 "신평사 의견서 타임라인" → "신평사 의견 (PDF 임베드 + 등급변동 타임라인 §11.3)" | ✅ |
| 9.6 | **신규 §16 로그인 페이지 명세** 추가 (단일 계정 PoC, 카드 레이아웃, 컴포넌트 매핑, 인터랙션) | ✅ |
| 9.7 | §6.4 PipelineProgress / §6.5 JobBadge: 분석가 화면 사용 금지 메모 추가 | ✅ |
| 9.8 | §8 자동/수동 시각 구분: PoC 인라인 편집 미사용 + "수기 데이터는 엑셀에서만 편집" 메모 추가 | ✅ |
| 추가 | 가이드 파일 헤더에 v4 변경 노트 + plan 참조 명시 | ✅ |

---

## (참고) 9_legacy. 처리 전 기록 — plan 우선 결정 사항

위 9 섹션이 적용되기 전, 두 문서 충돌을 정리한 원본 기록:

### 9.1 §4.5 매트릭스 표준 레이아웃 — 헤더와 KPI Bar 정정

**기존**:
```
[Logo] [GlobalSearch] [Edit Toggle] [Refresh] [Export]
KPI: [발행자수] [등급분포] [전망변동] [수집률]
```

**plan 우선 변경**:
```
[Logo] [GlobalSearch] [Export] [User: risk] [Logout]
KPI: [전체 종목 수] [등급 분포] [의견 변동(▲▼-)] [검수 진행 현황]
```

이유: PoC는 읽기 전용 + 운영 메타 미노출. Edit Toggle·Refresh 버튼은 정책 위반. 4번 KPI는 분석가 워크플로우 가시화에 검수 진행률이 더 적절.

### 9.2 §4.5 Sidebar — Bulk Action 범위 축소

**기존**: 체크박스 + (암묵적) Bulk Action — 코멘트 재생성/News 재수집 등 작업 트리거 함의

**plan 우선 변경**: 체크박스는 유지, Bulk Action은 **"선택 행 엑셀 export"만**. 작업 트리거(코멘트 재생성, News 재수집 등)는 UI 미노출.

### 9.3 §4.6 종목 상세 §4 — "심사역 코멘트 (편집 모드 시 활성)" 제거

**plan 우선 변경**: 편집 모드 자체가 PoC에 없음. §4를 "AI 코멘트(당기/전기 비교)"로 재정의. 분석가의 추가 메모는 우측 검수 패널의 "확정 코멘트(선택)" 필드로 이동.

### 9.4 §4.6 종목 상세 §7 — "변경 이력 / 백업" 톤다운

**plan 우선 변경**: "백업"이라는 운영성 단어 제거. **"반기 히스토리"**로 라벨 변경. 내용은 `_workspace/snapshots/`에서 분석가용 시계열 비교 (등급·유니버스·심사역 판단 변천).

### 9.5 §1 디자인 원칙 — 인쇄/PDF 친화 보강

**plan 우선 보강**: 단일 세로 스크롤 원칙은 plan v6 종목 상세 §7섹션 구조와 일치. 가이드의 §4.6 ASCII 다이어그램에 "§ 3 신평사 의견 — PDF 임베드 + 등급 변동 타임라인" 명시 추가.

### 9.6 신규 §16 — 로그인 페이지 명세 추가 필요

가이드에 누락된 영역. 추가할 내용:
- 라우트: `/login`
- 단일 계정: id `risk` / pw `1962`
- 레이아웃: 중앙 정렬, max-w-md 카드, 로고 + 입력 2개 + Primary 버튼
- 시각: 가이드 §6.6의 shadcn `Card`, `Input`, `Button` 사용
- 미인증 접근은 모두 `/login`으로 리다이렉트
- 헤더 §4.2와 일관된 톤 (sticky·border-b)

### 9.7 §6.4 PipelineProgress / §6.5 JobBadge — 사용 위치 제한 메모

**plan 우선 보강**: 컴포넌트 정의는 유지하되 **분석가 화면(매트릭스/종목 상세)에는 사용 금지** 메모 추가. 향후 운영자용 별도 화면(예: `/admin/jobs`)에서만 사용.

### 9.8 §8 자동/수동 시각 구분 — 인라인 편집 제거 확인

**plan 우선 변경**: §8의 "수동 입력 컬럼 = bg-background (기본)"는 시각 구분 의도만. PoC에서는 **인라인 편집 미사용**, 모든 컬럼이 사실상 읽기 전용. "수기 데이터는 엑셀에서만 편집" 한 줄 추가 권장.

---

> 위 항목은 plan mode 종료 후 `DESIGN-GUIDE.md`에 직접 반영 예정. 사용자 추가 의견에 따라 9.1~9.8 중 일부는 가이드 그대로 유지하고 plan을 양보하는 선택도 가능.
