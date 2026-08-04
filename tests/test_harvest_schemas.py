"""Row-schema equivalence tests for the 26 pharma/drug-registry scrapers.

Relocated verbatim (assertions untouched) from metadatarr's
test_scrapers_migrated.py / test_scrapers_batch3.py / test_scrapers_batch4.py
/ test_scrapers_batch5.py / test_scrapers_batch6.py, keeping only the tests
for scrapers that live in this package, re-pointed at pysubstance.harvest.*.
These lock the exact flat-row shape each scraper emits (the contract the
LeData datasets depend on) against a realistic upstream sample, so a future
engine change can't silently alter the output schema.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from harvestkit.engine import all_sources

from pysubstance.harvest.openfda_labels import OpenFDALabels
from pysubstance.harvest.pubchem import PubChemCompoundsSource
from pysubstance.harvest.who_inn import WhoInnSource, NAME_TYPES
from pysubstance.harvest.chembl_drugs import ChemblDrugsSource
from pysubstance.harvest.dailymed_names import DailyMedNamesSource
from pysubstance.harvest.health_canada_drugs import HealthCanadaDrugsSource
from pysubstance.harvest.rxnorm import RxNormSource, TARGET_TTYS
from pysubstance.harvest.anmat_drugs import AnmatDrugsSource
from pysubstance.harvest.pmda_drugs import PMDADrugsSource, _parse_page
from pysubstance.harvest.codifa_drugs import (
    CodifaDrugsSource,
    _parse_letter_page,
    _parse_detail_page,
)
from pysubstance.harvest.fass_drugs import FassDrugsSource, _parse_letter_page as fass_parse_letter_page
from pysubstance.harvest.titck_drugs import TitckDrugsSource, _parse_workbook as titck_parse_workbook
from pysubstance.harvest.swissmedic_drugs import (
    SwissmedicDrugsSource,
    _parse_workbook as swissmedic_parse_workbook,
    _find_xlsx_url,
    _parse_date,
)
from pysubstance.harvest.who_atc import WhoAtcSource, _parse_child_links, _parse_substance_table
from pysubstance.harvest.grls_drugs import GrlsDrugsSource, _parse_results
from pysubstance.harvest.aemps_drugs import AempsDrugsSource
from pysubstance.harvest.ansm_drugs import AnsmDrugsSource
from pysubstance.harvest.anvisa_drugs import AnvisaDrugsSource
from pysubstance.harvest.cbg_drugs import CbgDrugsSource
from pysubstance.harvest.isp_drugs import IspDrugsSource
from pysubstance.harvest.pharmac_drugs import PharmacDrugsSource, _parse_workbook as pharmac_parse_workbook
from pysubstance.harvest.fda_ndc import FdaNdcSource, _row as fda_ndc_row
from pysubstance.harvest.fda_orange_book import FdaOrangeBookSource, _parse_products
from pysubstance.harvest.ema_epar import EmaEparSource, _parse_xlsx, _map_column, _is_header_row
from pysubstance.harvest.kegg_drugs import (
    KeggDrugsSource,
    _parse_names,
    _parse_kegg_record,
    _split_records,
)
from pysubstance.harvest.drugbank_open import DrugbankOpenSource, _parse_row as drugbank_parse_row


# ---------------------------------------------------------------------------
# openfda_labels  (from test_scrapers_migrated.py)
# ---------------------------------------------------------------------------

def test_openfda_map_row_flattens_openfda_block():
    src = OpenFDALabels()
    rec = {
        "set_id": "abc-123",
        "id": "id-1",
        "effective_time": "20200101",
        "openfda": {
            "brand_name": ["Tylenol"],
            "generic_name": ["acetaminophen"],
            "manufacturer_name": ["J&J"],
            "product_type": ["HUMAN OTC DRUG"],
            "route": ["ORAL"],
            "substance_name": ["ACETAMINOPHEN"],
            "package_ndc": ["50580-449"],
            "rxcui": ["1234"],
            "spl_id": ["spl-1"],
        },
        "indications_and_usage": ["pain", "fever"],
        "warnings": ["do not exceed"],
    }
    row = src.map_row(rec)
    assert row["set_id"] == "abc-123"
    assert row["brand_name"] == "Tylenol"          # _first: list -> scalar
    assert row["generic_name"] == "acetaminophen"
    assert row["route"] == ["ORAL"]                # list fields stay lists
    assert row["ndc"] == ["50580-449"]             # package_ndc -> ndc
    assert row["indications_and_usage"] == "pain fever"  # _join
    assert row["boxed_warning"] == ""              # absent -> ""


def test_openfda_partitions_cover_years_plus_catchall():
    parts = OpenFDALabels().partitions()
    assert len(parts) == (2030 - 1950) + 1
    assert parts[0] == {"search": "effective_time:[19500101+TO+19501231]"}
    assert parts[-1] == {"search": "_missing_:effective_time"}


def test_openfda_registered():
    reg = all_sources()
    assert reg.get("openfda_labels") is OpenFDALabels


# ---------------------------------------------------------------------------
# pubchem / who_inn / chembl_drugs / dailymed_names  (from test_scrapers_batch3.py)
# ---------------------------------------------------------------------------

def test_pubchem_map_row_schema():
    src = PubChemCompoundsSource()
    row = src.map_row(2244, {
        "IUPACName": "aspirin", "MolecularFormula": "C9H8O4", "MolecularWeight": "180.16",
        "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O", "InChI": "InChI=1S/...",
        "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "Charge": 0, "XLogP": 1.2, "ExactMass": "180.042",
    }, ["Aspirin", "Acetylsalicylic acid"])
    assert row["cid"] == 2244
    assert row["iupac_name"] == "aspirin"
    assert row["synonyms"] == ["Aspirin", "Acetylsalicylic acid"]
    assert set(row) == {
        "cid", "iupac_name", "molecular_formula", "molecular_weight", "canonical_smiles",
        "inchi", "inchikey", "charge", "xlogp", "exact_mass", "synonyms",
    }


def test_pubchem_fetch_stops_when_search_empty():
    src = PubChemCompoundsSource()
    src._total_cids_cache = 100
    src._search_cids = lambda retstart, retmax=10000: []
    rows, cursor = src.fetch(0)
    assert rows == []
    assert cursor is None


def test_pubchem_fetch_advances_retstart_and_stops_at_total():
    src = PubChemCompoundsSource()
    src._total_cids_cache = 1
    src._search_cids = lambda retstart, retmax=10000: [2244]
    src._fetch_properties = lambda cids: {}
    src._fetch_synonyms = lambda cids: {}
    rows, cursor = src.fetch(0)
    assert len(rows) == 1
    assert cursor is None


def test_pubchem_registered():
    assert all_sources().get("pubchem_compounds") is PubChemCompoundsSource


def test_who_inn_map_row_schema():
    src = WhoInnSource()
    sub = {
        "_approvalIDDisplay": "R16CO5Y76E",
        "_name": "ASPIRIN",
        "names": [{"name": "Aspirin", "type": "INN", "languages": ["en"]}],
        "codes": [{"code": "50-78-2", "codeSystem": "CAS"}],
        "substanceClass": "chemical",
        "status": "approved",
    }
    row = src.map_row(sub)
    assert row["unii"] == "R16CO5Y76E"
    assert row["names"] == [{"name": "Aspirin", "name_type": "INN", "language": "en"}]
    assert set(row) == {
        "unii", "preferred_name", "names", "codes", "substance_class", "status",
    }


def test_who_inn_fetch_advances_type_when_short_of_total():
    src = WhoInnSource()
    src._get_page = lambda skip, name_type: {"content": [{"_approvalIDDisplay": "X1"}], "total": 1}
    rows, cursor = src.fetch({"type_idx": 0, "skip": 0})
    assert len(rows) == 1
    assert cursor == {"type_idx": 1, "skip": 0}


def test_who_inn_fetch_finishes_after_last_type():
    src = WhoInnSource()
    src._get_page = lambda skip, name_type: {}
    rows, cursor = src.fetch({"type_idx": len(NAME_TYPES) - 1, "skip": 0})
    assert rows == []
    assert cursor is None


def test_who_inn_registered():
    assert all_sources().get("who_inn") is WhoInnSource


def test_chembl_drugs_map_row_schema():
    src = ChemblDrugsSource()
    mol = {
        "molecule_chembl_id": "CHEMBL25",
        "pref_name": "ASPIRIN",
        "max_phase": 4,
        "molecule_type": "Small molecule",
        "molecule_synonyms": [{"synonyms": "Aspirin", "syn_type": "INN"}],
        "cross_references": [{"xref_src": "PubChem", "xref_id": "2244"}],
        "molecule_structures": {"standard_inchi": "InChI=1S/...", "canonical_smiles": "CC(=O)O"},
    }
    row = src.map_row(mol)
    assert row["chembl_id"] == "CHEMBL25"
    assert row["synonyms"] == [{"name": "Aspirin", "syn_type": "INN", "language": "en"}]
    assert row["pubchem_cid"] == 2244
    assert set(row) == {
        "chembl_id", "pref_name", "max_phase", "molecule_type", "first_approval",
        "atc_classifications", "usan_stem", "usan_stem_definition", "oral", "parenteral",
        "topical", "withdrawn_flag", "black_box_warning", "synonyms", "pubchem_cid",
        "inchi", "canonical_smiles",
    }


def test_chembl_drugs_fetch_stops_at_total_count():
    src = ChemblDrugsSource()
    src._get_page = lambda offset: {
        "molecules": [{"molecule_chembl_id": "CHEMBL1"}],
        "page_meta": {"total_count": 1},
    }
    rows, cursor = src.fetch(0)
    assert len(rows) == 1
    assert cursor is None


def test_chembl_drugs_registered():
    assert all_sources().get("chembl_drugs") is ChemblDrugsSource


def test_dailymed_names_stage_names_maps_rows():
    src = DailyMedNamesSource()
    src._get_names_page = lambda page: {
        "data": [{"name_type": "B", "drug_name": "Tylenol"}],
        "metadata": {"total_pages": 1},
    }
    rows, cursor = src.fetch({"stage": "names", "page": 1})
    assert rows == [{"name_type": "B", "drug_name": "Tylenol", "source": "drugnames"}]
    assert cursor == {"stage": "spls", "page": 1}


def test_dailymed_names_stage_spls_maps_rows_and_finishes():
    src = DailyMedNamesSource()
    src._get_spls_page = lambda page: {
        "data": [{"title": "Tylenol 500mg", "setid": "abc", "published_date": "2020-01-01"}],
        "metadata": {"total_pages": 1},
    }
    rows, cursor = src.fetch({"stage": "spls", "page": 1})
    assert rows[0]["name_type"] == "SPL"
    assert rows[0]["setid"] == "abc"
    assert cursor is None


def test_dailymed_names_registered():
    assert all_sources().get("dailymed_names") is DailyMedNamesSource


# ---------------------------------------------------------------------------
# health_canada_drugs / rxnorm / anmat_drugs  (from test_scrapers_batch4.py)
# ---------------------------------------------------------------------------

def test_health_canada_drugs_registered():
    assert all_sources().get("health_canada_drugs") is HealthCanadaDrugsSource


def test_health_canada_drugs_fetch_returns_none_for_none_cursor():
    src = HealthCanadaDrugsSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_health_canada_drugs_parses_tsv_columns(tmp_path):
    import zipfile
    from pysubstance.harvest.health_canada_drugs import _DRUG_COLS, _ING_COLS, _STATUS_COLS

    zip_path = tmp_path / "allfiles.zip"
    drug_row = ",".join(f'"{c}{i}"' for i, c in enumerate(_DRUG_COLS))
    ing_row = ",".join(f'"{c}{i}"' for i, c in enumerate(_ING_COLS))
    # drug_code=drug_code0 for both; strength fields index-matched
    status_row = '"drug_code0","1","APPROVED","2020-01-01","L1"'
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("drug.txt", drug_row + "\n")
        zf.writestr("ingred.txt", ing_row + "\n")
        zf.writestr("status.txt", status_row + "\n")

    src = HealthCanadaDrugsSource()
    src._output_dir = tmp_path
    import pysubstance.harvest.health_canada_drugs as mod
    mod._download_zip = lambda output_dir: zip_path

    rows, cursor = src.fetch(0)
    assert cursor is None
    assert len(rows) == 1
    row = rows[0]
    assert row["drug_code"] == "drug_code0"
    assert row["status"] == "APPROVED"
    assert len(row["active_ingredients"]) == 1
    assert set(row) == {
        "drug_code", "drug_identification_number", "brand_name", "descriptor",
        "class_name", "company_name", "number_of_ais", "last_update_date",
        "status", "active_ingredients",
    }


def test_rxnorm_map_row_schema():
    src = RxNormSource()
    row = src.map_row({"rxcui": "1191", "name": "Aspirin", "tty": "IN"}, ["N02BA01"])
    assert row == {"rxcui": "1191", "name": "Aspirin", "tty": "IN", "atc_codes": ["N02BA01"]}
    assert set(row) == {"rxcui", "name", "tty", "atc_codes"}


def test_rxnorm_fetch_dedups_and_only_fetches_atc_for_ingredients():
    src = RxNormSource()
    src._concepts = [
        {"rxcui": "1", "name": "Aspirin", "tty": "IN"},
        {"rxcui": "2", "name": "Tylenol", "tty": "BN"},
    ]
    src._seen = {"2"}
    atc_calls = []
    src._get_atc = lambda rxcui: atc_calls.append(rxcui) or ["X"]

    rows, cursor = src.fetch(0)
    assert cursor is None
    assert [r["rxcui"] for r in rows] == ["1"]  # rxcui 2 skipped (already seen)
    assert atc_calls == ["1"]  # only the IN-type concept triggers an ATC lookup


def test_rxnorm_all_concepts_dedups_by_rxcui_across_ttys():
    src = RxNormSource()
    calls = {"n": 0}

    def fake_get(path, **params):
        calls["n"] += 1
        tty = params.get("tty")
        return {"minConceptGroup": {"minConcept": [{"rxcui": "1", "name": "A", "tty": tty}]}}

    src._get = fake_get
    concepts = src._all_concepts()
    assert calls["n"] == len(TARGET_TTYS)
    assert len(concepts) == 1  # deduped by rxcui even though every TTY returned rxcui "1"


def test_rxnorm_registered():
    assert all_sources().get("rxnorm_drugs") is RxNormSource


def test_anmat_drugs_map_row_schema():
    src = AnmatDrugsSource()
    row = src.map_row({
        "nombre_comercial": "Aspirineta", "nombre_generico": "Acido acetilsalicilico",
        "laboratorio_titular": "Bayer", "concentracion": "100mg",
        "forma_farmaceutica": "comprimido", "presentacion": "caja x 30",
        "numero_certificado": "12345",
    }, "http://example.com/data.csv")
    assert row == {
        "nombre_comercial": "Aspirineta",
        "nombre_generico": "Acido acetilsalicilico",
        "laboratorio_titular": "Bayer",
        "concentracion": "100mg",
        "forma_farmaceutica": "comprimido",
        "presentacion": "caja x 30",
        "numero_certificado": "12345",
        "language": "es-AR",
        "source_url": "http://example.com/data.csv",
    }
    assert set(row) == {
        "nombre_comercial", "nombre_generico", "laboratorio_titular", "concentracion",
        "forma_farmaceutica", "presentacion", "numero_certificado", "language", "source_url",
    }


def test_anmat_drugs_fetch_none_cursor_is_noop():
    src = AnmatDrugsSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_anmat_drugs_registered():
    assert all_sources().get("anmat_drugs") is AnmatDrugsSource


# ---------------------------------------------------------------------------
# pmda / codifa / fass / titck / swissmedic / who_atc / grls  (from test_scrapers_batch5.py)
# ---------------------------------------------------------------------------

def test_pmda_parse_page_schema():
    html = """
    <table>
      <tr><th>Brand Name</th><th>Non-proprietary Name</th><th>Approved in</th></tr>
      <tr><td>Tylenol</td><td>Acetaminophen</td><td>2020-01</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = _parse_page(soup)
    assert rows == [{
        "brand_name": "Tylenol",
        "nonproprietary_name": "Acetaminophen",
        "approved_in": "2020-01",
        "language": "en",
        "country": "JP",
    }]


def test_pmda_parse_page_skips_tables_without_expected_headers():
    html = "<table><tr><th>foo</th></tr><tr><td>bar</td></tr></table>"
    soup = BeautifulSoup(html, "html.parser")
    assert _parse_page(soup) == []


def test_codifa_parse_letter_page_extracts_slug_and_href():
    html = '<a href="/farmaci/a/aspirina-100mg">Aspirina 100mg</a>'
    rows = _parse_letter_page(html, "a")
    assert rows == [{"brand_name": "Aspirina 100mg", "slug": "aspirina-100mg",
                     "href": "/farmaci/a/aspirina-100mg"}]


def test_codifa_parse_detail_page_dl():
    html = (
        "<dl>"
        "<dt>Principio Attivo</dt><dd>acido acetilsalicilico</dd>"
        "<dt>Classe Terapeutica</dt><dd>antinfiammatori</dd>"
        "<dt>ATC</dt><dd>N02BA01</dd>"
        "<dt>Forma Farmaceutica</dt><dd>compresse</dd>"
        "</dl>"
    )
    detail = _parse_detail_page(html)
    assert detail == {
        "principio_attivo": "acido acetilsalicilico",
        "classe_terapeutica": "antinfiammatori",
        "atc": "N02BA01",
        "forma_farmaceutica": "compresse",
    }


def test_codifa_final_row_merges_listing_and_detail():
    listing = _parse_letter_page(
        '<a href="/farmaci/a/aspirina-100mg">Aspirina 100mg</a>', "a")[0]
    detail = _parse_detail_page("<dl><dt>ATC</dt><dd>N02BA01</dd></dl>")
    row = {
        "brand_name": listing["brand_name"],
        "slug": listing["slug"],
        "href": listing["href"],
        "letter": "a",
        "language": "it",
        "source": "codifa",
        **detail,
    }
    assert row == {
        "brand_name": "Aspirina 100mg",
        "slug": "aspirina-100mg",
        "href": "/farmaci/a/aspirina-100mg",
        "letter": "a",
        "language": "it",
        "source": "codifa",
        "atc": "N02BA01",
    }


def test_fass_parse_letter_page_extracts_npl_id_and_trade_name():
    html = """
    <h2>Alvedon</h2>
    <ul>
      <li><a href="/LIB/product/12345">Tablet 500mg</a></li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    rows = fass_parse_letter_page(soup, seen)
    assert rows == [{
        "trade_name": "Alvedon",
        "dosage_form": "Tablet 500mg",
        "manufacturer": "",
        "npl_id": "12345",
        "product_url": "https://fass.se/LIB/product/12345",
        "language": "sv",
    }]


def test_fass_parse_letter_page_dedups_within_page():
    html = """
    <h2>Alvedon</h2>
    <ul>
      <li><a href="/LIB/product/12345">Tablet</a></li>
      <li><a href="/LIB/product/12345">Tablet</a></li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    rows = fass_parse_letter_page(soup, seen)
    assert len(rows) == 1


def test_titck_parse_workbook_filters_non_aktif(tmp_path):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(3):
        ws.append([None] * 7)  # rows 1-3 are header/junk, data starts row 4
    ws.append(["Parol", "8699000000001", "N02BE01", "Paracetamol", "Firma A", "Normal", "Aktif"])
    ws.append(["Old Drug", "8699000000002", "N02BE02", "Old", "Firma B", "Normal", "Pasif"])

    rows = titck_parse_workbook(ws)
    assert rows == [{
        "ilac_adi": "Parol",
        "barkod": "8699000000001",
        "atc_kodu": "N02BE01",
        "atc_adi": "Paracetamol",
        "firma_adi": "Firma A",
        "recete_turu": "Normal",
        "durumu": "Aktif",
        "language": "tr",
    }]


def test_swissmedic_find_xlsx_url_extracts_link():
    html = '<a href="/dam/foo/zugelassene_arzneimittel_x.xlsx.download.xlsx/x.xlsx">list</a>'
    assert _find_xlsx_url(html) == (
        "https://www.swissmedic.ch/dam/foo/zugelassene_arzneimittel_x.xlsx.download.xlsx/x.xlsx"
    )


def test_swissmedic_find_xlsx_url_falls_back():
    from pysubstance.harvest.swissmedic_drugs import FALLBACK_XLSX_URL
    assert _find_xlsx_url("<html>no links here</html>") == FALLBACK_XLSX_URL


def test_swissmedic_parse_date_handles_datetime_and_string():
    import datetime
    assert _parse_date(None) == ""
    assert _parse_date("2020-01-01") == "2020-01-01"
    assert _parse_date(datetime.date(2020, 1, 1)) == "2020-01-01"


def test_swissmedic_parse_workbook_schema(tmp_path):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(7):
        ws.append([None] * 8)  # rows 1-7 junk/header, data starts row 8 (DATA_START=7, 0-idx)
    ws.append(["12345", None, "Dafalgan", "Bristol-Myers", "N02BE01", None,
               "B", "2020-01-01"])

    rows = swissmedic_parse_workbook(ws)
    assert rows == [{
        "zulassungsnummer": "12345",
        "bezeichnung": "Dafalgan",
        "zulassungsinhaber": "Bristol-Myers",
        "heilmittelcode": "N02BE01",
        "abgabekategorie": "B",
        "erstzulassung": "2020-01-01",
        "language": "de-CH",
    }]


def test_who_atc_parse_child_links_filters_by_code_length():
    html = (
        '<a href="?code=A01">A01 - group</a>'
        '<a href="?code=A02">A02 - other</a>'
        '<a href="?code=A">A - parent</a>'
        '<a href="?code=A01AA">too deep</a>'
        '<a href="?code=A03">Guidelines</a>'
    )
    links = _parse_child_links(html, "A")
    assert links == [("A01", "A01 - group"), ("A02", "A02 - other")]


def test_who_atc_parse_substance_table_schema():
    html = """
    <table>
      <tr><td>ATC code</td><td>Name</td><td>DDD</td><td>U</td><td>Adm.R</td><td>Note</td></tr>
      <tr><td>A01AA01</td><td>sodium fluoride</td><td>1</td><td>mg</td><td>O</td><td></td></tr>
    </table>
    """
    hierarchy = {
        "level1_code": "A", "level1_name": "ALIMENTARY",
        "level2_code": "A01", "level2_name": "STOMATOLOGICAL",
        "level3_code": "A01A", "level3_name": "STOMATOLOGICAL PREP",
        "level4_code": "A01AA", "level4_name": "Caries prophylactic agents",
    }
    rows = _parse_substance_table(html, hierarchy)
    assert rows == [{
        "atc_code": "A01AA01",
        "name": "sodium fluoride",
        "ddd": "1",
        "uom": "mg",
        "adm_r": "O",
        "note": "",
        **hierarchy,
    }]


def test_grls_parse_results_schema():
    html = """
    <table>
      <tr><th>Регистрационный номер</th><th>Торговое наименование</th>
          <th>МНН</th><th>Производитель</th></tr>
      <tr><td>ЛП-000001</td><td>Аспирин</td><td>ацетилсалициловая кислота</td><td>Bayer</td></tr>
    </table>
    """
    rows = _parse_results(html)
    assert rows == [{
        "language": "ru",
        "source": "grls",
        "reg_number": "ЛП-000001",
        "trade_name": "Аспирин",
        "inn_mnn": "ацетилсалициловая кислота",
        "manufacturer": "Bayer",
    }]


def test_all_seven_batch5_scrapers_are_registered():
    reg = all_sources()
    assert reg.get("pmda_drugs") is PMDADrugsSource
    assert reg.get("codifa_drugs") is CodifaDrugsSource
    assert reg.get("fass_drugs") is FassDrugsSource
    assert reg.get("titck_drugs") is TitckDrugsSource
    assert reg.get("swissmedic_drugs") is SwissmedicDrugsSource
    assert reg.get("who_atc") is WhoAtcSource
    assert reg.get("grls_drugs") is GrlsDrugsSource


# ---------------------------------------------------------------------------
# aemps / ansm / anvisa / cbg / isp / pharmac / fda_ndc / fda_orange_book /
# ema_epar / kegg / drugbank  (from test_scrapers_batch6.py)
# ---------------------------------------------------------------------------

def test_aemps_drugs_map_row_schema():
    src = AempsDrugsSource()
    row = src.map_row({
        "nregistro": "12345", "nombre": "Aspirina 100mg",
        "labtitular": "Bayer", "labcomercializador": "Bayer ES",
        "viasAdministracion": [{"nombre": "Oral"}],
        "formaFarmaceutica": {"nombre": "comprimido"},
        "vtm": {"nombre": "aspirin"},
        "dosis": "100mg", "comercializado": True, "receta": False,
        "generico": False, "huerfano": False,
    })
    assert row == {
        "nregistro": "12345",
        "nombre": "Aspirina 100mg",
        "laboratorio_titular": "Bayer",
        "laboratorio_comercializador": "Bayer ES",
        "vias_administracion": ["Oral"],
        "forma_farmaceutica": "comprimido",
        "vtm": "aspirin",
        "dosis": "100mg",
        "comercializado": True,
        "receta": False,
        "generico": False,
        "huerfano": False,
        "language": "es",
        "source": "aemps_cima",
    }


def test_aemps_drugs_fetch_stops_after_total_pages(monkeypatch):
    src = AempsDrugsSource()
    src.throttle.wait = lambda: None

    def fake_get_json(url, params=None):
        return {
            "totalFilas": 3, "tamanioPagina": 2,
            "resultados": [{"nregistro": "1"}, {"nregistro": "2"}]
                          if params["pagina"] == 1 else [{"nregistro": "3"}],
        }

    src.get_json = fake_get_json
    rows, cursor = src.fetch(1)
    assert len(rows) == 2
    assert cursor == 2
    rows2, cursor2 = src.fetch(2)
    assert len(rows2) == 1
    assert cursor2 is None


def test_aemps_drugs_registered():
    assert all_sources().get("aemps_drugs") is AempsDrugsSource


class _FakeAnsmSession:
    def __init__(self, compo_text, spec_text):
        self._urls = {}
        self.compo_text = compo_text
        self.spec_text = spec_text
        self.headers = {}

    def get(self, url, timeout=None, verify=None):
        class _R:
            def __init__(self, content):
                self.content = content

            def raise_for_status(self):
                pass

        if "COMPO" in url:
            return _R(self.compo_text.encode("utf-8"))
        return _R(self.spec_text.encode("utf-8"))


def test_ansm_drugs_fetch_joins_composition_and_speciality(monkeypatch):
    compo = "62012345\tcp\tSUB1\tAcide acetylsalicylique\t500mg\n"
    spec = "62012345\tASPIRINE 500 mg\tcomprime\torale\t1\t\tcommercialisee\t\t\t\ttitulaire A\n"

    import pysubstance.harvest.ansm_drugs as mod
    monkeypatch.setattr(mod.requests, "Session", lambda: _FakeAnsmSession(compo, spec))

    src = AnsmDrugsSource()
    rows, cursor = src.fetch(0)
    assert cursor is None
    assert len(rows) == 1
    row = rows[0]
    assert row["cis_code"] == "62012345"
    assert row["specialite_name"] == "ASPIRINE 500 mg"
    assert row["substances"] == [{"code": "SUB1", "name": "Acide acetylsalicylique", "dosage": "500mg"}]
    assert set(row) == {
        "cis_code", "specialite_name", "dosage_form", "route", "status",
        "commercialisation_status", "holders", "substances", "language", "source",
    }


def test_ansm_drugs_fetch_none_cursor_is_noop():
    src = AnsmDrugsSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_ansm_drugs_registered():
    assert all_sources().get("ansm_drugs") is AnsmDrugsSource


def test_anvisa_drugs_fetch_parses_csv(monkeypatch):
    import pysubstance.harvest.anvisa_drugs as mod

    csv_text = (
        "TIPO_PRODUTO;NOME_PRODUTO;DATA_FINALIZACAO_PROCESSO;CATEGORIA_REGULATORIA;"
        "NUMERO_REGISTRO_PRODUTO;DATA_VENCIMENTO_REGISTRO;NUMERO_PROCESSO;"
        "CLASSE_TERAPEUTICA;EMPRESA_DETENTORA_REGISTRO;SITUACAO_REGISTRO;PRINCIPIO_ATIVO\n"
        '"Generico";"ASPIRINA";"2020-01-01";"Novo";"12345";"2030-01-01";"999";'
        '"Antitermico";"Bayer";"Ativo";"ACIDO ACETILSALICILICO"\n'
    )

    class _FakeResp:
        def raise_for_status(self):
            pass

        def iter_content(self, n):
            yield csv_text.encode("utf-8")

    class _FakeSession:
        headers = {}

        def get(self, url, timeout=None, verify=None, stream=None):
            return _FakeResp()

    monkeypatch.setattr(mod.requests, "Session", lambda: _FakeSession())

    src = AnvisaDrugsSource()
    rows, cursor = src.fetch(0)
    assert cursor is None
    assert len(rows) == 1
    row = rows[0]
    assert row["nome_produto"] == "ASPIRINA"
    assert row["principio_ativo"] == "ACIDO ACETILSALICILICO"
    assert set(row) == {
        "tipo_produto", "nome_produto", "data_finalizacao", "categoria_regulatoria",
        "numero_registro", "data_vencimento", "numero_processo", "classe_terapeutica",
        "empresa_detentora", "situacao", "principio_ativo",
    }


def test_anvisa_drugs_fetch_none_cursor_is_noop():
    src = AnvisaDrugsSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_anvisa_drugs_registered():
    assert all_sources().get("anvisa_drugs") is AnvisaDrugsSource


def test_cbg_drugs_fetch_skips_empty_productnaam(monkeypatch):
    import pysubstance.harvest.cbg_drugs as mod

    csv_text = (
        "REGISTRATIENUMMER|PRODUCTNAAM|INSCHRIJVINGSDATUM|HANDELSVERGUNNINGHOUDER|"
        "AFLEVERSTATUS|FARMACEUTISCHEVORM|ATC|WERKZAMESTOFFEN\n"
        "RVG 12345|Aspirine 100mg|2000-01-01|Bayer BV|UA|tablet|N02BA01|acetylsalicylzuur\n"
        "RVG 99999||2000-01-01|Bayer BV|UA|tablet|N02BA01|acetylsalicylzuur\n"
    )

    class _FakeResp:
        def raise_for_status(self):
            pass

        def iter_content(self, n):
            yield csv_text.encode("utf-8")

    class _FakeSession:
        headers = {}

        def get(self, url, timeout=None, verify=None, stream=None):
            return _FakeResp()

    monkeypatch.setattr(mod.requests, "Session", lambda: _FakeSession())

    src = CbgDrugsSource()
    rows, cursor = src.fetch(0)
    assert cursor is None
    assert len(rows) == 1
    row = rows[0]
    assert row["productnaam"] == "Aspirine 100mg"
    assert row["language"] == "nl"
    assert set(row) == {
        "registratienummer", "productnaam", "inschrijvingsdatum",
        "handelsvergunninghouder", "afleverstatus", "farmaceutischevorm",
        "atc", "werkzamestoffen", "language",
    }


def test_cbg_drugs_registered():
    assert all_sources().get("cbg_drugs") is CbgDrugsSource


def test_isp_drugs_fetch_parses_csv(monkeypatch):
    import pysubstance.harvest.isp_drugs as mod

    csv_text = (
        "N° Registro;Nombre Producto;Razon Social Titular;Condicion Venta\n"
        "F-12345/20;Aspirina 500mg;Bayer Chile;Directa\n"
    )

    class _FakeResp:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    class _FakeSession:
        headers = {}

        def get(self, url, timeout=None, verify=None):
            return _FakeResp(csv_text.encode("utf-8"))

    monkeypatch.setattr(mod.requests, "Session", lambda: _FakeSession())

    src = IspDrugsSource()
    rows, cursor = src.fetch(0)
    assert cursor is None
    assert len(rows) == 1
    row = rows[0]
    assert row["numero_registro"] == "F-12345/20"
    assert row["language"] == "es-CL"
    assert set(row) == {"numero_registro", "nombre_producto", "titular", "condicion_venta", "language"}


def test_isp_drugs_registered():
    assert all_sources().get("isp_drugs") is IspDrugsSource


def test_pharmac_parse_workbook_dedups_by_composite_key():
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(3):
        ws.append([None] * 10)  # rows 1-3 junk/header, data starts row 4 (DATA_START=3, 0-idx)
    ws.append(["Paracetamol", "500mg tab", "Panadol", "1234", "NZ001", 1.5, "$0.00", "", "tab", "Y"])
    ws.append(["Paracetamol", "500mg tab", "Panadol", "1234", "NZ001", 1.5, "$0.00", "", "tab", "Y"])

    rows = pharmac_parse_workbook(ws)
    assert len(rows) == 1
    assert rows[0] == {
        "chemical": "Paracetamol",
        "presentation": "500mg tab",
        "brand": "Panadol",
        "pharmacode": "1234",
        "nzmt_ctpp_id": "NZ001",
        "subsidy": "$0.00",
        "fully_subsidised": "Y",
        "language": "en-NZ",
    }


def test_pharmac_drugs_fetch_none_cursor_is_noop():
    src = PharmacDrugsSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_pharmac_drugs_registered():
    assert all_sources().get("pharmac_drugs") is PharmacDrugsSource


def test_fda_ndc_row_schema():
    row = fda_ndc_row({
        "PRODUCTNDC": "1234-5678", "NONPROPRIETARYNAME": "Acetaminophen",
        "PROPRIETARYNAME": "Tylenol", "PROPRIETARYNAMESUFFIX": "Extra Strength",
        "LABELERNAME": "J&J", "PRODUCTTYPENAME": "HUMAN OTC DRUG",
        "DOSAGEFORMNAME": "TABLET", "ROUTENAME": "ORAL",
        "MARKETINGCATEGORYNAME": "OTC MONOGRAPH", "APPLICATIONNUMBER": "",
        "SUBSTANCENAME": "ACETAMINOPHEN", "ACTIVE_NUMERATOR_STRENGTH": "500",
        "ACTIVE_INGRED_UNIT": "mg/1", "PHARM_CLASSES": "", "DEASCHEDULE": "",
        "MARKETINGSTART": "20200101", "MARKETINGEND": "",
        "LISTING_RECORD_CERTIFIED_THROUGH": "20241231",
    })
    assert row == {
        "product_ndc": "1234-5678",
        "generic_name": "Acetaminophen",
        "brand_name": "Tylenol",
        "brand_name_suffix": "Extra Strength",
        "labeler_name": "J&J",
        "product_type": "HUMAN OTC DRUG",
        "dosage_form": "TABLET",
        "route": ["ORAL"],
        "marketing_category": "OTC MONOGRAPH",
        "application_number": "",
        "substance_name": "ACETAMINOPHEN",
        "active_numerator_strength": "500",
        "active_ingred_unit": "mg/1",
        "pharm_classes": "",
        "deaschedule": "",
        "marketing_start_date": "20200101",
        "marketing_end_date": "",
        "listing_record_certified_through": "20241231",
    }


def test_fda_ndc_row_empty_route_is_empty_list():
    row = fda_ndc_row({"ROUTENAME": ""})
    assert row["route"] == []


def test_fda_ndc_fetch_none_cursor_is_noop():
    src = FdaNdcSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_fda_ndc_registered():
    assert all_sources().get("fda_ndc") is FdaNdcSource


def test_fda_orange_book_parse_products_schema():
    import zipfile
    import io as _io

    buf = _io.BytesIO()
    text = (
        "Ingredient~DF;Route~Trade_Name~Applicant~Strength~Appl_Type~Appl_No~"
        "Product_No~TE_Code~Approval_Date~RLD~RS~Type~Applicant_Full_Name\n"
        "ASPIRIN~TABLET;ORAL~BAYER ASPIRIN~BAYER~325MG~OTC~012345~001~AB~"
        "Approved Prior to Jan 1, 1982~Yes~Yes~RX~Bayer HealthCare LLC\n"
    )
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("products.txt", text)

    rows = list(_parse_products(buf.getvalue()))
    assert rows == [{
        "ingredient": "ASPIRIN",
        "dosage_form": "TABLET",
        "route": "ORAL",
        "trade_name": "BAYER ASPIRIN",
        "applicant": "BAYER",
        "strength": "325MG",
        "appl_type": "OTC",
        "appl_no": "012345",
        "product_no": "001",
        "te_code": "AB",
        "approval_date": "Approved Prior to Jan 1, 1982",
        "rld": "Yes",
        "rs": "Yes",
        "drug_type": "RX",
        "applicant_full_name": "Bayer HealthCare LLC",
    }]


def test_fda_orange_book_fetch_none_cursor_is_noop():
    src = FdaOrangeBookSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_fda_orange_book_registered():
    assert all_sources().get("fda_orange_book") is FdaOrangeBookSource


def test_ema_map_column_matches_by_substring():
    assert _map_column("Medicine name") == "medicine_name"
    assert _map_column("International non-proprietary name (INN) / common name") == "inn_common_name"
    assert _map_column("something unrelated") is None


def test_ema_parse_xlsx_schema():
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Content type: medicine"])
    ws.append([None])
    ws.append(["Medicine name", "Active substance", "Authorisation status", "URL", "Generic"])
    ws.append(["Aspirin", "acetylsalicylic acid", "Authorised", "https://ema/x", "yes"])

    import io as _io
    buf = _io.BytesIO()
    wb.save(buf)

    rows = list(_parse_xlsx(buf.getvalue()))
    assert rows == [{
        "medicine_name": "Aspirin",
        "inn_common_name": "",
        "active_substance": "acetylsalicylic acid",
        "product_number": "",
        "authorisation_status": "Authorised",
        "atc_code": "",
        "therapeutic_area": "",
        "date_of_authorisation": "",
        "generic": "yes",
        "orphan": "",
        "biosimilar": "",
        "url": "https://ema/x",
    }]


def test_ema_epar_fetch_none_cursor_is_noop():
    src = EmaEparSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_ema_epar_registered():
    assert all_sources().get("ema_epar") is EmaEparSource


def test_kegg_parse_names_strips_tags():
    names, tags = _parse_names("Aspirin (JAN/USP/INN); Acetylsalicylic acid (JP18)")
    assert names == ["Aspirin", "Acetylsalicylic acid"]
    assert tags == {"Aspirin": ["JAN/USP/INN"], "Acetylsalicylic acid": ["JP18"]}


def test_kegg_parse_kegg_record_schema():
    text = (
        "ENTRY       D00109                      Drug\n"
        "NAME        Aspirin (JAN/USP/INN);\n"
        "            Acetylsalicylic acid (JP18)\n"
        "FORMULA     C9H8O4\n"
        "CLASS       Analgesic\n"
        "            Antipyretic\n"
    )
    parsed = _parse_kegg_record(text)
    assert parsed["kegg_id"] == "D00109"
    assert parsed["formula"] == "C9H8O4"
    assert parsed["drug_class"] == ["Analgesic", "Antipyretic"]
    assert "Aspirin (JAN/USP/INN);" in parsed["names_block"]


def test_kegg_split_records():
    text = "ENTRY D1\nNAME A\n///\nENTRY D2\nNAME B\n///\n"
    records = _split_records(text)
    assert len(records) == 2
    assert records[0].startswith("ENTRY D1")
    assert records[1].startswith("ENTRY D2")


def test_kegg_drugs_fetch_walks_batches_and_stops():
    src = KeggDrugsSource()
    src.throttle.wait = lambda: None
    src._kegg_ids = ["D00001", "D00002"]
    src._kegg_name_raw = {"D00001": "One (INN)", "D00002": "Two (INN)"}
    src._fetch_batch = lambda ids: (
        "ENTRY       D00001                      Drug\n"
        "NAME        One (INN)\n"
        "FORMULA     C1\n"
        "///\n"
        "ENTRY       D00002                      Drug\n"
        "NAME        Two (INN)\n"
        "FORMULA     C2\n"
        "///\n"
    )
    rows, cursor = src.fetch(0)
    assert cursor is None  # BATCH(10) > len(ids), everything fetched in one page
    assert [r["kegg_id"] for r in rows] == ["D00001", "D00002"]
    assert rows[0]["formula"] == "C1"


def test_kegg_drugs_fetch_falls_back_to_minimal_row_on_empty_response():
    src = KeggDrugsSource()
    src.throttle.wait = lambda: None
    src._kegg_ids = ["D00001"]
    src._kegg_name_raw = {"D00001": "One (INN)"}
    src._fetch_batch = lambda ids: ""
    rows, cursor = src.fetch(0)
    assert rows == [{
        "kegg_id": "D00001", "names": ["One"], "tags": {"One": ["INN"]},
        "formula": "", "drug_class": [], "name_raw": "One (INN)",
    }]
    assert cursor is None


def test_kegg_drugs_fetch_returns_none_past_end():
    src = KeggDrugsSource()
    src._kegg_ids = ["D00001"]
    rows, cursor = src.fetch(5)
    assert rows == []
    assert cursor is None


def test_kegg_drugs_registered():
    assert all_sources().get("kegg_drugs") is KeggDrugsSource


def test_drugbank_parse_row_schema():
    row = drugbank_parse_row({
        "DrugBank ID": "DB00945", "Name": "Aspirin", "CAS Number": "50-78-2",
        "UNII": "R16CO5Y76E", "Synonyms": "Acetylsalicylic acid|ASA",
        "Standard InChI": "InChI=1S/...", "Standard InChI Key": "BSYNRYMUTXBXSQ",
        "SMILES": "CC(=O)OC1=CC=CC=C1C(=O)O", "Formula": "C9H8O4",
        "Groups": "approved; over the counter",
        "ATC Codes": "N02BA01|A01AD05", "Description": "desc",
        "Indication": "indication", "Pharmacodynamics": "pd",
        "Mechanism of Action": "moa", "Food Interactions": "Take with food",
        "Categories": "Analgesics; Antipyretics",
    })
    assert row == {
        "drugbank_id": "DB00945",
        "name": "Aspirin",
        "cas_number": "50-78-2",
        "unii": "R16CO5Y76E",
        "synonyms": ["Acetylsalicylic acid", "ASA"],
        "standard_inchi": "InChI=1S/...",
        "standard_inchi_key": "BSYNRYMUTXBXSQ",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "formula": "C9H8O4",
        "groups": ["approved", "over the counter"],
        "atc_codes": ["N02BA01", "A01AD05"],
        "description": "desc",
        "indication": "indication",
        "pharmacodynamics": "pd",
        "mechanism_of_action": "moa",
        "food_interactions": ["Take with food"],
        "categories": ["Analgesics", "Antipyretics"],
    }


def test_drugbank_open_fetch_reads_csv_path(tmp_path):
    csv_text = "DrugBank ID,Name\nDB00945,Aspirin\n"
    p = tmp_path / "drugbank.csv"
    p.write_text(csv_text, encoding="utf-8")

    src = DrugbankOpenSource()
    src._csv_path = str(p)
    rows, cursor = src.fetch(0)
    assert cursor is None
    assert len(rows) == 1
    assert rows[0]["drugbank_id"] == "DB00945"
    assert rows[0]["name"] == "Aspirin"


def test_drugbank_open_fetch_none_cursor_is_noop():
    src = DrugbankOpenSource()
    rows, cursor = src.fetch(None)
    assert rows == []
    assert cursor is None


def test_drugbank_open_registered():
    assert all_sources().get("drugbank_open") is DrugbankOpenSource


def test_all_26_pysubstance_scrapers_are_registered():
    reg = all_sources()
    expected = {
        "aemps_drugs", "ansm_drugs", "anvisa_drugs", "cbg_drugs", "isp_drugs",
        "pharmac_drugs", "anmat_drugs", "health_canada_drugs", "swissmedic_drugs",
        "titck_drugs", "grls_drugs", "codifa_drugs", "fass_drugs", "pmda_drugs",
        "openfda_labels", "fda_ndc", "fda_orange_book", "ema_epar", "who_atc",
        "who_inn", "rxnorm_drugs", "dailymed_names", "chembl_drugs", "kegg_drugs",
        "drugbank_open", "pubchem_compounds",
    }
    missing = expected - set(reg)
    assert not missing, f"missing from registry: {missing}"
