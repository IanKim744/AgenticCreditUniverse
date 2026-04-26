---
name: excel-merge
description: 신규 종목 코멘트와 등급 정보를 기존 유니버스 엑셀과 머지하여 26.1H 유니버스 엑셀을 생성한다. 사용자 수기 셀(이전 반기 코멘트, 그룹사, 담당자 등)은 보존한다. "엑셀 머지", "유니버스 엑셀 작성", "26.1H 엑셀 채워" 요청 시 사용한다.
---

# Excel Merge

`legacy version/26.1Q 유니버스_작업완료.xlsx` 와 동일한 컬럼 스키마(+신규 3개 추가)로 26.1H 엑셀을 생성한다. 핵심은 **수기 작성 셀 보존**.

## 컬럼 스키마 (18개, 순서 고정)

기존 15개 컬럼 + 신규 3개("AI 판단", "AI 판단 사유", "심사역 최종 판단"):

| idx | 컬럼명 | 자동/수기 | 출처 |
|-----|--------|----------|------|
| 0 | 발행기관 | 키 | master.json |
| 1 | 현업 요청 분류 | 수기 보존 | 사용자 |
| 2 | 26년\n유의업종 | 수기 보존 | 사용자 |
| 3 | 업종 | 수기 보존 | 사용자 |
| 4 | 25.2H 신용등급 | 수기 보존 | 직전 반기 |
| 5 | 25.2H\n등급전망 | 수기 보존 | 직전 반기 |
| 6 | 26.1H 신용등급 | **자동** | grade_input |
| 7 | 26.1H\n등급전망 | **자동** | grade_input |
| 8 | 25.2H 유니버스 | 수기 보존 | 직전 반기 |
| 9 | 26.1H 유니버스 | **자동** | grade_input |
| 10 | 26.1H\n담당 | 수기 보존 | 사용자 |
| 11 | 25.2H 검토 코멘트 | **수기 보존 (절대 덮어쓰지 않음)** | 직전 반기 |
| 12 | 26.1H 검토 코멘트 | **자동** | comments/{company}.json |
| 13 | 26.1H 유니버스 의견변동 | **자동 (수식)** | I열(25.2H) ↔ J열(26.1H) 비교 |
| 14 | 그룹사 | 수기 보존 | 사용자 |
| 15 | AI 판단 | **자동** | judgment/stage2_review.json `decisions[name].final` (O/△/X) |
| 16 | AI 판단 사유 | **자동** | judgment/stage2_review.json `decisions[name].rationale` (wrap_text) |
| 17 | 심사역 최종 판단 | **수기 보존 (절대 덮어쓰지 않음)** | 사용자 |

> 컬럼명에 포함된 줄바꿈(`\n`)은 그대로 유지(openpyxl이 `\n` 포함 헤더를 인식).

## 머지 알고리즘

```python
import openpyxl
from openpyxl import load_workbook
from pathlib import Path
from datetime import datetime
import shutil, json

def merge(source_xlsx, comments_dir, judgment_path, master_path,
          grade_input, output_xlsx):
    # 1. 백업
    bk = Path(f"out/backup/{datetime.now():%Y%m%d_%H%M%S}_{Path(source_xlsx).name}")
    bk.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source_xlsx, bk)

    wb = load_workbook(source_xlsx)
    ws = wb.active

    # 2. 헤더 검증 (18개 컬럼)
    headers = [c.value for c in ws[1]]
    expected = ["발행기관", "현업 요청 분류", "26년\n유의업종", "업종",
                "25.2H 신용등급", "25.2H\n등급전망", "26.1H 신용등급",
                "26.1H\n등급전망", "25.2H 유니버스", "26.1H 유니버스",
                "26.1H\n담당", "25.2H 검토 코멘트", "26.1H 검토 코멘트",
                "26.1H 유니버스 의견변동", "그룹사",
                "AI 판단", "AI 판단 사유", "심사역 최종 판단"]
    if headers[:len(expected)] != expected:
        raise SchemaMismatch(f"컬럼 불일치: {list(zip(headers, expected))}")

    # 3. Stage 2 검수 결과 로딩 (AI 판단 컬럼 채우는 데 필요)
    stage2 = json.loads(Path(judgment_path).read_text(encoding="utf-8"))
    decisions = stage2.get("decisions", {})

    # 4. 발행기관 → row index 매핑
    name_to_row = {}
    for r in range(2, ws.max_row + 1):
        name = ws.cell(r, 1).value
        if name:
            name_to_row.setdefault(name, r)  # 첫 매치만

    # 5. 갱신 + 추가
    report = {"updated": [], "added": [], "missing": [], "conflicts": []}
    rationale_align = Alignment(wrap_text=True, vertical="top", horizontal="left")

    for cmt_file in Path(comments_dir).glob("*.json"):
        rec = json.loads(cmt_file.read_text(encoding="utf-8"))
        name = rec["company"]
        comment = rec["comment"]
        grade = grade_input.get(name, {})
        dec = decisions.get(name, {})
        ai_decision = dec.get("final")    # O/△/X 또는 None
        rationale = dec.get("rationale", "")

        if name in name_to_row:
            r = name_to_row[name]
            # 7개 자동 갱신 컬럼: col 7, 8, 10, 13, 14, 16, 17.
            # col 12(25.2H 코멘트), col 18(심사역 최종 판단)은 절대 덮어쓰지 않음.
            if grade.get("rating"):
                ws.cell(r, 7).value = grade["rating"]
            if grade.get("outlook"):
                ws.cell(r, 8).value = grade["outlook"]
            if grade.get("universe"):
                ws.cell(r, 10).value = grade["universe"]
            ws.cell(r, 13).value = comment
            ws.cell(r, 14).value = opinion_change_formula(r)  # I열↔J열 비교 수식
            if ai_decision:
                ws.cell(r, 16).value = ai_decision
            if rationale:
                cell = ws.cell(r, 17)
                cell.value = rationale
                cell.alignment = rationale_align
            report["updated"].append({"company": name, "row": r})
        else:
            # 신규 행 추가
            new_r = ws.max_row + 1
            ws.cell(new_r, 1).value = name
            if grade.get("rating"):    ws.cell(new_r, 7).value = grade["rating"]
            if grade.get("outlook"):   ws.cell(new_r, 8).value = grade["outlook"]
            if grade.get("universe"):  ws.cell(new_r, 10).value = grade["universe"]
            ws.cell(new_r, 13).value = comment
            ws.cell(new_r, 14).value = opinion_change_formula(new_r)
            if ai_decision:
                ws.cell(new_r, 16).value = ai_decision
            if rationale:
                cell = ws.cell(new_r, 17)
                cell.value = rationale
                cell.alignment = rationale_align
            # 25.2H 컬럼·심사역 최종 판단(18)은 빈 채로 둠
            report["added"].append({"company": name, "row": new_r})

    # 의견변동 수식: 모든 데이터 행에 일괄 (수식이라 중복 적용 안전)
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value:
            ws.cell(r, 14).value = opinion_change_formula(r)

    # 5. 코멘트 누락 종목 표기
    expected_names = set(json.loads(Path(master_path).read_text())["companies"])
    produced_names = {Path(f).stem for f in Path(comments_dir).glob("*.json")}
    for name in expected_names - produced_names:
        report["missing"].append({"company": name, "reason": "comment-writer가 산출 안함"})

    # 6. 저장
    Path(output_xlsx).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_xlsx)
    Path("_workspace/merge/report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
```

## 의견변동 표기 규칙 — 엑셀 수식 (col 14)

정적 값이 아닌 **엑셀 수식**으로 박는다. I열(col 9, 25.2H 유니버스)와 J열(col 10, 26.1H 유니버스)을 비교해 자동 계산. 사용자가 J열 수기 변경 시 자동 갱신.

```python
def opinion_change_formula(r: int) -> str:
    return (
        f'=IF(OR(I{r}="",J{r}=""),"",'
        f'IF(I{r}=J{r},"-",'
        f'IF((IF(J{r}="O",3,IF(J{r}="△",2,IF(J{r}="X",1,0))))>'
        f'(IF(I{r}="O",3,IF(I{r}="△",2,IF(I{r}="X",1,0)))),"▲","▽")))'
    )
```

| 25.2H (I열) | 26.1H (J열) | 표기 |
|-------------|-------------|------|
| 동일 | 동일 | `-` |
| `O` | `△` 또는 `X` | `▽` (하향) |
| `△` | `X` | `▽` |
| `△` | `O` | `▲` (상향) |
| `X` | `△` 또는 `O` | `▲` |
| 한쪽 빈 셀 | — | `""` (빈 셀) |

순위: O=3 > △=2 > X=1. 같으면 "-", J가 더 크면 ▲, 작으면 ▽.

## 보존 규칙 (중요)

- **자동 갱신 대상 7개 컬럼**: col 7(26.1H 등급), col 8(26.1H 전망), col 10(26.1H 유니버스), col 13(26.1H 코멘트), col 14(의견변동 수식), col 16(AI 판단), col 17(AI 판단 사유).
- **절대 덮어쓰지 않는 컬럼**: col 12(25.2H 코멘트), col 18(심사역 최종 판단). 사용자 수기·심사역 검수 영역.
- col 17 셀은 `Alignment(wrap_text=True)` 적용, 컬럼 폭 50.
- 셀 스타일(폰트, 색, 줄바꿈)은 가능한 보존(openpyxl 기본 동작).
- 동일 발행기관 행이 2개 이상이면 첫 행만 갱신, 나머지는 `report.conflicts` 에 기록.

## 환경변수

- 없음. 외부 API 호출 없이 로컬 파일 입출력만.

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| 헤더 스키마 불일치 | 즉시 중단, 사용자에게 차이 보고. 자동 보정 금지 |
| 동일 종목 다중 행 | 첫 행 갱신 + conflicts 기록 |
| comment 파일 손상 | 종목 스킵 + missing에 기록 |
| 출력 디렉토리 권한 부재 | 즉시 중단 |

## 호출 예

```
Agent(universe-merger, model="opus",
      prompt="source_xlsx=AgenticCreditUniverse/legacy version/26.1Q 유니버스_작업완료.xlsx
              comments_dir=_workspace/comments/
              judgment_path=_workspace/judgment/stage2_review.json
              master_path=_workspace/master/master.json
              grade_input=<JSON: {company: {rating, outlook, universe}}>
              output_xlsx=out/26.1H 유니버스.xlsx
              스킬: excel-merge 사용
              보존: 25.2H 컬럼·그룹사·담당·업종·심사역 최종 판단 셀은 절대 덮어쓰지 마라.
              산출: 출력 엑셀 + _workspace/merge/report.json + out/backup/")
```

## 의존성

- `_workspace/comments/{회사}.json` — Stage 1 산출물 (comment-writer)
- `_workspace/judgment/stage2_review.json` — Stage 2 산출물 (judgment-reviewer)
- 기존 엑셀 헤더가 **18개 컬럼** 으로 확장되어 있어야 함 (없으면 SchemaMismatch).
  최초 1회 헤더 확장은 마이그레이션 스크립트(`_workspace/migrate_18cols.py`)가 담당:
  - col 17(심사역 최종 판단)을 col 18로 이동
  - col 17 새 헤더 = "AI 판단 사유"
