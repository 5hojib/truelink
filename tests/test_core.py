from __future__ import annotations

import pytest

from truelink.core import TrueLinkResolver


def test_get_supported_domains() -> None:
    """Test that get_supported_domains returns a list of strings."""
    domains = TrueLinkResolver.get_supported_domains()
    assert isinstance(domains, list)
    assert all(isinstance(domain, str) for domain in domains)


def test_is_supported() -> None:
    """Test that is_supported returns a boolean and works for both supported and unsupported domains."""
    # Test unsupported domain
    assert isinstance(TrueLinkResolver.is_supported("https://www.google.com"), bool)
    assert not TrueLinkResolver.is_supported("https://www.google.com")

    # Test at least one supported domain
    supported_domains = TrueLinkResolver.get_supported_domains()
    if supported_domains:
        # Use the first supported domain to construct a URL
        supported_url = f"https://{supported_domains[0]}"
        assert TrueLinkResolver.is_supported(supported_url)


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
