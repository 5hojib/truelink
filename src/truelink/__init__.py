from __future__ import annotations

from .core import TrueLinkResolver
from .exceptions import TrueLinkException, UnsupportedProviderException
from .types import FolderResult, LinkResult

__version__ = "0.0.11"
__all__ = [
    "FolderResult",
    "LinkResult",
    "TrueLinkException",
    "TrueLinkResolver",
    "UnsupportedProviderException",
]
