---
name: master-mapping
description: 발행기관명을 DART corp_code 와 NICE cmpCd 에 매핑하여 master.json을 생성·갱신한다. 신용평가 유니버스의 종목 마스터 관리, 신규 종목 추가, "마스터 매핑/리매핑" 요청 시 사용한다.
---

# Master Mapping

발행기관명을 두 가지 외부 식별자로 매핑한다:
- **DART corp_code** (8자리, DART OpenAPI corpCode.xml 출처)
- **NICE cmpCd** (NICE신용평가 회사 코드)

산출은 `_workspace/master/master.json` (단일 진실 공급원).

## master.json 스키마

```json
{
  "version": "1.0",
  "updated_at": "2026-04-25T11:40:00+09:00",
  "companies": {
    "다우기술": {
      "corp_code": "00139975",
      "cmp_cd": "ABC1234",
      "official_name": "(주)다우기술",
      "aliases": ["다우기술", "Dawootech"],
      "industry": "IT 서비스",
      "group": "다우키움그룹",
      "notes": ""
    }
  }
}
```

`unresolved.json` 은 별도 파일:

```json
{
  "items": [
    {"input_name": "신생바이오", "reason": "DART corpCode 매칭 0건"},
    {"input_name": "Foo Holdings", "reason": "NICE 검색 결과 0건"}
  ]
}
```

## 절차

### 1. DART corp_code 매핑

```python
# 의사코드
import sys, pathlib
sys.path.insert(0, "AgenticCreditUniverse/dart_scraper")
import dart_scraper as ds

# corpCode.xml 캐시 로드 (스크래퍼 자체 24h 캐시 활용)
client = ds.DartClient(api_key=os.environ["DART_API_KEY"])
corps = client.load_corp_codes()  # 또는 ds.get_corp_list()

# 발행기관명으로 매칭
for name in companies:
    matches = ds.match_corp(corps, name)  # 정확 매칭 우선, 없으면 유사도 ≥0.9
    if not matches:
        unresolved.append({"input_name": name, "reason": "DART corpCode 매칭 0건"})
        continue
    if len(matches) > 1:
        # 후보 다중: 사용자에게 선택 요청 또는 가장 시가총액/공시 빈도 높은 것 선택
        ...
    master[name] = {"corp_code": matches[0].corp_code, "official_name": matches[0].corp_name, ...}
```

> **주의**: `dart_scraper` 모듈의 실제 함수명은 코드 확인 후 정확히 호출한다. 모듈 디렉토리 `AgenticCreditUniverse/dart_scraper/` 의 `dart_scraper.py` 를 먼저 Read 하여 사용 가능한 API를 확인.

### 2. NICE cmpCd 매핑

NICE 검색 동작 특징:
- 단일 매칭이면 회사 페이지로 자동 redirect → URL 에 cmpcd 가 박혀 있음
- 다중 매칭이면 결과 페이지가 그대로 반환되며, `nicerating_scraper.resolve_cmpcd()` 는 즉시 ValueError 를 던짐
- 결과 페이지의 후보 항목은 onclick="goView('BOND', cmpcd)" 패턴으로 cmpcd 를 들고 있음 (anchor href 가 아님)

따라서 매핑은 **2단계**로 구성한다:

**Step A — 1차 시도** (단일 매칭이면 끝):
```python
sys.path.insert(0, "AgenticCreditUniverse/nicerating_scraper")
import nicerating_scraper as nrs
scraper = nrs.NiceRatingScraper()
try:
    cmp_cd = scraper.resolve_cmpcd(name)  # 단일 매칭 시 cmpcd 직접 반환
    entry["cmp_cd"] = cmp_cd
except ValueError:
    pass  # Step B 로 폴백
```

**Step B — 다중 매칭 폴백** (헬퍼 사용, `resolve_nice.resolve_cmpcd` 함수):
```python
sys.path.insert(0, ".claude/skills/master-mapping/scripts")
from resolve_nice import resolve_cmpcd as resolve_nice_cmpcd

cmp_cd, candidates = resolve_nice_cmpcd(
    scraper,
    query=name,                          # 부분 매칭용 검색어
    exact_name=entry["official_name"],   # 정확 매칭이 있으면 자동 채택
)
if cmp_cd:
    entry["cmp_cd"] = cmp_cd
else:
    # 정확 매칭 없음 → unresolved 기록 (사용자 확인 필요)
    unresolved.append({
        "input_name": name,
        "reason": f"NICE 다중 후보 (정확 매칭 없음): {candidates[:8]}",
    })
```

**CLI 단독 호출** (검증용):
```bash
$ROOT/.venv/bin/python .claude/skills/master-mapping/scripts/resolve_nice.py \
  --query 에스케이씨 --exact-name "에스케이씨(주)"
# {"cmp_cd": "1783748", "candidates": [...], "candidate_count": 5}
```

### 3. 사용자 입력 보존

- `aliases`: 사용자가 입력한 표기를 항상 보존(나중에 같은 표기로 다시 호출되어도 동일 매핑 유지).
- `group`, `industry`, `notes`: 사용자가 master.json 을 수기 보강할 수 있도록 빈 값으로 초기화.

### 4. 영속

```python
import json, pathlib
out = pathlib.Path("_workspace/master/master.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(master_doc, ensure_ascii=False, indent=2), encoding="utf-8")
```

`unresolved.json` 도 동일 디렉토리에.

## 행동 규칙

1. **정확 매칭 > 유사 매칭 > unresolved.** 자동 보정은 보수적으로.
2. **기존 매핑 보존.** 이미 매핑된 종목의 corp_code/cmp_cd 는 사용자 명시 없이 변경 금지.
3. **백업.** 기존 master.json 갱신 시 `master.json.bak` 으로 직전 본문 백업.
4. **출력 즉시 영속.** 메모리에 들고 다니지 않는다.

## 호출 예 (오케스트레이터에서)

```
Agent(master-curator, model="opus",
      prompt="다음 발행기관들의 master 매핑을 작성하라:
              [다우기술, 롯데물산, 보령, 부산롯데호텔, 씨제이프레시웨이]
              기존 마스터: _workspace/master/master.json (있으면 병합)
              산출: _workspace/master/master.json + unresolved.json
              스킬: master-mapping 사용")
```

## 환경변수

- `DART_API_KEY` 필수.
- NICE 검색은 공개 영역으로 충분(로그인 불필요).
