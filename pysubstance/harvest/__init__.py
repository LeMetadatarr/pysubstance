"""pysubstance.harvest — the 26 pharma/drug-registry bulk scrapers.

Importing this package imports every scraper module below, which registers
each one with :mod:`harvestkit.engine` (via ``@register``) as a side effect.
Run one from the command line with ``pysubstance-harvest <name>`` (see
:func:`main`), or ``python -m harvestkit <name>`` after importing this
package to populate the registry.
"""
from __future__ import annotations

import sys

from pysubstance.harvest import (
    aemps_drugs,
    anmat_drugs,
    ansm_drugs,
    anvisa_drugs,
    cbg_drugs,
    chembl_drugs,
    codifa_drugs,
    dailymed_names,
    drugbank_open,
    ema_epar,
    fass_drugs,
    fda_ndc,
    fda_orange_book,
    grls_drugs,
    health_canada_drugs,
    isp_drugs,
    kegg_drugs,
    openfda_labels,
    pharmac_drugs,
    pmda_drugs,
    pubchem,
    rxnorm,
    swissmedic_drugs,
    titck_drugs,
    who_atc,
    who_inn,
)

__all__ = [
    "aemps_drugs",
    "anmat_drugs",
    "ansm_drugs",
    "anvisa_drugs",
    "cbg_drugs",
    "chembl_drugs",
    "codifa_drugs",
    "dailymed_names",
    "drugbank_open",
    "ema_epar",
    "fass_drugs",
    "fda_ndc",
    "fda_orange_book",
    "grls_drugs",
    "health_canada_drugs",
    "isp_drugs",
    "kegg_drugs",
    "openfda_labels",
    "pharmac_drugs",
    "pmda_drugs",
    "pubchem",
    "rxnorm",
    "swissmedic_drugs",
    "titck_drugs",
    "who_atc",
    "who_inn",
    "main",
]


def main(argv=None) -> int:
    """Dispatch a registered scraper by name.

        pysubstance-harvest <name> [--output DIR] [--delay S] [--limit N]
        pysubstance-harvest --list

    Every module in this package is already imported (and thus registered)
    by the time this runs, since importing :mod:`pysubstance.harvest` itself
    imports them all.
    """
    from harvestkit.engine import all_sources, get_source, run_cli

    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("--list", "-l", "list"):
        for name in sorted(all_sources()):
            print(name)
        return 0

    name, rest = argv[0], argv[1:]
    try:
        source_cls = get_source(name)
    except KeyError:
        print(f"unknown scraper: {name!r}. Use --list to see available ones.",
              file=sys.stderr)
        return 2
    return run_cli(source_cls, rest)


if __name__ == "__main__":
    raise SystemExit(main())
