"""뉴스/리스크 리포트 생성용 Perplexity 프롬프트.

별도 파일로 분리해 프롬프트 튜닝 시 코드 변경 없이 수정 가능하게 함.
- PROMPT_TEMPLATE: 모든 호출 공통 user 메시지 ({name} 슬롯 치환)
- AGENT_INSTRUCTIONS: --api agent 모드 한정 system instructions
- DEFAULT_DENY_DOMAINS: search_domain_filter denylist (root domain, max 20)
"""

# Perplexity search_domain_filter — 신용평가 컨텍스트와 무관하거나
# 신뢰도가 낮은 root 도메인을 차단(서브도메인 모두 포함).
# naver.com 은 news.naver.com 같은 가치 있는 출처를 함께 잃기 때문에
# root 차단에서 제외 — 클라이언트 표시단(Section5News)에서 noisy 서브도메인만
# 추가 필터링하는 보완안과 짝을 이룸.
DEFAULT_DENY_DOMAINS = [
    "-tistory.com",
    "-youtube.com",
    "-namu.wiki",
    "-catch.co.kr",
    "-jobkorea.co.kr",
    "-saramin.co.kr",
    "-jasoseol.com",
    "-prime-career.com",
    "-teamblind.com",
    "-dcinside.com",
    "-fmkorea.com",
    "-clien.net",
    "-ruliweb.com",
    "-ppomppu.co.kr",
    "-cafe.daum.net",
    "-reddit.com",
    "-quora.com",
]

PROMPT_TEMPLATE = """## 역할 부여
당신은 기업의 잠재적 위험을 발굴하는 전문 '리스크 분석가(Risk Analyst)'입니다.
단순한 뉴스 요약이 아니라, 투자자 관점에서 치명적일 수 있는 법적·재무적 리스크를 검증해야 합니다.

## 필수 수행 지침 (Step-by-Step)

1. [일반 검색]과 [리스크 정밀 검색]을 분리하여 수행하십시오.
   - 일반 검색: 실적, 경영 전략, 신사업 등
   - 리스크 정밀 검색: 아래 키워드를 조합하여 별도로 검색할 것 (단순 뉴스 검색 금지)

2. **리스크 정밀 검색 키워드 (반드시 포함)**
   - 기업명 + 검찰/경찰/금감원/공정위/국세청
   - 기업명 + 압수수색/소환조사/구속영장/고발/과징금
   - 기업명 + 횡령/배임/사기/자본시장법/분식회계/중대재해
   - 오너/경영진 이름 + 리스크/의혹/논란

3. 시계열 균형 유지
   - 가장 최근(1주일 이내) 뉴스뿐만 아니라, 6개월 기간 전체에 걸쳐 발생한 사건의 '진행 경과'를 추적하십시오.

## 출력 양식 (Report Format)
1. **Executive Summary**: 3줄 요약 (호재와 악재의 비중)
2. **Critical Risk (거버넌스/법적 리스크)**:
   - 금융당국/수사기관 조사 현황 (사건명, 진행 단계, 예상 파급력)
   - 주요 소송 및 분쟁 (소송 가액, 승소 가능성, 재무적 영향)
   - *특이사항이 없을 경우 '해당 기간 내 특이사항 없음'으로 명기*

3. **Business & Financials (영업/재무)**:
   - 실적 추이(실적 변동 요인 포함)및 특이사항

4. **Conclusion**: 종합 평가 (투자 주의 등급)

## 분석 대상
- 대상 기업: {name}
"""

AGENT_INSTRUCTIONS = (
    "You have web_search and fetch_url tools. Run MULTIPLE targeted searches: "
    "one set for 일반(실적·전략·신사업), and separate sets for 리스크 정밀 검색 "
    "(검찰/경찰/금감원/공정위/국세청, 압수수색/소환조사/구속영장/고발/과징금, "
    "횡령/배임/사기/자본시장법/분식회계/중대재해, 오너/경영진 이름 + 의혹/논란). "
    "Include Korean-language queries. Cover 최근 6개월 with emphasis on the last 1 week. "
    "Use citations. Respond fully in Korean following the exact Report Format."
)
