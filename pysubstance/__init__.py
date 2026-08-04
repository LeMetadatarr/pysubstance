"""pysubstance — pharma/drug-registry bulk harvesters, grouped on harvestkit.

Importing this package imports :mod:`pysubstance.harvest`, which in turn
imports every scraper module so it registers itself with
:mod:`harvestkit.engine` (``@register``).
"""
from pysubstance.version import __version__

import pysubstance.harvest  # noqa: F401  (import for @register side effects)

__all__ = ["__version__"]
