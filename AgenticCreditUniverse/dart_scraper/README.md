# DART Scraper

기업명 또는 corp_code를 받아 **가장 최신 정기보고서**(사업/반기/분기)를
DART OpenAPI로 찾고, 본문에서 **"사업의 내용"** 섹션과
**"연결재무제표 주석"**(없으면 **"재무제표 주석"**)를 추출해
HTML / 텍스트 / 메타데이터로 저장합니다.

## 필요 버전

- Python 3.10 이상
- 의존성: `requests`, `beautifulsoup4`, `lxml`, `python-dotenv`, `pytest`

```bash
pip install -r requirements.txt
```

## API 키 발급

1. <https://opendart.fss.or.kr/> 에 접속 → **회원가입**.
2. 로그인 후 **인증키 신청 / 관리** 메뉴에서 **인증키 신청**.
3. 이메일로 40자리 인증키 수신. 즉시 사용 가능 (일일 호출 한도 있음).

발급받은 키를 `.env` 파일에 저장하세요.

```bash
cp .env.example .env
$EDITOR .env                  # DART_API_KEY=... 채우기
```

> 키는 절대 저장소나 로그에 남기지 마세요. `.env`는 `.gitignore`에 포함되어 있습니다.

## 실행 예시

```bash
# 기업명으로 (최신 정기보고서: 사업/반기/분기 중 가장 최근 접수)
python dart_scraper.py --name "SK하이닉스" --outdir out/skhynix

# 사업보고서(A001)로 한정
python dart_scraper.py --name "삼성전자" --report-type A001 --outdir out/samsung

# corp_code로 직접 지정 (동명이인 회피)
python dart_scraper.py --corp-code 00164779 --outdir out/skhynix

# 별도(standalone) 주석 우선
python dart_scraper.py --name "카카오" --prefer standalone --outdir out/kakao

# 스크립트 인자로 비대화식(에러 시 --corp-code 재실행 안내)
python dart_scraper.py --name "삼성전자" --non-interactive

# 캐시 강제 갱신 (corpCode.xml 재다운로드)
python dart_scraper.py --name "네이버" --force-refresh
```

### 동명 기업 처리

`--name`만 주었는데 여러 건이 매칭되면, 상장 여부·corp_code·결산 정보와 함께
목록을 출력하고 STDIN으로 번호 입력을 받습니다. 배치 환경에서는
`--non-interactive` + `--corp-code`를 쓰세요.

## 출력 형식

`--outdir` 디렉토리에 아래와 같이 저장됩니다.

```
out/skhynix/
├── metadata.json            # corp / report / section 메타
├── business_section.html    # 사업의 내용 (원문 XML을 HTML 래핑)
├── business_section.txt     # 사업의 내용 (plain text 추출)
├── notes_section.html       # (연결)재무제표 주석
├── notes_section.txt
└── raw/
    ├── document.zip         # DART document.xml 원문 zip
    └── <member>.xml         # zip에 포함된 각 XML
```

`metadata.json`에는 `corp`, `report`(rcept_no, rcept_dt, report_nm 등),
`report_type_name`, 각 섹션의 상태(`ok`/`missing`) 및 `notes_section.variant`
(`consolidated` | `standalone`)가 기록됩니다.

## 캐시

`corpCode.xml`은 사이즈가 커서 1회 다운로드 후 `~/.cache/dart_corp_codes.json`에
24시간 캐시됩니다. `--force-refresh`로 무효화할 수 있습니다.

## CLI 옵션

| 인자 | 설명 |
|------|------|
| `--name <기업명>` | 회사명 검색 (한/영). `--corp-code`와 택일. |
| `--corp-code <8자리>` | DART 고유번호 직접 지정. |
| `--report-type any\|A001\|A002\|A003\|A004` | 기본 `any`. A001=사업, A002=반기, A003=1Q, A004=3Q. |
| `--prefer consolidated\|standalone` | 주석 우선순위. 기본 `consolidated`. 없으면 자동 폴백. |
| `--outdir <path>` | 저장 위치 (기본 `./out`). |
| `--non-interactive` | 동명 매칭 시 대화식 선택 없이 에러. |
| `--force-refresh` | corpCode 캐시 무시하고 재다운로드. |
| `-v, --verbose` | DEBUG 로깅. |

## 섹션 추출 규칙

DART 원문 XML은 `<SECTION-N><TITLE>…</TITLE>…</SECTION-N>` 형태로 계층화되어
있습니다. `<TITLE>` 텍스트를 정규화(NFKC + whitespace 정규화) 후 다음 정규식으로
매칭합니다.

- **사업의 내용**: `사업의\s*내용` (로마 숫자 / 아라비아 숫자 접두 상관없이 매칭)
- **연결 주석**: `연결재무제표(?:에\s*대한)?\s*주석`
- **별도 주석**: `재무제표(?:에\s*대한)?\s*주석` (단, 연결 버전은 `exclude`로 제외)

매칭된 `<TITLE>`의 가장 가까운 `SECTION-*` 조상을 해당 섹션의 루트로
삼아 XML 하위트리 전체를 직렬화합니다.

## 테스트

네트워크 / API 키 없이 로직을 검증하는 단위 테스트가 포함되어 있습니다.

```bash
python -m pytest test_dart_scraper.py -v
```

fixture (`fixtures/`) 에서:
- corpCode.xml 파서 — 상장/비상장 분리, 매칭 우선순위, zip 추출
- 최신 보고서 선정 — 날짜 우선, 동일 날짜일 때 유형 랭크(A001>A002>A004>A003)
- 섹션 추출 regex — 사업의 내용, 연결/별도 주석, exclude 필터 및 폴백 동작

## 보안 / 에티켓

- 요청 간 0.5–1.0s 지연, 429/5xx에 대해 지수 백오프 재시도(최대 4회).
- User-Agent 명시.
- API 키는 환경변수/`dotenv`로만 주입하고 로그에 찍지 않습니다.
- DART 이용약관을 준수하세요(상업적 재배포 제약, 저작권 등).

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `DART_API_KEY not configured` | `.env` 파일 또는 환경변수 누락. |
| `Ambiguous match` | 동명 기업 다수. `--corp-code`로 재시도. |
| `No periodic reports found` | 조회 기간 내 정기보고서 없음. `--report-type any` 확인 또는 기업 공시 주기 확인. |
| `'사업의 내용' section NOT found` | 구형 포맷/요약보고서 등. `raw/` 디렉토리에서 XML 직접 확인. |
| 429 / 500 반복 | 일일 호출 한도 초과 또는 DART 장애. 잠시 후 재시도. |

## 프로젝트 구조

```
dart_scraper/
├── dart_scraper.py          # 메인 모듈 + CLI
├── test_dart_scraper.py     # 단위 테스트
├── fixtures/
│   ├── corpcode_sample.xml
│   ├── list_sample.json
│   └── document_sample.xml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
