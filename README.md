# pysubstance

26 pharma / drug-registry bulk harvesters — national drug registries, ATC/INN
catalogues, and cross-reference sources — grouped onto the
[harvestkit](https://github.com/LeMetadatarr/harvestkit) resumable-harvest
engine. Extracted from [metadatarr](https://github.com/TigreGotico/metadatarr)'s
scraper collection into its own standalone package.

## Sources

| Scraper | Registry name | Registry |
| --- | --- | --- |
| `aemps_drugs` | `aemps_drugs` | Spain (AEMPS CIMA) |
| `ansm_drugs` | `ansm_drugs` | France (ANSM) |
| `anvisa_drugs` | `anvisa_drugs` | Brazil (ANVISA) |
| `cbg_drugs` | `cbg_drugs` | Netherlands (CBG-MEB) |
| `isp_drugs` | `isp_drugs` | Chile (ISP) |
| `pharmac_drugs` | `pharmac_drugs` | New Zealand (PHARMAC) |
| `anmat_drugs` | `anmat_drugs` | Argentina (ANMAT) |
| `health_canada_drugs` | `health_canada_drugs` | Canada (Health Canada DPD) |
| `swissmedic_drugs` | `swissmedic_drugs` | Switzerland (Swissmedic) |
| `titck_drugs` | `titck_drugs` | Turkey (TITCK) |
| `grls_drugs` | `grls_drugs` | Russia (GRLS) |
| `codifa_drugs` | `codifa_drugs` | Italy (Codifa) |
| `fass_drugs` | `fass_drugs` | Sweden (FASS) |
| `pmda_drugs` | `pmda_drugs` | Japan (PMDA) |
| `openfda_labels` | `openfda_labels` | USA (openFDA drug labels) |
| `fda_ndc` | `fda_ndc` | USA (FDA National Drug Code) |
| `fda_orange_book` | `fda_orange_book` | USA (FDA Orange Book) |
| `ema_epar` | `ema_epar` | EU (EMA EPAR) |
| `who_atc` | `who_atc` | WHO ATC classification |
| `who_inn` | `who_inn` | WHO International Nonproprietary Names |
| `rxnorm` | `rxnorm_drugs` | US NLM RxNorm |
| `dailymed_names` | `dailymed_names` | US NLM DailyMed |
| `chembl_drugs` | `chembl_drugs` | ChEMBL |
| `kegg_drugs` | `kegg_drugs` | KEGG DRUG |
| `drugbank_open` | `drugbank_open` | DrugBank (open data CSV) |
| `pubchem` | `pubchem_compounds` | PubChem |

Plus `pysubstance.unified` — a cross-source joiner that folds all 26 raw
JSONL datasets into one INN-keyed `unified_drugs.jsonl` (ChEMBL as the anchor,
RxNorm/WHO ATC/KEGG/EMA for identifiers, national registries for brand names
and local registration IDs).

## Install

```bash
pip install pysubstance
# or, for the HuggingFace publisher (via harvestkit):
pip install "pysubstance[hf]"
# or, for Cloudflare-guarded sources:
pip install "pysubstance[stealth]"
```

## Usage

```bash
# list every registered scraper
pysubstance-harvest --list

# harvest one source (resumable — safe to Ctrl-C and rerun)
pysubstance-harvest aemps_drugs --output ~/.cache/metadatarr/scrapers/

# fold everything harvested so far into one unified dataset
python -m pysubstance.unified --output ~/.cache/metadatarr/scrapers/
```

Every scraper is a `harvestkit.engine.Source` subclass: checkpoint/dedup/
pagination/throttle are handled by the shared engine, each module only
answers `initial_cursor()` and `fetch(cursor)`. See
[harvestkit](https://github.com/LeMetadatarr/harvestkit) for the full engine
API.

## License

Apache-2.0
