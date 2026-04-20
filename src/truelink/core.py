"""Core module for TrueLink."""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
import time
from collections import OrderedDict
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


class _CacheEntry:
    """Cache entry with timestamp for TTL support."""

    __slots__ = ("value", "timestamp")

    def __init__(self, value: LinkResult | FolderResult) -> None:
        self.value = value
        self.timestamp = time.time()


class _LRUCache:
    """LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries in cache
            ttl: Time-to-live in seconds for cache entries

        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()

    def get(self, key: str) -> LinkResult | FolderResult | None:
        """Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired

        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        current_time = time.time()

        # Check if entry has expired
        if current_time - entry.timestamp > self.ttl:
            del self._cache[key]
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return entry.value

    def set(self, key: str, value: LinkResult | FolderResult) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache

        """
        # Remove oldest entry if cache is full
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._cache.popitem(last=False)

        self._cache[key] = _CacheEntry(value)
        self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all entries from cache."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed

        """
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if current_time - entry.timestamp > self.ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


class TrueLinkResolver:
    """Main resolver class for extracting direct download links."""

    _resolvers: ClassVar[dict[str, type]] = {}
    _resolver_instances: ClassVar[dict[str, object]] = {}
    _cache: ClassVar[_LRUCache] = _LRUCache(max_size=1000, ttl=3600)

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        proxy: str | None = None,
        cache_max_size: int = 1000,
        cache_ttl: int = 3600,
    ) -> None:
        """Initialize TrueLinkResolver.

        Args:
            timeout (int): Request timeout in seconds (default: 30)
            max_retries (int): Maximum number of retries for failed attempts (default: 3)
            proxy (str): Proxy URL (optional)
            cache_max_size (int): Maximum number of entries in cache (default: 1000)
            cache_ttl (int): Cache time-to-live in seconds (default: 3600)

        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxy = proxy
        self._cache_max_size = cache_max_size
        self._cache_ttl = cache_ttl
        self._register_resolvers()

    @classmethod
    def _register_resolvers(cls) -> None:
        """Dynamically register resolvers."""
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
        """Register a new resolver."""
        cls._resolvers[domain] = resolver_class

    def _get_resolver(self, url: str) -> object:
        """Get appropriate resolver for URL."""
        domain = urlparse(url).hostname
        if not domain:
            msg = "Invalid URL: No domain found"
            raise InvalidURLException(msg)

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

        msg = f"No resolver found for domain: {domain}"
        raise UnsupportedProviderException(msg)

    async def resolve(
        self, url: str, *, use_cache: bool = False
    ) -> LinkResult | FolderResult:
        """Resolve a URL to direct download link(s) and return as a LinkResult or FolderResult object.

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
        if use_cache:
            cached_result = self._cache.get(url)
            if cached_result is not None:
                return cached_result

        resolver_instance = self._get_resolver(url)

        for attempt in range(self.max_retries):
            try:
                async with resolver_instance:
                    result = await resolver_instance.resolve(url)
                    if use_cache:
                        self._cache.set(url, result)
                    return result
            except ExtractionFailedException:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                if attempt == self.max_retries - 1:
                    msg = f"Failed to resolve URL after {self.max_retries} attempts: {e!s}"
                    raise ExtractionFailedException(msg) from e
                await asyncio.sleep(1 * (attempt + 1))
        return None

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all entries from the cache."""
        cls._cache.clear()

    @classmethod
    def cleanup_cache(cls) -> int:
        """Remove expired entries from the cache.

        Returns:
            Number of entries removed

        """
        return cls._cache.cleanup_expired()

    @staticmethod
    def is_supported(url: str) -> bool:
        """Check if URL is supported.

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

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        """Get list of supported domains.

        Returns:
            List of supported domain patterns

        """
        return list(cls._resolvers.keys())

    @classmethod
    def cleanup_resolver_instances(cls) -> None:
        """Clean up all resolver instances and close their sessions."""
        for instance in cls._resolver_instances.values():
            if hasattr(instance, "session") and instance.session:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(instance.session.close())
                    else:
                        loop.run_until_complete(instance.session.close())
                except Exception:
                    pass
        cls._resolver_instances.clear()
