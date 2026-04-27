# AgenticCreditUniverse

## 하네스: 신용평가 유니버스 자동화

**목표:** 발행기관 리스트를 받아 DART 공시·NICE 재무지표·신평 의견서·뉴스/리스크를 수집하고, Claude Sonnet 4.6으로 26.1H 검토 코멘트를 생성하여 엑셀 유니버스에 행 단위로 채워 넣는다.

**트리거:** 신용평가 유니버스 작성/갱신/재실행 관련 요청 시 `universe-build` 스킬을 사용하라. 단순 질문(스크래퍼 동작 원리, 컬럼 의미 등)은 직접 응답 가능.

**주요 모듈** (`AgenticCreditUniverse/` 하위):
- `dart_scraper/` — DART 사업내용 + 연결주석(별도 폴백)
- `nicerating_scraper/` — NICE 표준 재무지표 + 의견서 PDF
- `pplx_news/` — Perplexity 뉴스·리스크 리서치 (프롬프트는 `prompt_template.py` 분리, 기본 모델 `google/gemini-3.1-pro-preview`)
- `comment_generator/` — Claude Sonnet 4.6 (1M context) 코멘트 생성 + 유니버스 포함여부 2-stage 판정
  - Stage 1 (`generate_comment.py`): 종목별 코멘트 + 잠정 판단(O/△/X)
  - Stage 2 (`judgment_review.py`): 풀 단위 형평성·안정성 가드레일 검수 → 최종 판단

**환경 파일**(.gitignore 처리됨):
- `AgenticCreditUniverse/secrets.env` — `ANTHROPIC_API_KEY`, `DART_API_KEY`, `PERPLEXITY_API_KEY`, (선택) `NICE_USERNAME/PASSWORD`
- DART/NICE/Perplexity 키도 `.env` 포맷 파일에서만 로드. 코드 박지 않음.

**Python 환경**: `.venv/` (프로젝트 루트). 의존성: `requests`, `lxml`, `beautifulsoup4`, `python-dotenv`, `anthropic`, `openpyxl`. (선택) `playwright + chromium` — NICE 의견서 PDF 자동 다운에만 필요.

**작성 원칙:**
- 정제된 **연결재무지표 우선·없으면 별도** 폴백.
- 최신 공시 **연결재무제표 주석 우선·없으면 별도** 폴백.
- 입력에 없는 수치/사실은 만들지 않는다(환각 금지).
- 사용자가 수기 작성한 셀(25.2H 코멘트, 그룹사 표기 등)은 머지 시 **보존**한다.

## 디자인

모든 시각·스타일 결정은 `AgenticCreditUniverse/web/DESIGN-GUIDE.md`를 따른다.
이 문서를 먼저 읽지 않은 상태로 컴포넌트나 페이지를 작성하지 않는다.
정보 구조·기능·데이터 흐름은 짝꿍 문서 `AgenticCreditUniverse/web/PLAN.md`를 함께 참조한다.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-25 | 초기 구성 (6 agents + 7 skills) | 전체 | 사용자 수기 워크플로우의 자동화 |
| 2026-04-25 | 7개 이슈 영구 반영 + 코멘트 길이 강화 (400~600자 STRICT) | dart_scraper.py / master-mapping(scripts/resolve_nice.py 신규) / comment_generator(prompt_template + batch_generate.py 신규) / nice-collection / universe-build / CLAUDE.md | 첫 빌드(SKC·대한해운·한솔테크닉스)에서 발견된 우회 항목 본체화 — DART API 변경 대응, NICE 다중 매칭 자동 해소, ITPM 자동 sleep, 길이 강제 + 캐싱 활성화 |
| 2026-04-25 | 코멘트 입력에서 DART 연결재무제표 주석 제거 | comment_generator/{generate_comment.py, batch_generate.py, prompt_template.py} | 토큰 폭주 해소 — 주석이 input의 ~75%(SKC 기준 126K→~30K, ↓76%). DART scraper의 notes 수집은 보존(향후 용도) |
| 2026-04-25 | 코멘트 종결어미 정책 변경 (명사형 우선) | comment_generator/prompt_template.py | 신평 보고서 관행에 맞춤 — "…함/임/됨" 70%+ 통일. 가이드 + 예시 + self-check 동시 갱신으로 톤 일관성 확보 |
| 2026-04-25 | 수치 비교 표기 규칙 + NICE 수치 우선 정책 추가 | comment_generator/prompt_template.py | 전년대비 증감 시 괄호("(전년 100%)") 또는 화살표("100%→70%") 병기 의무화. PDF/뉴스 수치는 lag 가능성 → 충돌 시 NICE 값 채택 |
| 2026-04-25 | 뉴스 모듈 정리 — 폴더 리네임 + 프롬프트 외부 분리 + 기본 모델 변경 | pplx_risk_skhynix_gemini/ → pplx_news/, prompt_template.py 신설, pplx_risk_analyst.py 기본 --api agent | 폴더명 SK하이닉스/Gemini 흔적 제거. comment_generator와 동일하게 프롬프트 분리. 기본 호출이 `google/gemini-3.1-pro-preview` + web_search/fetch_url 도구 조합으로 작동 |
| 2026-04-26 | 26.1H 유니버스 포함여부 자동 판정 (2-stage 구조 + 안정성 가드레일) | comment_generator/{prompt_template.py, generate_comment.py, batch_generate.py, prompt_template_judgment.py 신규, judgment_review.py 신규, extract_existing_universe.py 신규} / .claude/skills/{excel-merge, judgment-review 신규, comment-generation, universe-build}/SKILL.md / .claude/agents/judgment-reviewer.md 신규 | 종목별 1차(comment-writer) → 풀 단위 2차(judgment-reviewer) 분리로 등급 간 형평성 보장. 직전 반기 대비 하향·상향 비중 ≤10% soft cap으로 반기 변동 안정화. 엑셀 컬럼 17개로 확장 — "AI 판단"(Stage 2 final 기호) + "심사역 최종 판단"(수기 보존) 추가 |
| 2026-04-26 | 엑셀 18개 컬럼으로 확장 + 의견변동 자동 수식 + 풀 정리 | output/26.1H 유니버스.xlsx (마이그레이션) / _workspace/{migrate_18cols.py 신규, merge_run.py 갱신} / .claude/skills/{excel-merge, universe-build, judgment-review}/SKILL.md / .claude/agents/judgment-reviewer.md | (i) AI 판단 사유 컬럼(Q열) 신설 — Stage 2 rationale을 엑셀 한 화면에서 확인. (ii) 의견변동(N열)에 I열↔J열 비교 수식 박아 사용자 J열 수정 시 ▲/▽/- 자동 갱신. (iii) 삼성FN리츠 행 삭제. 머지 base를 in-place(output 자체)로 변경하여 사용자 수기 작업 누적 가능. |
| 2026-04-26 | 웹 대시보드 설계 문서 도입 + 디자인 원칙 섹션 신설 | AgenticCreditUniverse/web/{DESIGN-GUIDE.md v4, PLAN.md} / CLAUDE.md (## 디자인 섹션) | PoC 웹 대시보드(매트릭스 + 종목 상세 + 검수 워크플로우) 설계 정합 — DESIGN-GUIDE는 시각/인터랙션 단일 출처, PLAN은 정보구조/기능/데이터 단일 출처. 두 문서 사이 충돌 항목은 PLAN 우선 정합 완료. 신규 컴포넌트·페이지 작성 전 두 문서 선독 강제. |
| 2026-04-26 | 매트릭스 행 호버 — solid `--row-hover` 토큰 도입, sticky 컬럼 뒤 비침 해결 + 호버 식별성 강화 | web/frontend/app/globals.css / web/frontend/components/matrix/MatrixTable.tsx / web/DESIGN-GUIDE.md §10.2 | 가로 스크롤 시 sticky "발행기관" 컬럼이 `bg-muted/50`(50% 알파)로 인해 반투명해져 우측 콘텐츠가 비쳤음. 행-레벨 호버 bg + sticky 셀 solid 호버 오버라이드로 분리하고, 솔리드 토큰(oklch 0.93)으로 식별성 ↑. |
| 2026-04-26 | 매트릭스 KPI 4카드 재구성 + 분포 차트 행 신설 + 유의업종 컬럼 + 22종목 업종 백필 | web/frontend/components/matrix/{KpiBar.tsx, MatrixTable.tsx, types.ts, DistributionRow.tsx 신규, RatingDistChart.tsx 신규, IndustryDistChart.tsx 신규} / web/frontend/app/page.tsx / web/backend/scripts/build_index.py / _workspace/master/{master.json, watch_industries.json 신규} / _workspace/scripts/seed_industries.py 신규 / output/26.1H 유니버스.xlsx (Col 4 22행) / web/PLAN.md v7 / web/DESIGN-GUIDE.md §4.5 | KPI ① "전체종목" → "검토 N + 가능/조건부/미편입 가로 카운트", KPI ② "등급분포 미니바" → "부정적 전망 N (X.X%)"로 교체. 분포는 KPI 아래 새 행으로 분리(좌: 등급 BarChart, 우: 업종 Donut). 유의업종 자동 판정 SSOT(`watch_industries.json` 7개 카테고리: 2차전지/석유화학/철강/상영관/건설/저축은행/부동산신탁) — build_index.py가 industry 매칭 시 자동 ○ 부여, 사용자 명시 'O'는 보존. |
| 2026-04-26 | 매트릭스 페이지 스크롤 전환 + 분포 차트 동일 높이/녹→적 그라데이션/도넛 확대·상위10 범례 | web/frontend/{app/page.tsx, components/matrix/{MatrixTable.tsx, MatrixView.tsx, KpiBar.tsx, Sidebar.tsx, DistributionRow.tsx, RatingDistChart.tsx, IndustryDistChart.tsx}} | (i) `flex h-screen` 매트릭스 내부 스크롤을 `min-h-screen` 페이지 스크롤로 전환 — KPI/분포가 자연스럽게 스크롤 아웃, AppHeader sticky-top-0 + 매트릭스 헤더·사이드바 sticky-top-14(=AppHeader 아래)로 viewport 고정. (ii) `useVirtualizer(parentRef)` → `useWindowVirtualizer(scrollMargin)` 로 전환 + 가로 스크롤 동기화(헤더/본문 두 overflow-x-auto 컨테이너 scrollLeft sync). (iii) 분포 카드 동일 높이 340px 고정. (iv) RatingDistChart 6단계 색상을 `--rating-tier-{1,2,4,6,7,8}` (oklch hue 160→25 그라데이션, 등급/전망 시맨틱과 동일)로 매핑 — AAA/AA, BB/B↓ 동일 색 회피. (v) IndustryDistChart 도넛 inner 60·outer 120 으로 확대 + 범례 상위 10개 + 비중(%) 만 표기. |
| 2026-04-27 | `/login` cosmic intro + 상시 starfield + 로그인 성공 시 dark→light 핸드오프 + 로그인 페이지 영문화 | web/frontend/components/cosmic/{BackgroundStars.tsx, IntroOverlay.tsx, useTextTargets.ts, cosmicTransition.ts 신규 4종} / web/frontend/app/login/page.tsx (영문화 + 다크 카드 + 캔버스 마운트 + 핸드오프 트리거) / web/frontend/app/globals.css (`body.cosmic-mode` + `.cosmic-handoff` 추가) / web/DESIGN-GUIDE.md §16.4 보정 + §16.5 신설 | 진입점 시그니처 모션 추가 — 별이 swirl → 텍스트 픽셀로 수렴 → 잔잔한 우주 배경으로 정착, 로그인 성공 시 어두운 우주에서 화사한 매트릭스로 부드럽게 인계. 외부 라이브러리 0(순수 Canvas 2D + RAF), 1회 표시(sessionStorage), `prefers-reduced-motion` skip, 30fps throttle, visibility pause, DPR 스케일링. `/login` 라우트에서만 mount → 매트릭스 라이트 테마 무영향. |
| 2026-04-27 | `/login` 인트로 단순화 + 레이아웃 분리 (사용자 피드백 반영) | web/frontend/components/cosmic/IntroOverlay.tsx (migration phase 폐기, 2단계 swirl→페이드로 단순화) / web/frontend/components/cosmic/useTextTargets.ts (삭제) / web/frontend/app/login/page.tsx (타이틀을 카드 외부 화면 상단으로 분리, `text-5xl ~ text-7xl` responsive) / web/DESIGN-GUIDE.md §16.1·§16.5.1·§16.5.5 (시퀀스/SSOT 갱신) | 별이 텍스트 모양으로 모이는 migration 이 시각적 완성도가 낮아 폐기. swirl → 동시 페이드아웃 + 타이틀·카드 페이드인(1200ms ease-out)으로 변경. 타이틀은 카드 안 `text-3xl` 에서 카드 외부 상단 `text-5xl~text-7xl` 큼지막한 hero 텍스트로 승격. 카드는 inputs + Sign in 버튼만 보유. 인트로 시퀀스 총 길이 5.2s → 3.9s. |
| 2026-04-27 | EB Garamond Italic hero + 좌우 코너 라벨 + FOC 해결 + reveal 3s 확장 (사용자 피드백 단계적 반영) | web/frontend/app/layout.tsx (next/font/google `EB_Garamond` italic 추가, `--font-eb-garamond` 변수 노출) / web/frontend/app/login/page.tsx (`useSyncExternalStore` 서버 snapshot `() => true` 로 반전 → SSR opacity:0, Global No.1 RWA Hub / Credit Intelligence Platform 코너 라벨, EB Garamond italic hero `clamp(48px,9vw,128px)`, reveal `cubic-bezier(0.16,1,0.3,1)` 3000ms + stagger 0/300/600ms, 코너 라벨 `text-sm sm:text-base`) / web/frontend/components/cosmic/IntroOverlay.tsx (T_SWIRL_END 2200, T_REVEAL_TRIGGER 3500, T_FADE_END 5200, fade `1 - t³` cubic ease-in) / web/DESIGN-GUIDE.md §16.5.1 시퀀스 표 갱신 | 사용자 피드백 4단계 반영: ① 깜빡임 — SSR snapshot 반전으로 첫 페인트부터 invisible 보장. ② 미적 비율 — 코너 라벨 + EB Garamond Italic hero + 라디얼 글로우. ③ 급한 느낌 — reveal 1.4→1.8→3.0s 확장, 별 페이드 cubic ease-in 3s, 1.7s 크로스페이드 윈도우. ④ 코너 라벨 가독성 — `text-[13px] sm:text-sm` → `text-sm sm:text-base`. 총 인트로 길이 ~6.8s. |
| 2026-04-27 | `/login` 회전 감속 + 페이드 linear 4s (사용자 피드백 3차) | web/frontend/components/cosmic/IntroOverlay.tsx (omega 약 60% 감속 — stars 0.45-1.0 → 0.15-0.40, dust 0.25 → 0.10. fade curve cubic ease-in `1-t³` → linear `1-t`. T_REVEAL_TRIGGER 3500 → 4000, T_FADE_END 5200 → 6200) / web/DESIGN-GUIDE.md §16.5.1 (시퀀스 표 갱신) | 별 회전이 여전히 빨라 보이고 페이드도 급하다는 피드백 정밀 대응. cubic ease-in 곡선이 처음엔 alpha 1 에 lingering 하다 끝에서 가속 dropoff 라 perceived "급함"의 근본 원인이었음 — linear 로 변경하니 4s 내내 균등 감소로 진정한 4초의 fade 가 시각적으로 인지됨. 총 인트로 길이 ~6.8s → ~7.6s. |
| 2026-04-27 | 외부 배포 — Vercel(프론트) + HuggingFace Spaces(백엔드) 무료 호스팅 | web/backend/scripts/build_index.py (절대경로 → env var, default 계산 lazy 로 컨테이너 IndexError 회피) / web/backend/Dockerfile + requirements.txt + frontend/public/robots.txt + frontend/app/layout.tsx (`robots: noindex/nofollow`) / .dockerignore (git 루트) / _hf_space/ staging 디렉토리 + _workspace/scripts/deploy_hf_space.py (huggingface_hub.upload_folder + add_space_secret + restart_space 자동화) | 경진대회용+사내 데모로 외부 시연 가능한 URL 필요. Fly.io 영구무료 종료(7일 trial 후 과금)로 HF Spaces Docker SDK 채택 — CPU basic free + ephemeral disk(검수 쓰기는 컨테이너 라이프타임 동안 유지, 재배포 시 초기화). 320MB 데이터(NICE PDF 포함) baked-in. Space 처음 Private 으로 만들었으나 Vercel rewrites 가 토큰 없이 호출하므로 Public 전환(데이터는 require_session 가드로 그대로 보호). LOGIN/SESSION secrets 자동 생성·HF Settings 등록. 프로덕션: `https://credit-universe.vercel.app` (rewrites → `https://theloves-credituniverse.hf.space`). |
| 2026-04-27 | Cosmic intro 매 방문 재생 (sessionStorage "1회" 정책 폐기) | web/frontend/components/cosmic/IntroOverlay.tsx (sessionStorage.setItem 1줄 삭제 + JSDoc 갱신) / web/frontend/app/login/page.tsx (shouldPlayIntroSnapshot 에서 sessionStorage 체크 삭제, prefers-reduced-motion 만 남김) / web/DESIGN-GUIDE.md §16.5.1·§16.5.2 (시퀀스/정책 갱신) | 배포 직후 사용자 피드백 — production 첫 진입 후 같은 탭 재방문 시 인트로 skip 되어 시연 가치 손상. sessionStorage 캐시(IntroOverlay T_REVEAL_TRIGGER 4s 도달 시 setItem)가 LoginPage shouldPlayIntroSnapshot 에서 introDone=true 즉시 마운트 → IntroOverlay 자체 미마운트가 원인. 시그니처 모션은 매번 보여야 가치 있음(22행 데이터라 자주 들어오는 워크플로우도 아님). prefers-reduced-motion 존중은 유지. |
| 2026-04-27 | Cosmic intro `prefers-reduced-motion` 무시 — 모든 사용자 강제 재생 | web/frontend/app/login/page.tsx (shouldPlayIntroSnapshot 항상 true 반환) / web/DESIGN-GUIDE.md §16.5.3 (a11y 예외 명시) | sessionStorage 정책 폐기 후에도 사용자(Chrome) 에서 인트로 미표시. SSR HTML 분석 결과 캔버스+opacity:0 등 SSR 정상이나 hydration 직후 IntroOverlay 즉시 unmount → client snapshot 의 matchMedia(reduced-motion) 가 true 반환하는 환경 의심(OS 설정 또는 Chrome 내부 정책). 진단보다 fix 우선 — 시연/심사 컨텍스트라 OS 설정이 silent-skip 못 하게 강제 true. a11y < demo first-impression 명시. 시연 종료 후 일반 운영 전환 시 재검토. |
