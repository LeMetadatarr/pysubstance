# Dataset

## What this repo produces

`pysubstance` harvests pharmaceutical and drug-registry data from 26 public sources. The sources include national drug registries (AEMPS, ANSM, ANVISA, CBG, ISP, PHARMAC, ANMAT, Health Canada, Swissmedic, TITCK, GRLS, Codifa, FASS, PMDA), FDA sources (NDC, Orange Book, openFDA labels), WHO classifications (ATC and INN), RxNorm, DailyMed, ChEMBL, KEGG, DrugBank Open Data, PubChem, and EMA EPAR.

Each harvester writes one JSONL file in the output directory. The package also provides `pysubstance.unified`, which reads the raw JSONL files and builds one normalized file named `unified_drugs.jsonl`. The unified file has one row per International Nonproprietary Name (INN) or active ingredient, joined on ChEMBL as the anchor and enriched with identifiers and brand names from the other sources.

## Dataset format

### Raw harvesters

Each raw harvester emits one row per source record. The exact schema depends on the source. Examples include:

- `chembl_drugs`: `chembl_id`, `pref_name`, `max_phase`, `molecule_type`, `first_approval`, `atc_classifications`, `usan_stem`, `withdrawn_flag`, `synonyms`, `pubchem_cid`, `inchi`, `canonical_smiles`.
- `openfda_labels`: `set_id`, `brand_name`, `generic_name`, `manufacturer_name`, `product_type`, `route`, `substance_name`, `ndc`, `rxcui`, `indications_and_usage`, `warnings`, `boxed_warning`.
- `fda_ndc`: `product_ndc`, `generic_name`, `brand_name`, `labeler_name`, `dosage_form`, `route`, `substance_name`, `marketing_start_date`.
- `who_atc`: `atc_code`, `name`, `ddd`, `uom`, `adm_r`, `level1_code`, `level1_name`, `level2_code`, `level2_name`, `level3_code`, `level3_name`, `level4_code`, `level4_name`.
- `pubchem_compounds`: `cid`, `iupac_name`, `molecular_formula`, `molecular_weight`, `canonical_smiles`, `inchi`, `inchikey`, `charge`, `xlogp`, `exact_mass`, `synonyms`.

Inspect the source module or the JSONL file for the full schema of a given harvester.

### `unified_drugs.jsonl`

One row per INN or active ingredient. Each row is a JSON object with these fields:

| Field | Type | Description |
| --- | --- | --- |
| `inn` | string | Preferred or canonical substance name. |
| `chembl_id` | string or null | ChEMBL molecule identifier. |
| `rxcui` | string or null | RxNorm concept unique identifier. |
| `kegg_id` | string or null | KEGG DRUG identifier. |
| `pubchem_cid` | integer or null | PubChem compound identifier. |
| `atc_codes` | list of strings | WHO ATC codes. |
| `atc_hierarchy` | object or null | Level 1-4 ATC hierarchy names and codes. |
| `max_phase` | integer or null | ChEMBL clinical development phase. |
| `molecule_type` | string or null | ChEMBL molecule type. |
| `first_approval` | integer or null | First approval year when known. |
| `withdrawn` | boolean | Whether ChEMBL marks the drug as withdrawn. |
| `usan_stem` | string or null | USAN stem when available. |
| `molecular_formula` | string or null | Molecular formula from KEGG or ChEMBL. |
| `smiles` | string or null | Canonical SMILES. |
| `inchi` | string or null | Standard InChI. |
| `synonyms` | list of strings | Substance synonyms. |
| `brand_names` | list of strings | Brand names from national registries and FDA sources. |
| `country_ids` | object | Mapping from country code to lists of local registration identifiers. |
| `ipa` | object | Mapping from language code to IPA pronunciations when available. |
| `arpabet` | string or null | ARPABET pronunciation when available. |
| `categories` | list of strings | Psychoactive or therapeutic categories. |
| `tripsit_summary` | string or null | Harm-reduction summary when available. |

## How to generate it

Install the package and harvest the sources you need:

```bash
pip install pysubstance

# example: harvest core identifier sources
pysubstance-harvest chembl_drugs --output ~/.cache/metadatarr/scrapers/
pysubstance-harvest who_atc --output ~/.cache/metadatarr/scrapers/
pysubstance-harvest rxnorm_drugs --output ~/.cache/metadatarr/scrapers/
pysubstance-harvest openfda_labels --output ~/.cache/metadatarr/scrapers/

# then fold all harvested JSONL files into one unified dataset
python -m pysubstance.unified --output ~/.cache/metadatarr/scrapers/
```

The individual harvests are resumable. You can stop any harvester with Ctrl-C and rerun the same command to continue from the last checkpoint.

## Worth publishing on Hugging Face?

Yes. The raw sources are public government and scientific databases. The unified view combines identifiers, structures, classifications, brand names, and country registrations into one normalized dataset that is useful for pharmacovigilance and medical informatics research. Review the terms of each source before redistribution.

## ML tasks served

- Drug-drug interaction prediction.
- Pharmacovigilance signal detection.
- Medical named entity recognition and relation extraction.
- ATC code prediction and drug classification.
- Drug repurposing candidate ranking.
- Medical question answering and entity normalization.
