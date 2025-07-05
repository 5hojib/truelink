class TrueLinkException(Exception):
    """Base exception for TrueLink"""
    pass

class UnsupportedProviderException(TrueLinkException):
    """Raised when provider is not supported"""
    pass

class InvalidURLException(TrueLinkException):
    """Raised when URL is invalid"""
    pass

class ExtractionFailedException(TrueLinkException):
    """Raised when link extraction fails"""
    pass
