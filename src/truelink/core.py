from __future__ import annotations

import asyncio
import importlib
import pkgutil
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse

from . import resolvers
from .exceptions import (
    ExtractionFailedException,
    InvalidURLException,
    UnsupportedProviderException,
)

if TYPE_CHECKING:
    from .types import FolderResult, LinkResult


class TrueLinkResolver:
    """Main resolver class for extracting direct download links"""

    _resolvers: ClassVar[dict[str, type]] = {}
    _resolver_instances: ClassVar[dict[str, object]] = {}

    def __init__(
        self, timeout: int = 30, max_retries: int = 3, proxy: str | None = None
    ) -> None:
        """Initialize TrueLinkResolver

        Args:
            timeout (int): Request timeout in seconds (default: 30)
            max_retries (int): Maximum number of retries for failed attempts (default: 3)
            proxy (str): Proxy URL (optional)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxy = proxy
        self._register_resolvers()

    @classmethod
    def _register_resolvers(cls) -> None:
        """Dynamically register resolvers"""
        if cls._resolvers:
            return

        package_path = resolvers.__path__
        package_name = resolvers.__name__

        for _, module_name, _ in pkgutil.walk_packages(
            package_path, f"{package_name}."
        ):
            module = importlib.import_module(module_name)
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if (
                    isinstance(attribute, type)
                    and hasattr(attribute, "DOMAINS")
                    and attribute.__name__.endswith("Resolver")
                ):
                    for domain in attribute.DOMAINS:
                        cls.register_resolver(domain, attribute)

    @classmethod
    def register_resolver(cls, domain: str, resolver_class: type) -> None:
        """Register a new resolver"""
        cls._resolvers[domain] = resolver_class

    def _get_resolver(self, url: str) -> object:
        """Get appropriate resolver for URL"""
        domain = urlparse(url).hostname
        if not domain:
            raise InvalidURLException("Invalid URL: No domain found")

        resolver_class = self._resolvers.get(domain)
        if resolver_class:
            if domain not in self._resolver_instances:
                self._resolver_instances[domain] = resolver_class(proxy=self.proxy)
            resolver = self._resolver_instances[domain]
            resolver.timeout = self.timeout
            return resolver

        for pattern, resolver_class in self._resolvers.items():
            if domain.endswith(pattern):
                if pattern not in self._resolver_instances:
                    self._resolver_instances[pattern] = resolver_class(
                        proxy=self.proxy
                    )
                resolver = self._resolver_instances[pattern]
                resolver.timeout = self.timeout
                return resolver

        raise UnsupportedProviderException(f"No resolver found for domain: {domain}")

    _cache: ClassVar[dict[str, LinkResult | FolderResult]] = {}

    async def resolve(
        self, url: str, use_cache: bool = False
    ) -> LinkResult | FolderResult:
        """
        Resolve a URL to direct download link(s) and return as a LinkResult or FolderResult object.

        Args:
            url: The URL to resolve
            use_cache: Whether to use the cache

        Returns:
            A LinkResult or FolderResult object.

        Raises:
            InvalidURLException: If URL is invalid
            UnsupportedProviderException: If provider is not supported
            ExtractionFailedException: If extraction fails after all retries
        """
        if use_cache and url in self._cache:
            return self._cache[url]

        resolver_instance = self._get_resolver(url)

        for attempt in range(self.max_retries):
            try:
                async with resolver_instance:
                    result = await resolver_instance.resolve(url)
                    if use_cache:
                        self._cache[url] = result
                    return result
            except ExtractionFailedException:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise ExtractionFailedException(
                        f"Failed to resolve URL after {self.max_retries} attempts: {e!s}"
                    ) from e
                await asyncio.sleep(1 * (attempt + 1))
        return None

    @staticmethod
    def is_supported(url: str) -> bool:
        """
        Check if URL is supported

        Args:
            url: The URL to check

        Returns:
            True if supported, False otherwise
        """
        domain = urlparse(url).hostname
        if not domain:
            return False

        if domain in TrueLinkResolver._resolvers:
            return True

        return any(
            domain.endswith(pattern) for pattern in TrueLinkResolver._resolvers
        )

    @staticmethod
    def get_supported_domains() -> list:
        """
        Get list of supported domains

        Returns:
            List of supported domain patterns
        """
        return list(TrueLinkResolver._resolvers.keys())
