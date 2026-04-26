"""dart_scraper 보강 호출 헬퍼.

이슈:
1. DART API 가 list 응답에서 pblntf_detail_ty 필드를 안 채워줘 dart_scraper.filter_periodic 가 모두 거름.
2. 정정 보고서([기재정정]/[첨부정정])가 본문 zip 누락으로 BadZipFile 유발.

대응:
- filter_periodic 을 monkey-patch 하여 report_nm 기반으로 분류 + 정정 보고서 제외.
- 산출 파일명을 컨벤션(business.txt, notes.txt) 으로 매핑(심볼릭 링크).
"""
from __future__ import annotations
import json, logging, os, pathlib, re, sys


def main(corp_code: str, outdir: str) -> dict:
    logging.basicConfig(level=logging.WARNING)
    for n in ("urllib3", "urllib3.connectionpool", "requests"):
        logging.getLogger(n).setLevel(logging.WARNING)

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "AgenticCreditUniverse" / "dart_scraper"))
    import dart_scraper as ds

    def patched_filter_periodic(reports):
        keep = []
        for r in list(reports):
            nm = r.report_nm or ""
            # 정정 보고서 제외 (본문 zip 누락 빈번)
            if "[기재정정]" in nm or "[첨부정정]" in nm or "[정정]" in nm:
                continue
            if r.pblntf_detail_ty in ds.PERIODIC_TYPES:
                keep.append(r); continue
            if "사업보고서" in nm:
                r.pblntf_detail_ty = "A001"; keep.append(r)
            elif "반기보고서" in nm:
                r.pblntf_detail_ty = "A002"; keep.append(r)
            elif "분기보고서" in nm:
                m = re.search(r"\((\d{4})\.(\d{2})\)", nm)
                r.pblntf_detail_ty = "A003" if (m and m.group(2) == "03") else "A004"
                keep.append(r)
        return keep
    ds.filter_periodic = patched_filter_periodic

    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)
    result = ds.run(
        api_key=os.environ["DART_API_KEY"],
        name=None, corp_code=corp_code,
        report_type="any", outdir=out,
        prefer="consolidated", interactive=False, force_refresh=False,
    )

    # 컨벤션 매핑: business_section.txt → business.txt
    for src, dst in [("business_section.txt", "business.txt"),
                     ("notes_section.txt", "notes.txt")]:
        s, d = out / src, out / dst
        if s.exists() and not d.exists():
            d.write_bytes(s.read_bytes())
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--corp-code", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    res = main(args.corp_code, args.outdir)
    print(json.dumps({k: res.get(k) for k in ("report_nm","rcept_dt","rcept_no","report_type_name","notes_basis","extraction_failed")}, ensure_ascii=False))
