"""Unit tests for dart_scraper.

These tests exercise the pure parsing / extraction logic using fixtures in
./fixtures — no network calls, no API key required.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

import pytest

import dart_scraper as ds


FIXTURES = Path(__file__).parent / "fixtures"


# -----------------------------------------------------------------------------
# corpCode
# -----------------------------------------------------------------------------

def load_corpcode_bytes() -> bytes:
    return (FIXTURES / "corpcode_sample.xml").read_bytes()


def test_parse_corp_codes_count_and_shape():
    corps = ds.parse_corp_codes(load_corpcode_bytes())
    assert len(corps) == 4
    samsung = [c for c in corps if c.corp_code == "00126380"][0]
    assert samsung.corp_name == "삼성전자"
    assert samsung.stock_code == "005930"
    assert samsung.is_listed is True
    unlisted_samsung = [c for c in corps if c.corp_code == "12345678"][0]
    assert unlisted_samsung.is_listed is False


def test_search_corps_prefers_listed():
    corps = ds.parse_corp_codes(load_corpcode_bytes())
    hits = ds.search_corps(corps, "삼성전자")
    assert len(hits) == 2
    # listed corp should come first
    assert hits[0].corp_code == "00126380"
    assert hits[1].corp_code == "12345678"


def test_search_corps_whitespace_and_case_insensitive():
    corps = ds.parse_corp_codes(load_corpcode_bytes())
    # Whitespace / case variations on the English name
    hits = ds.search_corps(corps, "sk hynix")
    assert len(hits) == 1
    assert hits[0].corp_code == "00164779"

    hits2 = ds.search_corps(corps, "  SK하이닉스 ")
    assert len(hits2) == 1
    assert hits2[0].corp_code == "00164779"


def test_search_corps_no_hit():
    corps = ds.parse_corp_codes(load_corpcode_bytes())
    assert ds.search_corps(corps, "존재하지않는기업") == []


def test_extract_corpcode_xml_from_zip():
    # Build a zip with a single CORPCODE.xml member and round-trip.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("CORPCODE.xml", load_corpcode_bytes())
    buf.seek(0)
    xml = ds.extract_corpcode_xml(buf.read())
    corps = ds.parse_corp_codes(xml)
    assert any(c.corp_name == "SK하이닉스" for c in corps)


# -----------------------------------------------------------------------------
# report selection
# -----------------------------------------------------------------------------

def load_list_items() -> list[dict]:
    data = json.loads((FIXTURES / "list_sample.json").read_text(encoding="utf-8"))
    return data["list"]


def test_parse_reports_and_filter_periodic():
    reports = ds.parse_reports(load_list_items())
    # fixture has 4 periodic + 1 non-periodic (major-issue report, B-series)
    assert len(reports) == 5
    periodic = ds.filter_periodic(reports)
    assert len(periodic) == 4
    assert all(r.pblntf_detail_ty in ds.PERIODIC_TYPES for r in periodic)


def test_select_latest_report_any():
    reports = ds.parse_reports(load_list_items())
    picked = ds.select_latest_report(reports, report_type="any")
    assert picked is not None
    # 분기보고서 2024.05.14 is the most recent in fixture
    assert picked.rcept_no == "20240514000123"
    assert picked.pblntf_detail_ty == "A003"


def test_select_latest_report_specific_type():
    reports = ds.parse_reports(load_list_items())
    picked = ds.select_latest_report(reports, report_type="A001")
    assert picked is not None
    assert picked.rcept_no == "20240314000987"  # 사업보고서
    assert picked.pblntf_detail_ty == "A001"


def test_select_latest_report_tiebreak_by_rank():
    # Two periodic reports on the same day -> annual (A001) preferred over Q3 (A004)
    items = [
        {"corp_code": "X", "corp_name": "X", "report_nm": "Q3", "rcept_no": "R-Q3",
         "rcept_dt": "20250315", "pblntf_detail_ty": "A004"},
        {"corp_code": "X", "corp_name": "X", "report_nm": "Annual", "rcept_no": "R-A",
         "rcept_dt": "20250315", "pblntf_detail_ty": "A001"},
    ]
    picked = ds.select_latest_report(ds.parse_reports(items), report_type="any")
    assert picked is not None
    assert picked.rcept_no == "R-A"


def test_select_latest_report_no_candidates():
    items = [
        {"corp_code": "X", "corp_name": "X", "report_nm": "Major",
         "rcept_no": "X", "rcept_dt": "20250101", "pblntf_detail_ty": "B001"},
    ]
    assert ds.select_latest_report(ds.parse_reports(items), report_type="any") is None


# -----------------------------------------------------------------------------
# document extraction
# -----------------------------------------------------------------------------

def load_doc_bytes() -> bytes:
    return (FIXTURES / "document_sample.xml").read_bytes()


def test_find_business_section():
    matches = ds.find_sections_by_title(
        load_doc_bytes(), ds.BUSINESS_SECTION_PATTERN
    )
    assert len(matches) == 1
    # Must be the SECTION-1 wrapper, not the TITLE element itself.
    assert matches[0].tag.upper().startswith("SECTION-")
    text = "".join(matches[0].itertext())
    assert "메모리 반도체" in text


def test_find_consolidated_notes_section():
    matches = ds.find_sections_by_title(
        load_doc_bytes(), ds.CONSOLIDATED_NOTES_PATTERN
    )
    assert len(matches) == 1
    text = "".join(matches[0].itertext())
    assert "연결 기준 주석 본문" in text


def test_find_standalone_notes_with_exclude_filters_out_consolidated():
    # Without exclusion, "연결재무제표 주석" also matches STANDALONE_NOTES_PATTERN.
    all_hits = ds.find_sections_by_title(
        load_doc_bytes(), ds.STANDALONE_NOTES_PATTERN
    )
    assert len(all_hits) == 2

    only_standalone = ds.find_sections_by_title(
        load_doc_bytes(),
        ds.STANDALONE_NOTES_PATTERN,
        exclude=ds.CONSOLIDATED_NOTES_PATTERN,
    )
    assert len(only_standalone) == 1
    text = "".join(only_standalone[0].itertext())
    assert "별도 재무제표 주석 본문" in text


def test_business_section_pattern_matches_roman_prefix():
    assert ds.BUSINESS_SECTION_PATTERN.search("Ⅱ. 사업의 내용")
    assert ds.BUSINESS_SECTION_PATTERN.search("II. 사업의내용")
    assert ds.BUSINESS_SECTION_PATTERN.search("2. 사업의 내용 개요")


def test_consolidated_notes_pattern_variants():
    assert ds.CONSOLIDATED_NOTES_PATTERN.search("연결재무제표 주석")
    assert ds.CONSOLIDATED_NOTES_PATTERN.search("연결재무제표에 대한 주석")
    assert ds.CONSOLIDATED_NOTES_PATTERN.search("5. 연결재무제표에 대한 주석")
    # Plain "재무제표 주석" must NOT match consolidated.
    assert not ds.CONSOLIDATED_NOTES_PATTERN.search("재무제표 주석")


def test_extract_business_section_end_to_end():
    docs = {"document.xml": load_doc_bytes()}
    res = ds.extract_business_section(docs)
    assert res is not None
    name, html, text = res
    assert name == "document.xml"
    assert "메모리 반도체" in text
    assert "<!doctype html>" in html.lower()


def test_extract_notes_prefer_consolidated():
    docs = {"document.xml": load_doc_bytes()}
    res = ds.extract_notes_section(docs, prefer="consolidated")
    assert res is not None
    _, variant, _html, text = res
    assert variant == "consolidated"
    assert "연결 기준 주석 본문" in text


def test_extract_notes_prefer_standalone():
    docs = {"document.xml": load_doc_bytes()}
    res = ds.extract_notes_section(docs, prefer="standalone")
    assert res is not None
    _, variant, _html, text = res
    assert variant == "standalone"
    assert "별도 재무제표 주석 본문" in text


def test_extract_notes_fallback_when_no_consolidated():
    # Build an XML without consolidated notes.
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<DOCUMENT><LIBRARY>
  <SECTION-1><TITLE>Ⅲ. 재무사항</TITLE>
    <SECTION-2><TITLE>3. 재무제표 주석</TITLE><P>주석 본문</P></SECTION-2>
  </SECTION-1>
</LIBRARY></DOCUMENT>"""
    docs = {"d.xml": xml.encode("utf-8")}
    res = ds.extract_notes_section(docs, prefer="consolidated")
    assert res is not None
    _, variant, _html, text = res
    assert variant == "standalone"
    assert "주석 본문" in text


def test_unzip_document_round_trip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc1.xml", b"<a/>")
        zf.writestr("doc2.xml", b"<b/>")
    buf.seek(0)
    out = ds.unzip_document(buf.read())
    assert set(out) == {"doc1.xml", "doc2.xml"}
    assert out["doc1.xml"] == b"<a/>"


# -----------------------------------------------------------------------------
# CLI smoke (just argparse construction — no network)
# -----------------------------------------------------------------------------

def test_cli_parser_requires_name_or_corpcode():
    parser = ds.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_cli_parser_ok_with_name():
    parser = ds.build_parser()
    ns = parser.parse_args(["--name", "삼성전자"])
    assert ns.name == "삼성전자"
    assert ns.report_type == "any"
    assert ns.prefer == "consolidated"
