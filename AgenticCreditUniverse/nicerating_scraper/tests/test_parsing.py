#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline unit / e2e tests for nicerating_scraper v2."""
from __future__ import annotations

import importlib, json, os, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
sys.path.insert(0, str(ROOT))
NS = importlib.import_module("nicerating_scraper")


def _fix(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class TestCompanyInfo(unittest.TestCase):
    def test_samsung_overview(self):
        info = NS.parse_company_info(_fix("company_detail.html"), cmpCd="1326874")
        self.assertEqual(info.cmpNm, "삼성전자(주)")
        self.assertEqual(info.industry, "기타-비금융")
        self.assertEqual(info.affiliate, "삼성")
        self.assertEqual(info.fiscal_month, "12")


class TestMajorFinance(unittest.TestCase):
    def test_cfs_shape(self):
        d = json.loads(_fix("finance_cfs.json"))
        ft = NS.parse_major_finance_json(d, cmpCd="1326874", kind="CFS")
        self.assertEqual(ft.kind_label, "연결")
        self.assertEqual(len(ft.periods), 7)
        accounts = [r["계정명"] for r in ft.indicators]
        for a in ["매출액", "EBITDA", "부채비율(%)", "당기순이익"]:
            self.assertIn(a, accounts)
        sales = next(r for r in ft.indicators if r["계정명"] == "매출액")
        self.assertEqual(sales[ft.periods[-1]], "3,336,059")


class TestFullFinance(unittest.TestCase):
    def test_samsung_full(self):
        d = json.loads(_fix("charge_finance_cfs.json"))
        ft = NS.parse_full_finance_json(d, cmpCd="1326874", kind="CFS")
        self.assertEqual(ft.cmpNm, "삼성전자(주)")
        self.assertEqual(ft.kind_label, "연결")
        self.assertEqual(len(ft.periods), 7)
        self.assertEqual(len(ft.sections["재무상태표(BS)"]), 58)
        self.assertEqual(len(ft.sections["손익계산서(IS)"]), 52)
        self.assertEqual(len(ft.sections["현금흐름표(CF)"]), 47)
        bs = {r["계정명"]: r for r in ft.sections["재무상태표(BS)"]}
        self.assertEqual(bs["자산총계"][ft.periods[-1]], "5,669,421")

    def test_skhynix_full(self):
        d = json.loads(_fix("charge_finance_cfs_skhynix.json"))
        ft = NS.parse_full_finance_json(d, cmpCd="1670352", kind="CFS")
        self.assertEqual(ft.cmpNm, "에스케이하이닉스(주)")
        is_rows = {r["계정명"]: r for r in ft.sections["손익계산서(IS)"]}
        self.assertEqual(is_rows["매출액"][ft.periods[-1]], "971,467")
        self.assertEqual(is_rows["당기순이익"][ft.periods[-1]], "429,479")


MINI_HTML = r"""
<html><body>
<div class="tit_group"><h2>채권</h2></div>
<table>
  <caption>목록</caption>
  <thead><tr>
    <th>회차</th><th>상환순위</th><th>종류</th><th>평정</th>
    <th>현재</th><th>등급결정일(평가일)</th><th>등급확정일</th>
    <th>발행일</th><th>만기일</th><th>발행액(억원)</th>
    <th>채권상세</th><th>의견서</th><th>재무</th><th>보고서</th>
    <th>등급</th><th>전망</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>제224-4회</td><td>선순위</td><td>SB</td><td>정기</td>
      <td>AA+</td><td>안정적</td>
      <td>2026.03.05</td><td>2026.03.05</td>
      <td>2023.02.14</td><td>2033.02.14</td><td>800</td>
      <td><a><img alt="채권"></a></td>
      <td><a href="javascript:fncFileDown('0602f034-8f4b-45e9-bb0e-dad43e69ebb4')"><img alt="의견서"></a></td>
      <td><a><img alt="재무"></a></td><td></td>
    </tr>
    <tr>
      <td>제224-4회</td><td>선순위</td><td>SB</td><td>정기</td>
      <td>AA</td><td>긍정적</td>
      <td>2025.10.30</td><td>2025.10.30</td>
      <td>2023.02.14</td><td>2033.02.14</td><td>800</td>
      <td><a><img alt="채권"></a></td>
      <td><a href="javascript:fncFileDown('dc09551d-bda4-415f-8f1c-7f294ead90e1')"><img alt="의견서"></a></td>
      <td><a><img alt="재무"></a></td><td></td>
    </tr>
  </tbody>
</table>
<div class="tit_group"><h2>기업어음</h2></div>
<table>
  <caption>목록</caption>
  <thead><tr>
    <th>평정</th><th>현재등급</th><th>등급결정일(평가일)</th><th>등급확정일</th>
    <th>유효기간</th><th>의견서</th><th>재무</th><th>보고서</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>정기</td><td>A1</td><td>2025.10.30</td><td>2025.10.30</td>
      <td>2026.06.30</td>
      <td><a href="javascript:fncFileDown('0d392377-4aa2-4ebb-aa32-efcfd43875a9')"><img alt="의견서"></a></td>
      <td></td><td></td>
    </tr>
  </tbody>
</table>
</body></html>"""


class TestRatingParsing(unittest.TestCase):
    def test_parses_and_picks_latest(self):
        ents = NS.parse_ratings_from_html(MINI_HTML)
        self.assertEqual(len(ents), 3)
        pick = NS.pick_latest_rating(ents)
        self.assertIsNotNone(pick)
        self.assertEqual(pick.determined_date, "2026.03.05")
        self.assertEqual(pick.rating_type, "채권")
        self.assertEqual(pick.bond_series, "제224-4회")
        self.assertEqual(pick.bond_kind, "SB")
        self.assertEqual(pick.docId, "0602f034-8f4b-45e9-bb0e-dad43e69ebb4")

    def test_filename_format(self):
        pick = NS.pick_latest_rating(NS.parse_ratings_from_html(MINI_HTML))
        fname = NS._build_pdf_filename("1670352", pick)
        self.assertEqual(fname, "1670352_20260305_제224-4회_SB_AA+.pdf")


class TestLoginGuard(unittest.TestCase):
    def test_login_missing_creds_raises(self):
        for k in (NS.ENV_USER_ID, NS.ENV_USER_PW):
            os.environ.pop(k, None)
        s = NS.NiceRatingScraper(request_delay=0)
        with self.assertRaises(ValueError) as ctx:
            s.login()
        self.assertIn("자격 증명", str(ctx.exception))


class TestCmpcdExtraction(unittest.TestCase):
    def test_from_url(self):
        self.assertEqual(
            NS._extract_cmpcd_from_url("https://x/companyGradeInfo.do?cmpCd=1670352&s=526"),
            "1670352",
        )
    def test_none(self):
        self.assertIsNone(NS._extract_cmpcd_from_url("https://x/foo"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
