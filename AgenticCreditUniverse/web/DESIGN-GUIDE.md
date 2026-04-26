# 디자인 시스템 가이드 v4

> 본 문서는 Claude Code가 본 프로젝트의 화면을 일관되게 구현하기 위한 단일 디자인 명세입니다.
> 라우팅·데이터·기능 구조는 별도 문서(`enumerated-questing-summit.md` plan v6)를 따르고, **본 문서는 시각/인터랙션만 다룹니다.**

> **v4.1 변경 (2026-04-26)** — 6개 UX 개선 + 단기등급 매핑 + 분포차트 8 버킷:
> - §2.3 신용등급 시맨틱 컬러: 6 버킷 → **8 버킷 그라데이션** (AA-↑ / A+ / A0 / A- / BBB+ / BBB0 / BBB- / BB+↓), 토큰 `--rating-tier-1`~`-8`. **단기등급(A1 / A2± / A3±)도 동일 hue 라인에 매핑**(예: A2+ ≡ A+ tier-2). 옛 토큰은 호환 별칭.
> - §4.6 종목 상세 우측 컬럼: TOC 단독(180px) → **검수 액션 패널 + TOC 단일 sticky 사이드바(320px)**. 페이지 스크롤 무관하게 검수 액션이 항상 노출.
> - §4.5 매트릭스 KPI Bar "등급 분포" 차트: 3 버킷(high/mid/low) → **8 버킷 + NR**. 카운트 0 버킷은 범례 자동 생략.
> - §4.6 §1 개요: 전기·당기 카드 사이에 `RatingDeltaIcon` (before → after 시각화).
> - §4.6 §6 DART: `<details open>` 기본 펼침 + Tabs 제거 → 사업의 내용 → 연결 주석 세로 스택. 메타는 공시일자만 노출.
> - DART 본문: 토픽 마커(`[…]`) 기반 단락 분기 (백엔드 `_dart_xml_to_html` 후처리). 한 단락에 여러 주제가 들어있던 원공시를 분석가가 읽기 좋게 분해.
> - §4.6 §3 신평사 의견: 임베드 PDF + 메타 (평가사명 / 공시일 / 유효기간 / 채권 정보) + 다운로드 버튼. PDF는 `Content-Disposition: inline` 으로 서버에서 임베드 가능하게 반환.
> - §4.6 §5 뉴스/리스크: 인용은 1년 이내 자료만 (백엔드 `_news_for` 가 `last_updated`/`date` 필드로 자동 필터링). 인용 항목에 발행일 표기. 신규 수집 시 Perplexity API 측 `search_recency_filter: "year"` / `search_after_date_filter` 도 함께 적용.
> - §6.1.1 신규 `RatingDeltaIcon` 컴포넌트 명세.
> - §9.1 `ratingBucket()` 단일 출처화.
> - 매트릭스 `curr_grade` 셀 내부 `RatingDeltaIcon` 인라인 표기 (§4.5 별도 컬럼 신설 없이).
> - 종목 상세 백 링크 카피: "매트릭스로" → "← 전체 목록".

> **v4 변경 (2026-04-26)** — plan v6과의 충돌을 plan 우선으로 정합:
> - §4.5 매트릭스 헤더에서 `Edit Toggle`·`Refresh` 제거, KPI Bar의 "수집률" → "검수 진행 현황"
> - §4.5 Sidebar Bulk Action 범위를 "엑셀 export 전용"으로 축소
> - §4.6 종목 상세 §4 "심사역 코멘트(편집 모드)" → "AI 코멘트(읽기 전용)"
> - §4.6 §7 "변경 이력 / 백업" → "반기 히스토리(스냅샷 시계열)"
> - §4.6 §3 "신평사 의견서 타임라인" → "신평사 의견 (PDF + 등급변동 타임라인)"
> - §6.4 PipelineProgress / §6.5 JobBadge: 분석가 화면(매트릭스/종목 상세) 사용 금지 메모 추가
> - §8 자동/수동 시각 구분: PoC 인라인 편집 미사용 메모 추가
> - **§16 신규** 로그인 페이지 명세 추가 (단일 계정 PoC)

---

## 0. 기술 스택 (디자인 관련 한정)

| 영역 | 도구 | 비고 |
|---|---|---|
| 프레임워크 | **Next.js (App Router)** | TypeScript |
| 스타일링 | **Tailwind CSS v4** | `@theme inline` 사용 |
| 컴포넌트 | **shadcn/ui** | 모든 프리미티브의 단일 출처 |
| 아이콘 | **lucide-react** | 단일 라이브러리 |
| 차트 | **Recharts** | shadcn `chart` 래퍼와 호환 |
| 테이블 | **TanStack Table v8** + **TanStack Virtual v3** | 200행 이상 영역에 적용 |
| 폰트 | **Pretendard** + **Geist Mono** | `next/font/local`로 셀프호스팅 |
| 모션 | **tailwindcss-animate** (기본) + **framer-motion** (시그니처 한정) | 절제 원칙 유지 |
| 색상 | **oklch** + `color-mix(in oklab)` | hex/rgb 직접 작성 금지 |

---

## 1. 디자인 원칙

- **톤**: 클린 라이트 엔터프라이즈. Notion / Linear / Vercel 계열의 절제된 라이트 테마.
- **테마**: 단일 라이트 테마 (다크 토큰은 정의하되 비활성).
- **정보 밀도**: 신용 심사 워크벤치 특성상 표·KPI·차트 중심. 패딩보다 정렬과 가독성 우선.
- **숫자 가독성**: 모든 수치 영역에 `tabular-nums` 적용 (자릿수 정렬).
- **색상 사용 원칙**:
  - 액션 강조는 `--primary` 1색만 사용
  - 의미 색상(등급, 전망, 델타)은 시맨틱 토큰 함수로만 매핑 (직접 hex/rgb 금지)
  - 톤다운된 표현은 `color-mix(in oklab, <token> 14%, transparent)` 패턴 사용
- **모션**: 기본은 `transition-colors`만. **시그니처 모션은 §11에서 정의된 위치에만** 적용.
- **인쇄/PDF 친화**: 종목 상세 등 보고서성 페이지는 단일 세로 스크롤 우선. 탭 분할 지양.

---

## 2. 컬러 토큰

모든 색상은 **oklch** 포맷. Tailwind 매핑은 `@theme inline { --color-<n>: var(--<n>); }` 으로 자동 노출되어 `bg-<n>`, `text-<n>`, `border-<n>` 으로 사용.

### 2.1 베이스 (라이트)

| 토큰 | 값 | Tailwind | 용도 |
|---|---|---|---|
| `--background` | `oklch(0.992 0.002 250)` | `bg-background` | 페이지 베이스 |
| `--foreground` | `oklch(0.20 0.02 260)` | `text-foreground` | 본문 텍스트 |
| `--card` | `oklch(1 0 0)` | `bg-card` | 카드/패널 |
| `--card-foreground` | `oklch(0.20 0.02 260)` | `text-card-foreground` | 카드 본문 |
| `--popover` | `oklch(1 0 0)` | `bg-popover` | 드롭다운/툴팁 배경 |
| `--popover-foreground` | `oklch(0.20 0.02 260)` | `text-popover-foreground` | 팝오버 본문 |
| `--primary` | `oklch(0.50 0.16 260)` | `bg-primary` | 액션 / 링크 / 로고 (인디고) |
| `--primary-foreground` | `oklch(0.99 0.002 250)` | `text-primary-foreground` | primary 위 텍스트 |
| `--secondary` | `oklch(0.965 0.008 250)` | `bg-secondary` | 보조 패널 |
| `--secondary-foreground` | `oklch(0.25 0.03 260)` | `text-secondary-foreground` | 보조 텍스트 |
| `--muted` | `oklch(0.965 0.008 250)` | `bg-muted` | 비강조 영역, 자동 수집 컬럼 |
| `--muted-foreground` | `oklch(0.50 0.02 260)` | `text-muted-foreground` | 라벨/메타 텍스트 |
| `--accent` | `oklch(0.955 0.015 255)` | `bg-accent` | 호버/활성 상태 배경 |
| `--accent-foreground` | `oklch(0.30 0.10 260)` | `text-accent-foreground` | 호버/활성 텍스트 |
| `--destructive` | `oklch(0.55 0.20 25)` | `bg-destructive` | 위험/삭제 액션 |
| `--destructive-foreground` | `oklch(0.984 0.003 247.858)` | `text-destructive-foreground` | destructive 위 텍스트 |
| `--border` | `oklch(0.92 0.008 255)` | `border-border` | 외곽선 |
| `--input` | `oklch(0.92 0.008 255)` | `border-input` | 인풋 외곽선 |
| `--ring` | `oklch(0.50 0.16 260)` | `ring-ring` | 포커스 링 (= primary) |

### 2.2 차트 팔레트

| 토큰 | 값 | 용도 |
|---|---|---|
| `--chart-1` | `oklch(0.55 0.16 260)` | 1차 시리즈 (인디고) |
| `--chart-2` | `oklch(0.65 0.14 180)` | 2차 (틸) |
| `--chart-3` | `oklch(0.70 0.16 80)` | 3차 (앰버) |
| `--chart-4` | `oklch(0.60 0.18 25)` | 4차 (코랄) |
| `--chart-5` | `oklch(0.55 0.14 310)` | 5차 (퍼플) |

다중 카테고리 차트(예: 업종 도넛)는 `chart-1 ~ chart-5` 다음에 `--rating-bbb`, `--rating-aa`, `--watch-negative` 까지 8색 순환.

### 2.3 신용등급 시맨틱 컬러

`lib/credit.ts` 의 `ratingColorVar()` / `ratingBucket()` 가 등급 문자열 → 8 버킷 → CSS 변수로 매핑. **그린 160° → 레드 25° 그라데이션**. 한국 단기등급(A1/A2±/A3±)도 동일 hue 라인에 매핑.

| 토큰 | 값 | 장기등급 | 단기등급 | 의미 |
|---|---|---|---|---|
| `--rating-tier-1` | `oklch(0.55 0.13 160)` | `AAA`, `AA+`, `AA`, `AA-` | `A1`, `A1+` | 최우량~우량 (그린) |
| `--rating-tier-2` | `oklch(0.60 0.14 140)` | `A+` | `A2+` | 양호 상단 |
| `--rating-tier-3` | `oklch(0.65 0.15 115)` | `A`, `A0` | `A2`, `A20` | 양호 |
| `--rating-tier-4` | `oklch(0.68 0.16  90)` | `A-` | `A2-` | 양호 하단 (옐로우그린) |
| `--rating-tier-5` | `oklch(0.70 0.17  70)` | `BBB+` | `A3+` | 투자등급 하단 진입 (앰버) |
| `--rating-tier-6` | `oklch(0.65 0.18  50)` | `BBB`, `BBB0` | `A3`, `A30` | 투자등급 하단 (오렌지) |
| `--rating-tier-7` | `oklch(0.60 0.19  35)` | `BBB-` | `A3-` | 투자등급 경계 (오렌지레드) |
| `--rating-tier-8` | `oklch(0.55 0.20  25)` | `BB+`~`D` (BB+, BB, BB-, B+, B, B-, CCC, CC, C, D) | `B`, `C`, `D` | 투기등급 이하 (레드) |

**핵심 의도**: AA-까지는 단일 그린 묶음. 그 아래로는 등급 한 칸마다 색이 바뀌어 A+/A/A-/BBB+/BBB/BBB- 경계가 시각적으로 구분된다. **BB+ 이하는 모두 동일 레드** — 분석가 관점에서 투기등급 진입 자체가 이미 단일한 위험 신호이므로 더 잘게 쪼개지 않는다.

**호환 별칭** (`globals.css` 정의): `--rating-aaa`/`--rating-aa` → tier-1, `--rating-a` → tier-3, `--rating-bbb` → tier-5, `--rating-bb`/`--rating-b` → tier-8. KpiBar 도넛(high/mid/low)과 universe-chip의 △ 칩이 별칭을 통해 자연스럽게 새 팔레트로 합류.

`ratingTier()` 는 위를 다시 3구간으로 묶음 (필터/도넛 그루핑 용도, 색상은 위 8 버킷 우선):
- `high` = AAA~A
- `mid` = BBB
- `low` = BB 이하

`isInvestmentGrade(r)` = `tier !== "low"`

### 2.4 Watch (전망) 시맨틱

| 토큰 | 값 | 의미 | 라벨 |
|---|---|---|---|
| `--watch-positive` | `oklch(0.55 0.14 160)` | 긍정적 전망 | "긍정적" |
| `--watch-stable` | `oklch(0.55 0.02 260)` | 안정적 전망 | "안정적" |
| `--watch-negative` | `oklch(0.55 0.20 25)` | 부정적 전망 | "부정적" |

KPI 카드의 델타 색상도 동일 토큰 사용:
- 양수 → `--watch-positive`
- 음수 → `--watch-negative`
- 0 → `--muted-foreground`

### 2.5 파이프라인 / Job 상태

자동 수집 파이프라인 진행 표시 및 Job 배지에 사용.

| 토큰 | 값 | 의미 | 라벨 |
|---|---|---|---|
| `--state-pending` | `oklch(0.65 0.02 260)` | 대기 | "대기" |
| `--state-running` | `oklch(0.55 0.16 260)` (= primary) | 실행 중 | "수집 중" / "분석 중" |
| `--state-success` | `oklch(0.55 0.13 160)` (= rating-aaa) | 완료 | "완료" |
| `--state-failed` | `oklch(0.55 0.20 25)` (= destructive) | 실패 | "실패" |

`running` 상태에는 `animate-pulse` 적용 (시그니처 모션 §11.2 참조).

### 2.6 서피스 & 그림자

| 토큰 | 값 | 용도 |
|---|---|---|
| `--surface-subtle` | `oklch(0.978 0.004 250)` | 푸터, 자동 수집 컬럼 등 미세 톤다운 |
| `--shadow-card` | `0 1px 2px 0 oklch(0.20 0.02 260 / 0.04), 0 1px 3px 0 oklch(0.20 0.02 260 / 0.06)` | 일반 카드 |
| `--shadow-elevated` | `0 4px 12px -2px oklch(0.20 0.02 260 / 0.08), 0 2px 4px -1px oklch(0.20 0.02 260 / 0.04)` | 모달, 드롭다운, floating TOC |

### 2.7 색상 합성 패턴 (배지·델타)

톤다운된 시맨틱 표현은 항상 `color-mix(in oklab, <color>, transparent)` 패턴.

```ts
backgroundColor: `color-mix(in oklab, ${color} 14%, transparent)`,
border:           `1px solid color-mix(in oklab, ${color} 28%, transparent)`,
color:            color,
```

**고정 비율**: 배경 14%, 보더 28%, 텍스트 100%. 새 시맨틱 배지를 만들 때도 이 비율 유지.

---

## 3. 타이포그래피

### 3.1 폰트 패밀리

```css
--font-sans: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
--font-mono: 'Geist Mono', ui-monospace, SFMono-Regular, monospace;
```

- **Pretendard**: `next/font/local` 로 셀프호스팅. `font-display: swap` 적용. 한글 가독성 + 숫자 정렬 양쪽 모두 시스템 폰트 대비 우수.
- **Geist Mono**: 코드 블록, 식별자(티커) 등 모노스페이스가 필요한 곳에만 사용.

### 3.2 폰트 피처

```css
body {
  font-feature-settings: "cv11", "ss01";
  -webkit-font-smoothing: antialiased;
}
.tabular-nums { font-variant-numeric: tabular-nums; }
```

`tabular-nums` 는 모든 KPI 값, 등급 배지, 테이블 수치, 차트 라벨에 적용.

### 3.3 사이즈 스케일

| 용도 | Tailwind 클래스 | 비고 |
|---|---|---|
| 랜딩 hero h1 | `text-4xl sm:text-5xl font-semibold tracking-tight` | 줄바꿈 허용 |
| 페이지 h1 | `text-2xl font-semibold tracking-tight` | 매트릭스, 종목 상세 헤더 |
| 섹션 h2 | `text-lg font-semibold` | 섹션 구분 |
| 카드 제목 | `text-base font-medium` 또는 `text-sm font-semibold` | 컨텍스트에 따라 |
| KPI 값 | `text-2xl font-semibold tracking-tight tabular-nums` | KpiCard |
| 본문 | `text-sm` | 기본 |
| 라벨/메타 | `text-xs text-muted-foreground` | 보조 정보 |
| 캡션 | `text-[11px]` | 차트 축, 미세 보조 |
| 차트 축/범례 | `fontSize: 11~12` (Recharts inline) | |

### 3.4 굵기

400 (기본) / 500 (`font-medium`, 라벨) / 600 (`font-semibold`, 제목·KPI) **만 사용**. `font-bold` (700) 금지 — 라이트 톤 일관성 유지.

### 3.5 자간

- 큰 제목 (h1): `tracking-tight` 적용
- 본문/라벨: 기본 자간

---

## 4. 레이아웃 & 스페이싱

### 4.1 컨테이너

- 표준: `mx-auto max-w-7xl px-6` (모든 페이지 main)
- 페이지 세로 패딩: 랜딩 `py-16`, 일반 페이지 `py-8`
- 매트릭스(테이블 중심) 페이지는 컨테이너 없이 풀폭 사용 가능

### 4.2 헤더 / 푸터

- **헤더**: `sticky top-0 z-40 border-b bg-background/85 backdrop-blur`, 높이 `h-14`, 내부 gap `gap-6`
- **푸터**: `mt-16 border-t bg-[var(--surface-subtle)]`, 텍스트 `text-xs text-muted-foreground`

### 4.3 카드

- 표준 카드: `rounded-lg border bg-card p-4` + 인라인 `style={{ boxShadow: "var(--shadow-card)" }}`
- shadcn `Card` 사용 시 기본 `rounded-xl border bg-card text-card-foreground shadow` 유지
- 카드 간 간격: `gap-3` ~ `gap-6` (밀도에 따라)

### 4.4 라운드 스케일 (`--radius: 0.625rem`)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--radius-sm` | ≈ 6px | 작은 배지 |
| `--radius-md` | ≈ 8px | 버튼, 인풋 |
| `--radius-lg` | 10px | 일반 카드 |
| `--radius-xl` | ≈ 14px | shadcn Card |
| `rounded-full` | — | 전망(Watch) 배지 (pill) |

### 4.5 매트릭스 화면 표준 레이아웃

```
┌──────────────────────────────────────────────────────────┐
│ Header (h-14, sticky top-0, z-40)                        │
│ [Logo] [GlobalSearch] [Export] [User: risk] [Logout]     │
├──────────────────────────────────────────────────────────┤
│ KPI Bar (sticky top-14)                                  │
│ [{current} 검토 + O/△/X] [부정적 전망] [의견변동] [검수] │
├──────────────────────────────────────────────────────────┤
│ Distribution Row (lg:grid-cols-2)                        │
│ [유효신용등급 분포 BarChart] [업종 분포 Donut + 범례]    │
├──────────┬───────────────────────────────────────────────┤
│ Sidebar  │ Table Area                                    │
│ (w-72)   │ - Bulk Action Bar (선택 시 등장 — 엑셀 export │
│ 필터     │   전용. 작업 트리거는 UI 미노출)              │
│ 검색     │ - TanStack Virtualized Table (1,000행)        │
│ 체크박스 │   - Sticky 1st Column (종목명)                │
│          │   - Sortable Headers                          │
│          │   - Row Click → 종목 상세로 navigate          │
└──────────┴───────────────────────────────────────────────┘
```

**KPI 카드 구성 (plan v7 정합)**:
1. **{current} 검토** — 큰 숫자 + 가로 인라인 카운트 `O 가능 N · △ 조건부 N · X 미편입 N`
2. **부정적 전망** — `negative` 카운트 + "X.X% (N/total)"
3. **의견 변동** — ▲N(green) / ▼N(red) / -N(muted) 가로 정렬
4. **검수 진행 현황** — 검수완료 N / 전체 N + 진행률 바

**분포 차트 행 (KPI 바로 아래)**:
- 좌: `RatingDistChart` — 당기 유효등급 BarChart (AAA/AA/A/BBB/BB/B↓), 막대 색상 = `ratingColorVar()` (§2.3 시맨틱)
- 우: `IndustryDistChart` — 업종 도넛 PieChart, 8색 순환 (`var(--chart-1..8)`, §7.2 패턴), 우측에 라벨·카운트 범례

**매트릭스 컬럼 v7 추가**: "업종" 우측에 **유의업종** 칩 컬럼 — `industry_2026 === 'O'` 일 때 ○ (color: `--watch-negative`, 14% bg). 자동 판정 SSOT는 `_workspace/master/watch_industries.json` (사용자 운영, 매 반기 갱신).

**헤더 액션 (plan v6 정합)**:
- ❌ `Edit Toggle` 없음 — 매트릭스/대시보드 모든 컬럼 읽기 전용 (수기 데이터 편집은 엑셀에서만)
- ❌ `Refresh` 없음 — 빌드/재수집 트리거는 UI 미노출 (CLI/cron으로만)
- ✅ `엑셀 다운로드` (outline) — 매트릭스 export
- ✅ 우측 끝: 사용자 표시 (`risk`) + 로그아웃

### 4.6 종목 상세 화면 표준 레이아웃

탭 분할 대신 **단일 세로 스크롤 본문 + 우측 sticky 사이드바**. 사이드바에는 검수 액션 패널과 목차(TOC)가 위→아래 순서로 함께 sticky. 인쇄/PDF 친화성 유지 (인쇄 시 사이드바는 숨겨도 본문이 단일 페이지 흐름).

```
┌──────────────────────────────────────────────┬───────────────┐
│ Back Link "← 전체 목록"                      │ ┌───────────┐ │
│ Header Card                                  │ │ 검수 액션 │ │
│ [종목명/티커/업종]                           │ │ [O/△/X]   │ │
│ [RatingBadge] [WatchBadge] [의견변동]        │ │ [AI 동의] │ │
├──────────────────────────────────────────────┤ │ [확정]    │ │
│ § 1. 개요  (전기 [→] 당기 등급 비교,         │ └───────────┘ │
│            AI 판단 Stage1/2)                 │ ┌───────────┐ │
│ § 2. 재무 추이 (NICE 7년 시계열, 4 차트)     │ │  목차     │ │
│ § 3. 신평사 의견 (PDF + 등급변동 타임라인)   │ │  개요     │ │
│ § 4. AI 코멘트 (당기/전기 비교, 읽기 전용)   │ │  재무     │ │
│ § 5. 관련 뉴스 그리드 + 인용 링크            │ │  의견     │ │
│ § 6. DART 공시 (default open)                │ │  …        │ │
│ § 7. 반기 히스토리 (스냅샷 시계열)           │ └───────────┘ │
└──────────────────────────────────────────────┴───────────────┘
   본문 (스크롤)                                  Sticky top-20
```

- 그리드: `grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 lg:items-start`. 우측 컬럼 폭은 **320px** (검수 액션 패널 가독성 기준).
- 우측 사이드바는 **단일 sticky 컨테이너**: `<aside className="hidden lg:block lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto space-y-6">` 안에 `<ReviewActionPanel />` + `<FloatingTOC />` 세로 스택. 뷰포트가 짧을 때는 사이드바가 자체 스크롤.
- 모바일(<lg): 사이드바 전체 숨김. PoC는 데스크톱 1280+ 워크벤치 가정.

> **§ 1 개요 (v4 변경)**: 전기·당기 등급 카드 사이에 `→` 아이콘 — 등급 상향 시 `ArrowUp` + `--watch-positive`, 하향 시 `ArrowDown` + `--watch-negative`, 동일 시 `ArrowRight` + muted. 시간 흐름의 시각화.
>
> **§ 4 AI 코멘트 (v4 변경)**: 편집 모드 제거. 분석가 추가 메모는 우측 검수 액션 패널의 "확정 코멘트(선택)" 필드로 이동. 본 영역은 항상 읽기 전용.
>
> **§ 6 DART 공시 (v4.1 변경)**: `<details open>` 으로 카드 자체는 진입 시 펼침. **Tabs 제거** — 사업의 내용 본문 아래로 연결 주석 본문이 이어서 노출(분석가가 두 본문을 동시 비교 가능). 메타 영역은 공시일자 + DART 원공시 링크만 유지(접수번호 제거).
>
> **§ 7 반기 히스토리 (v4 변경)**: 기존 "변경 이력 / 백업"의 운영성 톤을 제거. `_workspace/snapshots/{전기, 전전기}/`에서 분석가용 시계열을 조회 — 등급·유니버스·심사역 판단 변천 표.

- TOC는 `lg:` 이상에서만 표시. 모바일은 단일 컬럼.
- TOC 활성 항목은 `IntersectionObserver` 기반으로 스크롤 위치 따라 강조 (sticky 컨테이너 부모가 sticky를 제어 — TOC 자체는 일반 nav).
- TOC 스타일: `text-xs text-muted-foreground`, 활성은 `text-foreground border-l-2 border-primary pl-3`.

### 4.7 반응형 브레이크포인트

Tailwind 기본값 (`sm: 640`, `md: 768`, `lg: 1024`, `xl: 1280`).

주요 패턴:
- KPI 카드 그리드: `grid-cols-2 lg:grid-cols-4`
- 차트 영역: `grid-cols-1 lg:grid-cols-3` (좌측 분포 차트가 `lg:col-span-2`)
- 피처 카드: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
- 종목 상세 + TOC: `grid-cols-1 lg:grid-cols-[1fr_180px]`

기준은 **데스크톱 우선 (1280+ 워크벤치 가정)**, 모바일은 단일 컬럼 폴백.

### 4.8 z-index 레이어

- `z-40`: 헤더
- `z-30`: KPI Bar (헤더 아래 sticky)
- 모달/시트는 shadcn Dialog/Sheet 기본값 사용

---

## 5. 아이콘

- 라이브러리: **lucide-react** 단일 출처
- 표준 사이즈:
  - 메뉴/액션: `h-4 w-4`
  - 델타 화살표 (`ArrowUp`/`ArrowDown`/`Minus`): `h-3 w-3`
  - 인풋 내부 (검색): `h-3.5 w-3.5`
  - 피처 카드: `h-5 w-5`
  - 자동 수집 잠금 (`Lock`): `h-3 w-3` + `text-muted-foreground`
- 색상: `text-primary` (강조), `text-muted-foreground` (보조), 의미 색은 시맨틱 변수
- 자주 사용되는 아이콘: `Sparkles`(편집·AI), `Search`, `ArrowRight`, `ArrowUp/Down`, `Minus`, `BarChart3`, `FileText`, `MessageSquare`, `Newspaper`, `Lock`, `RefreshCw`, `Download`. **로고는 아이콘 없이 텍스트("Credit Universe")만 사용.**

---

## 6. 핵심 시각 컴포넌트 명세

라우팅·데이터 구조는 별도 문서 기준이지만, **시각 컴포넌트의 prop과 스타일은 본 문서 단일 출처.**

### 6.1 RatingBadge

| Prop | 타입 | 기본 | 설명 |
|---|---|---|---|
| `rating` | `Rating` (AAA…B) | — | 표시할 등급 |
| `size` | `"sm" \| "md" \| "lg"` | `"sm"` | 패딩/폰트 크기 |
| `className` | `string` | — | 추가 클래스 |

사이즈별 클래스:
- `sm`: `px-2 py-0.5 text-xs`
- `md`: `px-2.5 py-1 text-sm`
- `lg`: `px-4 py-1.5 text-lg`

색상은 §2.7 합성 패턴 (14% / 28% / 100%) + `ratingColorVar(rating)`.

### 6.1.1 RatingDeltaIcon

전기↔당기 신용 신호(등급 + 전망) 변동 인디케이터. 매트릭스 `curr_grade` 셀과 종목 상세 §1 개요의 당기 PeriodCard에서 사용. 색·아이콘 매핑은 §6.3 KpiCard 델타와 동일.

| Prop | 타입 | 기본 | 설명 |
|---|---|---|---|
| `prev` | `string?` | — | 전기 등급 |
| `curr` | `string?` | — | 당기 등급 |
| `prevWatch` | `string?` | — | 전기 전망 (등급 미상/유지 시 fallback) |
| `currWatch` | `string?` | — | 당기 전망 |
| `size` | `"sm" \| "lg"` | `"sm"` | 매트릭스 = sm (h-3 w-3), 개요 = lg (h-5 w-5) |

방향 결정 (등급 우선, 전망 fallback):
1. `compareRating(prev, curr)` 가 0이 아니면 그 부호로 결정
2. 등급이 같거나 미상이면 `compareWatch(prevWatch, currWatch)` (positive > stable > negative)로 결정 — 예: 부정적→안정적 = 상향
3. 둘 다 미상/유지 → `Minus` (유지) 또는 입력 자체가 모두 null이면 `null` 반환

색상:
- 상향: `var(--watch-positive)` + `ArrowUp`
- 하향: `var(--watch-negative)` + `ArrowDown`
- 유지: muted `Minus`

**배치 규칙**:
- 매트릭스 `curr_grade` 셀: `RatingBadge` → `WatchBadge` → `RatingDeltaIcon` 순. 등급/전망 모두 본 후 변동을 마지막에 표기.
- 종목 상세 §1 개요 **당기 카드 내부**: `WatchBadge` 우측에 인라인 (배치 규칙은 매트릭스와 동일). 전기 카드에는 표시하지 않음.
- 종목 상세 §1 개요 **카드 사이 영역**: 항상 정적 `ArrowRight` muted 색 (시간 흐름 신호 — 변동 강조는 당기 카드 안에서 처리).

### 6.2 WatchBadge

| Prop | 타입 | 기본 | 설명 |
|---|---|---|---|
| `watch` | `"positive" \| "stable" \| "negative"` | — | 전망 상태 |
| `size` | `"sm" \| "md"` | `"sm"` | 패딩/폰트 크기 |

스타일: `rounded-full px-2 py-0.5 text-xs` + 시맨틱 토큰 합성. pill 형태 유지.

### 6.3 KpiCard

| Prop | 타입 | 설명 |
|---|---|---|
| `label` | `string` | 상단 라벨 (`text-xs muted`) |
| `value` | `string \| number` | 큰 수치 (`text-2xl semibold tabular-nums`) |
| `unit` | `string?` | 단위 (값 우측, muted) |
| `delta` | `number?` | 양/음/0 → 색·아이콘 매핑 |
| `deltaLabel` | `string?` | 델타 우측 보조 텍스트 |
| `hint` | `string?` | delta 미사용 시 보조 설명 |

델타 매핑:
- `delta > 0` → `text-[color:var(--watch-positive)]` + `ArrowUp`
- `delta < 0` → `text-[color:var(--watch-negative)]` + `ArrowDown`
- `delta === 0` → `text-muted-foreground` + `Minus`

표기: `Math.abs(delta).toFixed(1)%`.
카드: `rounded-lg border bg-card p-4` + `--shadow-card`.

**※ 재무지표 컨텍스트(예: 부채비율 상승 = 악화)에서 시맨틱 반전이 필요하면, 호출 측에서 `delta` 부호를 미리 반전시켜 전달.**

### 6.4 PipelineProgress

자동 수집 파이프라인 4단계 진행 표시.

> **※ 사용 위치 제한 (v4)**: PoC 분석가 화면(매트릭스 / 종목 상세)에서는 **사용 금지**. 운영성 정보 미노출 정책. 향후 운영자 전용 화면(예: `/admin/jobs`) 한정.

```
[●대기] ── [●수집중] ── [○분석중] ── [○완료]
```

- 컨테이너: `flex items-center gap-2`
- 각 단계: 원형 인디케이터 + 라벨
- 활성 단계: `bg-primary text-primary-foreground` + `animate-pulse` (running일 때만)
- 완료 단계: `bg-[var(--state-success)] text-white`
- 미진입 단계: `bg-muted text-muted-foreground`
- 연결선: `h-px flex-1 bg-border`, 완료 구간은 `bg-primary`

### 6.5 JobBadge

> **※ 사용 위치 제한 (v4)**: PoC 분석가 화면에서는 **사용 금지**. PipelineProgress와 동일 사유.

| Prop | 타입 |
|---|---|
| `state` | `"pending" \| "running" \| "success" \| "failed"` |

- 라벨: 한글 매핑 (대기 / 실행중 / 완료 / 실패)
- 스타일: §2.7 합성 패턴 + `--state-*` 토큰
- `running` 상태에 `animate-pulse` 적용

### 6.6 활용할 shadcn/ui 프리미티브

`components/ui/` 에 포함되는 기본 컴포넌트:

| 컴포넌트 | 주요 사용처 |
|---|---|
| `Button` | CTA, 액션, 정렬 토글 |
| `Input` | 매트릭스 검색, 폼 |
| `Switch` | 헤더 편집 모드 |
| `Card` 계열 | 일반 섹션 컨테이너 |
| `Tabs` | (v4.1 이후 종목 상세에서 미사용) — DART 공시도 세로 스택으로 전환. 신규 사용 시 PLAN 문서와 정합 검토 |
| `Dialog` / `Sheet` | 모달, 사이드 패널 |
| `Select` | 정렬·필터 드롭다운 |
| `Tooltip` | 차트, 아이콘 보조 설명 |
| `Table` (raw) | 짧은 정적 테이블 |
| `Badge` | 일반 메타 정보 |
| `Checkbox` | Bulk 선택 |
| `Progress` | 수집률, 분석 진행 |
| `Skeleton` | 로딩 상태 |

---

## 7. 차트 시스템

라이브러리: **Recharts** (shadcn `chart` 래퍼와 호환).

### 7.1 공통 규칙

- 컨테이너: `<ResponsiveContainer width="100%" height="100%">`, 부모는 `h-56`/`h-72` 등 고정 높이
- 축: `tickLine={false} axisLine={false} fontSize={12}`
- 그리드: `<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />`
- 툴팁: `contentStyle={{ borderRadius: 8, border: "1px solid var(--border)", fontSize: 12, backgroundColor: "var(--popover)" }}`
- 색상은 항상 `var(--chart-N)` 또는 의미 토큰. **하드코딩 금지.**

### 7.2 표준 차트 패턴

| 차트 | 패턴 |
|---|---|
| 등급 분포 막대 | `Bar radius={[4,4,0,0]}` + `<Cell fill={ratingColorVar(rating)} />` |
| 업종 도넛 | `Pie innerRadius={40} outerRadius={70} paddingAngle={2}`, 8색 순환 |
| 재무 추이 라인 | 매출·영업이익 듀얼 라인. `chart-1` / `chart-2` |
| 부채비율·이자보상배율 듀얼축 | 좌축 `chart-1`, 우축 `chart-2`, 임계선 `<ReferenceLine stroke="var(--watch-negative)" strokeDasharray="4 4" />` |
| 등급 변동 타임라인 (시그니처) | §11.3 참조 |

---

## 8. 자동/수동 데이터 시각 구분

분석가가 "어디부터 시스템이 자동 수집했고, 어디부터 사람이 입력했는지" 즉시 인지할 수 있도록 시각 구분 필수.

| 구분 | 스타일 |
|---|---|
| 자동 수집 컬럼 (테이블) | `bg-muted/50` + 헤더에 `Lock` 아이콘 (`h-3 w-3 text-muted-foreground`) |
| 수동 입력 컬럼 (테이블) | `bg-background` (기본) + 헤더에 작은 `Pencil` 아이콘 (`h-3 w-3 text-muted-foreground`, 정보 표시용) |
| 자동 생성 텍스트 (코멘트 등) | 좌측 `border-l-2 border-primary pl-3` + 상단에 "AI 생성" 미니 라벨 (`text-[10px] text-primary font-medium uppercase tracking-wide`) |
| 사람 작성 텍스트 | 좌측 `border-l-2 border-border pl-3` |

> **PoC 편집 정책 (v4)**: 매트릭스/대시보드의 모든 컬럼은 **읽기 전용**. 위 시각 구분은 "데이터 출처"를 알리기 위한 목적이며, 인라인 편집 UI는 제공하지 않음. 수기 데이터(그룹사·담당·전기 보존 컬럼·심사역 최종 판단 등)는 **엑셀에서만 편집** → 다음 빌드 사이클에 반영. 단 하나의 예외: 종목 대시보드 우상단 검수 액션 패널의 "유니버스 분류 확정" 폼.

---

## 9. 상태 색상 매핑 가이드

### 9.1 신용등급 → 8 버킷

`ratingBucket()`이 단일 출처. 단기등급(A1/A2±/A3±)도 동일 라인에 매핑.

```ts
function ratingBucket(r: string): RatingBucket {
  const s = r.toUpperCase().trim();
  if (["AAA", "AA+", "AA", "AA-", "A1", "A1+"].includes(s)) return "tier-1";
  if (["A+", "A2+"].includes(s))                              return "tier-2";
  if (["A", "A0", "A2", "A20"].includes(s))                   return "tier-3";
  if (["A-", "A2-"].includes(s))                              return "tier-4";
  if (["BBB+", "A3+"].includes(s))                            return "tier-5";
  if (["BBB", "BBB0", "A3", "A30"].includes(s))               return "tier-6";
  if (["BBB-", "A3-"].includes(s))                            return "tier-7";
  return "tier-8"; // BB+ 이하 + B/C/D 단기 포함
}

function ratingColorVar(r: string): string {
  return `var(--rating-${ratingBucket(r)})`;
}
```

매트릭스 KPI Bar의 "등급 분포" 차트는 위 8 버킷 + NR (총 9 세그먼트)로 구성되며, 카운트가 0인 버킷은 범례에서 자동 생략된다.

### 9.2 등급 tier

| 반환값 | 매핑 | 용도 |
|---|---|---|
| `high` | A 이상 (AAA, AA*, A*) | 매트릭스 필터 "A 이상" |
| `mid` | BBB* | 매트릭스 필터 "BBB" |
| `low` | BB 이하 | 매트릭스 필터 "BB 이하" |

### 9.3 Watch / 델타 / Job 상태

§2.4, §2.5 참조.

---

## 10. 인터랙션 상태

### 10.1 링크/버튼 인터랙션

| 상태 | 스타일 |
|---|---|
| 링크 hover | `hover:bg-accent hover:text-foreground` |
| 활성 라우트 | `bg-accent text-accent-foreground` |
| Primary 버튼 hover | `hover:bg-primary/90` |
| Outline 버튼 hover | `hover:bg-accent` |
| 포커스 | `focus-visible:ring-1 focus-visible:ring-ring` |

### 10.2 테이블 행 인터랙션

| 상태 | 스타일 |
|---|---|
| 행 hover | `hover:bg-row-hover` + `cursor-pointer` (solid 토큰 — sticky 컬럼 뒤 콘텐츠 가려야 함) |
| 선택 (체크박스) | `bg-primary/5` + 좌측 `border-l-2 border-primary` |
| 정렬 활성 헤더 | 헤더 텍스트 옆에 `ArrowUp`/`ArrowDown` 아이콘 |

### 10.3 빈 상태 / 로딩 / 에러

**빈 상태 (Empty State)**
- 컨테이너: `py-12 text-center`
- 아이콘: 큰 아웃라인 (`h-10 w-10 text-muted-foreground/40`)
- 제목: `text-base font-medium`
- 설명: `text-sm text-muted-foreground mt-1`
- CTA: 옵션 (`Button variant="outline" size="sm"`)

**로딩**
- 데이터 영역: shadcn `Skeleton` 사용 (실제 콘텐츠와 동일한 형태/크기)
- 페이지 전환: 상단 progress bar (얇은 1px primary)
- 차트 로딩: 차트 영역 그대로 유지하고 중앙에 `Loader2 className="h-5 w-5 animate-spin text-muted-foreground"`

**에러**
- 컨테이너: `border border-destructive/30 bg-destructive/5 rounded-lg p-4`
- 아이콘: `AlertCircle h-4 w-4 text-destructive`
- 텍스트: `text-sm` (제목은 `font-medium text-destructive`)
- 재시도 버튼: `variant="outline" size="sm"`

---

## 11. 모션 (시그니처 한정)

엔터프라이즈 톤 유지를 위해 **기본은 `transition-colors`만**. 단, 대회 데모 임팩트를 위해 **아래 3개 위치에만** 시그니처 모션 허용.

### 11.1 KPI 카드 stagger fade-in (종목 상세 / 매트릭스 진입 시)

```tsx
import { motion } from "framer-motion";

<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.3, delay: index * 0.05, ease: "easeOut" }}
>
  <KpiCard ... />
</motion.div>
```

- 카드 6개 기준 총 시간: 약 580ms
- 페이지 첫 진입 시에만, 이후 데이터 갱신엔 미적용

### 11.2 파이프라인 running 상태 펄스

`animate-pulse` (Tailwind 기본) — 별도 라이브러리 불필요.
running 상태인 단계의 인디케이터에만 적용.

### 11.3 등급 변동 강조 (시그니처 차트)

종목 상세 §3 "신평사 의견서 타임라인"에서, 등급이 변동된 지점에 시각 강조:
- 마커: 더 큰 원 (반지름 6px), `stroke-width: 2`
- 색: 변동 방향에 따라 `--watch-positive` (상향) 또는 `--watch-negative` (하향)
- 진입 시 1회 한정 0.4s scale 애니메이션 (`scale: 0.7 → 1.0`)

이 외 위치에는 모션 적용 금지. 특히 호버 스케일/리프트, 페이지 전환 슬라이드 등은 사용하지 않음.

---

## 12. 접근성

- **대비**: 본문 `--foreground` (oklch 0.20) on `--background` (oklch 0.992) — WCAG AA 충족. 배지는 단색 텍스트 + 14% 배경으로 4.5:1 이상 유지.
- **포커스 가시성**: 모든 인터랙티브 요소에 `focus-visible:ring-1 focus-visible:ring-ring` 보존. 커스텀 링크에도 동일 적용.
- **aria-label**: 아이콘 단독 버튼, 토글, 모달에 명시.
- **시맨틱 HTML**: `header` / `main` / `footer` / `nav` / `section` 사용. 페이지당 단일 `h1`.
- **인쇄/PDF**: 종목 상세는 단일 세로 스크롤 — 브라우저 인쇄/PDF 저장 시 정보 누락 없음.
- **메타**: 각 라우트 메타 (title/description/og:*)를 페이지별로 분리.

---

## 13. 확장 규칙 — Do & Don't

### Do

- ✅ 신규 색상은 반드시 `app/globals.css` 의 `:root` + `@theme inline` 양쪽에 oklch 로 추가
- ✅ 의미 색이 필요한 경우(새 등급 구간, 새 상태 등) 시맨틱 토큰 신설 후 매핑 함수 갱신
- ✅ 카드 그림자는 `--shadow-card` / `--shadow-elevated` 둘 중 선택
- ✅ 수치는 항상 `tabular-nums` 와 함께 출력
- ✅ 새 페이지는 메타(title/description/og:*) 페이지별 분리
- ✅ 자동 수집 데이터는 §8 패턴으로 시각 구분
- ✅ 모든 인터랙티브 요소에 호버/포커스 상태 정의
- ✅ 빈 상태 / 로딩 / 에러 화면을 페이지마다 명시적으로 디자인

### Don't

- ❌ 컴포넌트에 hex / rgb / oklch 직접 작성 (예: `text-[#0070f3]`, `bg-[oklch(0.5...)]`)
- ❌ `font-bold` (700) 사용 — semibold (600)까지만
- ❌ 종목 상세 본체를 탭으로 분할 (인쇄 친화성 저하). v4.1 이후 부분 영역에서도 Tabs 미사용 (DART는 세로 스택으로 전환됨)
- ❌ 다크 모드 강제 적용 (현재 비활성. 활성화 전 `.dark` 토큰 검수 필요)
- ❌ 임의 그림자/라운드 추가 — 토큰 스케일 안에서 선택
- ❌ §11에 없는 위치에 모션 적용 (호버 스케일, 페이지 전환 슬라이드 등 금지)
- ❌ 차트 색을 시리즈마다 임의 지정 — 항상 `--chart-N` 또는 시맨틱 토큰 사용
- ❌ 한글 폰트로 시스템 폰트만 의존 — 반드시 Pretendard 셀프호스팅
- ❌ 한 페이지에 `h1` 두 개 이상

---

## 14. 디자인 토큰 디렉터리 (디자인 관련 파일만)

```
app/
├─ globals.css                # 모든 토큰 (oklch) + Tailwind theme 매핑 + Pretendard import
├─ layout.tsx                 # 폰트 로드, html/body 설정
└─ ...

components/
├─ rating-badge.tsx           # 등급 배지
├─ watch-badge.tsx            # 전망 배지
├─ kpi-card.tsx               # KPI 카드
├─ pipeline-progress.tsx      # 파이프라인 진행 표시
├─ job-badge.tsx              # Job 상태 배지
└─ ui/                        # shadcn/ui 프리미티브

lib/
├─ credit.ts                  # 등급 타입 / 색상 매핑 / tier / isInvestmentGrade / 포매팅
└─ utils.ts                   # cn() (clsx + tailwind-merge)
```

(라우팅·데이터 레이어는 별도 문서 기준)

---

## 15. 포매팅 유틸 (`lib/credit.ts`)

| 함수 | 시그니처 | 동작 |
|---|---|---|
| `formatBillionKRW(value)` | `(억원) → string` | 10000 이상 → `n.n조원`, 미만 → `1,234억원` |
| `formatPercent(value, digits=1)` | | `12.3%` |
| `formatMultiple(value, digits=1)` | | `4.2x` |
| `formatDelta(value, digits=1)` | | 부호 포함 `+1.2%` / `-0.8%` |
| `compareRating(a, b)` | | `RATING_ORDER` 인덱스 차 |
| `ratingTier(r)` | | `"high" \| "mid" \| "low"` |
| `isInvestmentGrade(r)` | | `tier !== "low"` |
| `ratingColorVar(r)` | | `var(--rating-*)` 문자열 |

`RATING_ORDER` 는 `AAA → B` 14단계 배열, 정렬 기준의 단일 출처.

---

---

## 16. 로그인 페이지 (`/login`) — v4 추가

PoC는 단일 계정 인증 (id `risk` / pw `1962`). 미인증 접근은 모두 `/login`으로 리다이렉트.

### 16.1 레이아웃

```
┌────────────────────────────────────────────────┐
│                                                │
│              ┌──────────────────┐              │
│              │                  │              │
│              │ Credit Universe  │              │
│              │                  │              │
│              │  ┌────────────┐  │              │
│              │  │ 아이디     │  │              │
│              │  └────────────┘  │              │
│              │  ┌────────────┐  │              │
│              │  │ 비밀번호   │  │              │
│              │  └────────────┘  │              │
│              │                  │              │
│              │  [   로그인   ]  │              │
│              │                  │              │
│              └──────────────────┘              │
│                                                │
└────────────────────────────────────────────────┘
```

- 페이지 컨테이너: `min-h-screen flex items-center justify-center bg-background px-6`
- 카드: `w-full max-w-sm rounded-xl border bg-card p-8` + `--shadow-elevated`
- 로고 영역: 중앙 정렬 텍스트만 — 타이틀 `text-3xl font-semibold tracking-tight` ("Credit Universe"). 아이콘/서브타이틀 없음.
- 입력 사이 간격: `space-y-3`
- Primary 버튼: `w-full` + `Button size="default" variant="default"` (가이드 §6.6)

### 16.2 컴포넌트 매핑

| 영역 | shadcn 프리미티브 |
|---|---|
| 카드 | `Card` |
| 입력 (id, pw) | `Input` (type="text" / "password") |
| 라벨 | `Label` (위쪽 정렬, `text-xs font-medium text-muted-foreground`) |
| 버튼 | `Button` (variant=default, size=default, w-full) |
| 에러 메시지 | §10.3 에러 컨테이너 패턴 (border-destructive/30, bg-destructive/5) |

### 16.3 인터랙션

- 엔터 키 → 자동 제출
- 잘못된 자격 → 카드 하단에 인라인 에러 (`text-sm text-destructive`)
- 성공 → `/`(매트릭스)로 이동
- 로딩: 버튼 안 `Loader2 animate-spin` + "로그인 중…" 라벨 + disabled
- 자동 로그인 / 비밀번호 찾기 / 회원가입 링크 **모두 없음** (PoC 단일 계정)

### 16.4 시각 톤

- 헤더/푸터 없음 — 전체 화면 단순 레이아웃
- 다른 페이지보다 **여백을 더 많이** 사용 (entry point 인상)
- 모션은 §11 위치가 아니므로 **사용 금지** (페이드인 등)

---

_본 문서는 디자인 변경과 함께 동기화 유지가 필요합니다. 토큰/컴포넌트를 수정하면 해당 섹션을 갱신해 주세요._
