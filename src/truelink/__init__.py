"""TrueLink is a Python library for resolving direct download links from various file hosting services."""

from __future__ import annotations

from .core import TrueLinkResolver
from .exceptions import TrueLinkException, UnsupportedProviderException
from .types import FolderResult, LinkResult

__version__ = "1.4.2-beta"
__all__ = [
    "FolderResult",
    "LinkResult",
    "TrueLinkException",
    "TrueLinkResolver",
    "UnsupportedProviderException",
]
