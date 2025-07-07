from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from .exceptions import InvalidURLException, UnsupportedProviderException
from .resolvers import (
    # YandexDiskResolver,
    BuzzHeavierResolver,
    # UploadHavenResolver,
    FuckingFastResolver,
    # MediaFileResolver,
    # MediaFireResolver,
    # DevUploadsResolver,
    LulaCloudResolver,
)

if TYPE_CHECKING:
    from .types import FolderResult, LinkResult


class TrueLinkResolver:
    """Main resolver class for extracting direct download links"""

    def __init__(self):
        self._resolvers: dict[str, type] = {
            # 'yadi.sk': YandexDiskResolver,
            # 'disk.yandex.': YandexDiskResolver,
            "buzzheavier.com": BuzzHeavierResolver,
            # 'devuploads': DevUploadsResolver,
            "lulacloud.com": LulaCloudResolver,
            # 'uploadhaven': UploadHavenResolver,
            "fuckingfast.co": FuckingFastResolver,
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

    async def resolve(self, url: str) -> LinkResult | FolderResult:
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
        async with resolver_instance:
            return await resolver_instance.resolve(url)

    def resolve_sync(self, url: str) -> LinkResult | FolderResult:
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
