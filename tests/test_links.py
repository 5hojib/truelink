import pytest
from truelink.core import TrueLinkResolver

@pytest.mark.asyncio
async def test_mediafire_folder():
    """Test that the mediafire folder link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://www.mediafire.com/folder/abdc8fr8j9nd2/K4"
    result = await resolver.resolve(url)
    assert result is not None

@pytest.mark.asyncio
async def test_mediafire_file():
    """Test that the mediafire file link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://www.mediafire.com/file/cw7xsnxna2xfg4k/K4.part7.rar/file"
    result = await resolver.resolve(url)
    assert result is not None

@pytest.mark.asyncio
async def test_terabox_link():
    """Test that the terabox link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://terabox.com/s/1vDkjtJWtIOcwr8swIOIBwQ"
    result = await resolver.resolve(url)
    assert result is not None
