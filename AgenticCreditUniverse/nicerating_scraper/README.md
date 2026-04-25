# NICE신용평가 스크래퍼

NICE신용평가(https://www.nicerating.com)에서 기업 공개 정보와 (선택적으로)
로그인 기반 재무부표 전체를 가져오는 파이썬 스크립트입니다.

## 제공 기능

| # | 기능 | 엔드포인트 | 로그인 |
|---|------|------------|-----|
| 1 | 기업명 → `cmpCd` 자동 해석 (정확 매칭 시 리다이렉트) | `GET /search/search.do` | ✗ |
| 2 | 기업 개요 (기업명·산업·계열·결산월) | `GET /disclosure/companyGradeInfo.do` | ✗ |
| 3 | **연결 / 개별 주요재무지표** (7 회계연도 × 18 지표) | `POST /company/companyMajorFinanceProc.do` | ✗ |
| 4 | **등급 히스토리 전체** (채권/기업어음/전자단기사채/기업신용등급·보험지급능력) | JS 렌더링 DOM | ✗ |
| 5 | **최신 등급확정일 의견서 PDF** 실제 다운로드 | `GET /common/fileDown.do?docId=<UUID>` | ✗ |
| 6 | 로그인 (유료회원) | `POST /logInProc.do` (form: `userId`, `userPw`) | — |
| 7 | **연결 기준 재무부표 전체** (BS 58 / IS 52 / CF 47 ≒ 157 행) | `POST /company/companyChargeFinanceProc.do` | ✓ |

출력: **JSON**, **CSV** (UTF-8 BOM, 한글 엑셀 호환), `pandas.DataFrame`.

## 설치

```bash
pip install requests beautifulsoup4 lxml pandas python-dotenv
# 최신 PDF 다운로드(JS 렌더링 필요) 를 사용하려면:
pip install playwright && playwright install chromium
```

## 최신 PDF 선정 규칙

유형 상관없이 기업 페이지의 모든 등급 히스토리 테이블을 수집한 뒤
**등급확정일**이 가장 최근인 행을 고릅니다. 동일 일자가 여럿이면
다음 순서로 타이브레이크 합니다.

1. 등급확정일 (desc)
2. 등급결정일(평가일) (desc)
3. 유형 우선순위: 채권 → 기업어음 → 전자단기사채 → 기업신용등급 → 보험지급능력 → 기타
   (장기 채권 발행의 평가의견서가 가장 상세)
4. 원 테이블 내 행 순서 (서버가 이미 최신순 반환)

파일명 형식:

- 회차 있는 행(채권): `<cmpCd>_<YYYYMMDD>_<회차>_<종류>_<등급>.pdf`
  예: `1670352_20260305_제224-4회_SB_AA+.pdf`
- 회차 없는 행(기업신용등급·기업어음 등): `<cmpCd>_<YYYYMMDD>_<등급유형>_<등급>.pdf`

## 자격 증명 (유료 재무부표 전용)

`.env` 파일을 프로젝트 루트에 만들어 아래 두 값을 설정하면 `--full-financials`
옵션으로 연결 기준 재무부표 전체를 내려받을 수 있습니다.

```bash
cp .env.example .env
# 에디터로 .env 열어 실제 값 입력
```

키 이름:

```
NICERATING_USER_ID=...
NICERATING_USER_PW=...
```

보안 메모:

- 스크래퍼는 자격 증명을 **메모리에서만** 사용합니다. 파일/로그에 쓰지
  않으며, 로그 핸들러에 설치된 필터가 ID/PW 문자열을 자동으로 `***` 로
  치환합니다.
- `.env.example` 은 placeholder 만 포함합니다. 실제 `.env` 는 git 등에
  절대 커밋하지 마세요.
- CI 에서는 환경변수로 직접 주입하고 실행 후 `unset` 하세요.

## CLI 사용 예

```bash
# 공개 요약 + 최신 신용평가 PDF (가장 최근 등급확정일 행)
python3 nicerating_scraper.py --cmpcd 1670352 --outdir ./out

# 기업명으로
python3 nicerating_scraper.py --name "SK하이닉스" --outdir ./out

# 로그인해서 재무부표 전체까지
python3 nicerating_scraper.py --cmpcd 1670352 --outdir ./out --full-financials
```

## 프로그래밍 API

```python
from nicerating_scraper import NiceRatingScraper

s = NiceRatingScraper(request_delay=1.0)

# (선택) 로그인
s.login()   # env 미설정이면 ValueError

# cmpCd 해석
cmpCd = s.resolve_cmpcd("SK하이닉스")

# 공개 요약 재무
ft_summary = s.get_financials(cmpCd, kind="CFS")

# 재무부표 전체 (로그인 필요)
ft_full = s.get_full_financials(cmpCd, kind="CFS")

# 최신 등급 PDF
rating, pdf_path = s.download_latest_rating_pdf(cmpCd, outdir="./out")
```

## 실제 실행 기록 (검증 완료)

### 1) 삼성전자 (cmpCd=1326874)

- 기업명 "삼성전자(주)" → cmpCd **1326874** (리다이렉트 자동 해석) ✓
- 연결 기준 주요재무지표 7 회계연도 × 18 지표 ✓
- 최신 등급확정일 **2004.06.01** (채권 제168회 선순위 SB, AAA/안정적),
  docId `00000000-0000-0000-0000-0d6XQ2SNfrZt`
- PDF 저장: `demo_out/1326874_20040601_채권_AAA.pdf` · 412,144 B · 2 pages ✓

### 2) SK하이닉스 (cmpCd=1670352)

- 기업명 "SK하이닉스" → cmpCd **1670352** (리다이렉트) ✓
- 최신 등급확정일 **2026.03.05**, 제224-4회 선순위 SB, AA+/안정적
  (발행일 2023.02.14, 만기 2033.02.14, 발행액 800억원), 
  docId `0602f034-8f4b-45e9-bb0e-dad43e69ebb4`
- PDF 저장: `demo_out/1670352_20260305_제224-4회_SB_AA+.pdf` · 699,996 B · 10 pages ·
  magic `%PDF-1.7` ✓
- 로그인 후 재무부표 전체 (연결 기준) 저장:
  `demo_out/nicerating_1670352_CFS_full.json` / `.csv`
  · BS 58 행 + IS 52 행 + CF 47 행 = **157 행 × 7 회계연도** ✓
- 샘플 수치 (CFS 연결, 단위: 억원 또는 % — `계정명` 내 표기):
  - 매출액: 2019→269,907, 2023→327,657, **2025→971,467**
  - 당기순이익: 2019→20,091, 2023→**-91,375**, 2025→429,479
  - 자산총계: 2019→652,484, 2025→1,761,077
  - 부채비율(%): 2019→36.1, 2023→87.5, 2025→**45.9**
  - 잉여현금흐름(FCF): 2019→-79,898, 2025→249,408
  - ROA(%): 2019→3.1, 2025→29.0

### 실제 실행 한 줄 (E2E 재현)

```bash
# .env 에 NICERATING_USER_ID / NICERATING_USER_PW 설정 후
python3 nicerating_scraper.py --name "SK하이닉스" --outdir ./demo_out --full-financials
```

## 파일 구성

```
.
├── nicerating_scraper.py        # 스크래퍼 (CLI + 라이브러리)
├── README.md                    # 이 문서
├── .env.example                 # 자격 증명 키 예시 (placeholder)
├── tests/
│   └── test_parsing.py          # 오프라인 end-to-end 테스트
├── fixtures/                    # 실제 사이트에서 캡처한 응답
│   ├── company_detail.html      # 삼성 기업 상세 페이지
│   ├── company_research.html    # 삼성 리서치 탭
│   ├── research_preview.html    # 리서치 preview.do 샘플
│   ├── file_down_paid.html      # fileDown.do 유료 차단 응답
│   ├── finance_cfs.json         # 공개 주요재무지표 JSON (삼성)
│   ├── charge_finance_cfs.json  # 재무부표 전체 JSON (삼성, 로그인 후)
│   └── charge_finance_cfs_skhynix.json   # 동일, SK하이닉스
└── demo_out/                    # 샘플 실행 결과
    ├── nicerating_1326874_CFS.json         # 삼성 공개 요약
    ├── nicerating_1326874_CFS.csv
    ├── 1326874_20040601_채권_AAA.pdf        # 삼성 최신 등급 PDF
    ├── 1670352_20260305_제224-4회_SB_AA+.pdf  # SK하이닉스 최신 등급 PDF
    ├── nicerating_1670352_CFS_full.json    # SK하이닉스 재무부표 전체 (연결)
    └── nicerating_1670352_CFS_full.csv
```

## 스크래핑 매너

- `robots.txt` 는 빈 응답 (별도 규칙 없음).
- 기본 1초 요청 지연 (`--delay 2.0` 등으로 조정).
- 일반 브라우저 수준의 `User-Agent`/`Accept-Language` 헤더 사용.
- JS 렌더링 (Playwright) 은 기업 상세 페이지 docId 매핑 추출 1회만
  수행하고 PDF 자체는 `requests` 로 직접 받습니다.
