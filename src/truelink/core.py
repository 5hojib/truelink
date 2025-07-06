import asyncio
import json # Added for JSON output
from dataclasses import asdict # Added for converting dataclass to dict
from urllib.parse import urlparse
from typing import Union, Dict, Type, Any # Added Any for resolve return

from .exceptions import InvalidURLException, UnsupportedProviderException
from .types import LinkResult, FolderResult # These are still used internally by resolvers
from .resolvers import (
    # YandexDiskResolver,
    BuzzHeavierResolver,
    # DevUploadsResolver,
    LulaCloudResolver,
    # UploadHavenResolver,
    FuckingFastResolver,
    # MediaFileResolver,
    # MediaFireResolver,
)

class TrueLinkResolver:
    """Main resolver class for extracting direct download links"""
    
    def __init__(self):
        self._resolvers: Dict[str, Type] = {
            # 'yadi.sk': YandexDiskResolver,
            # 'disk.yandex.': YandexDiskResolver,
            'buzzheavier.com': BuzzHeavierResolver,
            # 'devuploads': DevUploadsResolver,
            'lulacloud.com': LulaCloudResolver,
            # 'uploadhaven': UploadHavenResolver,
            'fuckingfast.co': FuckingFastResolver,
            # 'mediafile.cc': MediaFileResolver,
            # 'mediafire.com': MediaFireResolver,
            # Add more mappings
        }
    
    def _get_resolver(self, url: str):
        """Get appropriate resolver for URL"""
        domain = urlparse(url).hostname
        if not domain:
            raise InvalidURLException("Invalid URL: No domain found")
        
        for pattern, resolver_class in self._resolvers.items():
            if pattern in domain:
                return resolver_class()
        
        raise UnsupportedProviderException(f"No resolver found for domain: {domain}")
    
    async def resolve(self, url: str) -> Union[LinkResult, FolderResult]:
        """
        Resolve a URL to direct download link(s) and return as a LinkResult or FolderResult object.
        
        Args:
            url: The URL to resolve
            
        Returns:
            A LinkResult or FolderResult object.
            
        Raises:
            InvalidURLException: If URL is invalid
            UnsupportedProviderException: If provider is not supported
            ExtractionFailedException: If extraction fails
        """
        resolver_instance = self._get_resolver(url)
        # The resolver_instance.resolve(url) returns a LinkResult or FolderResult object
        result_object = await resolver_instance.resolve(url)

        return result_object
    
    def resolve_sync(self, url: str) -> Union[LinkResult, FolderResult]:
        """
        Synchronous version of resolve()
        
        Args:
            url: The URL to resolve
            
        Returns:
            A LinkResult or FolderResult object.
        """
        return asyncio.run(self.resolve(url))
    
    def is_supported(self, url: str) -> bool:
        """
        Check if URL is supported
        
        Args:
            url: The URL to check
            
        Returns:
            True if supported, False otherwise
        """
        try:
            self._get_resolver(url)
            return True
        except UnsupportedProviderException:
            return False
    
    def get_supported_domains(self) -> list:
        """
        Get list of supported domains
        
        Returns:
            List of supported domain patterns
        """
        return list(self._resolvers.keys())
