import asyncio
from urllib.parse import urlparse
from typing import Union, Dict, Type

from .exceptions import InvalidURLException, UnsupportedProviderException
from .types import LinkResult, FolderResult
from .resolvers import (
    # YandexDiskResolver,
    # BuzzHeavierResolver,
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
            # 'buzzheavier.com': BuzzHeavierResolver,
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
        Resolve a URL to direct download link(s)
        
        Args:
            url: The URL to resolve
            
        Returns:
            LinkResult for single files, FolderResult for folders
            
        Raises:
            InvalidURLException: If URL is invalid
            UnsupportedProviderException: If provider is not supported
            ExtractionFailedException: If extraction fails
        """
        resolver = self._get_resolver(url)
        return await resolver.resolve(url)
    
    def resolve_sync(self, url: str) -> Union[LinkResult, FolderResult]:
        """
        Synchronous version of resolve()
        
        Args:
            url: The URL to resolve
            
        Returns:
            LinkResult for single files, FolderResult for folders
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
