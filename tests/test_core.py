from __future__ import annotations

import pytest

from truelink.core import TrueLinkResolver


def test_get_supported_domains() -> None:
    """Test that get_supported_domains returns a list of strings."""
    domains = TrueLinkResolver.get_supported_domains()
    assert isinstance(domains, list)
    assert all(isinstance(domain, str) for domain in domains)


def test_is_supported() -> None:
    """Test that is_supported returns a boolean."""
    assert isinstance(TrueLinkResolver.is_supported("https://www.google.com"), bool)


@pytest.mark.asyncio
async def test_caching() -> None:
    """Test that caching works as expected."""
    resolver = TrueLinkResolver()
    url = "https://www.mediafire.com/file/cw7xsnxna2xfg4k/K4.part7.rar/file"

    # The first time, the URL will be resolved and the result will be cached
    result1 = await resolver.resolve(url, use_cache=True)

    # The second time, the result will be loaded from the cache
    result2 = await resolver.resolve(url, use_cache=True)

    assert result1 is result2
