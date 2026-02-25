"""Config parsers for network device configurations"""

from .base import BaseParser
from .cisco import CiscoIOSParser, CiscoParser

# Temporarily disable HuaweiParser import to avoid blocking the backend
# when Huawei parser code is being refactored. Cisco parsing continues
# to work normally. Once Huawei parser is stable, re‑enable the import
# and add it back to __all__.
try:
    from .huawei import HuaweiParser  # type: ignore
    __all__ = ["BaseParser", "CiscoParser", "CiscoIOSParser", "HuaweiParser"]
except Exception:  # pragma: no cover
    HuaweiParser = None  # type: ignore
    __all__ = ["BaseParser", "CiscoParser", "CiscoIOSParser"]

