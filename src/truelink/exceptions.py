from __future__ import annotations


class TrueLinkException(Exception):
    """Base exception for TrueLink"""


class UnsupportedProviderException(TrueLinkException):
    """Raised when provider is not supported"""


class InvalidURLException(TrueLinkException):
    """Raised when URL is invalid"""


class ExtractionFailedException(TrueLinkException):
    """Raised when link extraction fails"""
