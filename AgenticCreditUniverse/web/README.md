# 크레딧 유니버스 웹 (PoC)

신용평가 유니버스 1,000행을 분석가 한 명이 검수·확정하기 위한 단일 계정 웹 대시보드.

## 구조

```
web/
├── DESIGN-GUIDE.md         # 시각/인터랙션 단일 출처 (v4)
├── PLAN.md                 # 정보구조/기능/데이터 단일 출처 (v6)
├── frontend/               # Next.js 15 (App Router) + Tailwind v4 + shadcn/ui
├── backend/                # FastAPI (Python 3.14, .venv 공유)
├── Pretendard-1.3.9/       # 한글 폰트 패키지 (woff2는 frontend/app/fonts/로 복사)
├── Makefile                # make backend / make frontend / make index
└── .env.example            # backend/.env로 복사 후 사용
```

## 첫 실행 (개발)

```bash
cd web/
cp .env.example backend/.env          # SESSION_SECRET 채우기
make install                          # python deps + npm deps
make index                            # _workspace/index.sqlite 빌드
# 두 터미널에서:
make backend                          # http://localhost:8787
make frontend                         # http://localhost:3000
# 로그인: id `risk` / pw `1962`
```

## 데이터 흐름

- 단일 진실의 원천(SSOT) = `output/26.1H 유니버스.xlsx` (18컬럼) + `_workspace/` 산출물
- 백엔드 startup 시 SQLite 인덱스 풀 리빌드 (현재 데이터 22행, < 200ms)
- UI는 읽기 전용. 단 하나의 쓰기 액션 = 종목 상세의 "검수 확정" → Excel Col 18 + `_workspace/review_status.json` 동시 갱신 (매 쓰기 직전 `output/backup/`에 자동 백업)
- Col 14 (의견변동) Excel 수식은 모든 쓰기에서 보존됨 (`data_only=False` 로드)

## 화면 구조

| 라우트 | 용도 |
|---|---|
| `/login` | 단일 계정 로그인 (id `risk` / pw `1962`) |
| `/` | 매트릭스 (전체 종목 + KPI 4카드 + 좌측 필터 + 22행 가상화 테이블) |
| `/company/[slug]` | 종목 상세 (단일 세로 스크롤 + 우측 floating TOC + 7섹션 + 검수 액션 패널) |

## 폴더

```
backend/app/
├── main.py            # FastAPI 진입점, lifespan에서 인덱스 리빌드
├── settings.py        # pydantic-settings (.env 로드)
├── auth.py            # itsdangerous 12h 세션
├── deps.py            # SQLite 커넥션 의존성
├── excel_writer.py    # Col 18 atomic write (Col 14 수식 보존)
├── schemas.py         # pydantic 응답 모델
├── db_schema.sql      # SQLite 스키마
└── routers/{auth,companies,review}.py
backend/scripts/
└── build_index.py     # _workspace/index.sqlite 리빌드

frontend/app/
├── login/page.tsx     # 단일 계정 로그인
├── page.tsx           # 매트릭스
├── company/[slug]/page.tsx
├── error.tsx, not-found.tsx, loading.tsx
├── globals.css        # DESIGN-GUIDE §2 oklch 토큰 + @theme inline
├── layout.tsx         # Pretendard 셀프호스팅
└── fonts/             # Pretendard-{Regular,Medium,SemiBold}.woff2
frontend/components/
├── AppHeader.tsx, kpi-card.tsx, rating-badge.tsx, watch-badge.tsx, universe-chip.tsx
├── matrix/{KpiBar,Sidebar,MatrixTable,MatrixView,types}.tsx
├── detail/{DetailHeader,ReviewActionPanel,FloatingTOC, Section1Overview..Section7History}.tsx
└── ui/                # shadcn 18종 (button, input, card, …)
frontend/lib/
├── api.ts             # 서버측 fetch 헬퍼
├── credit.ts          # 등급/전망/포매팅 유틸
├── nice.ts            # NICE 시리즈 매핑
└── utils.ts           # cn()
```
