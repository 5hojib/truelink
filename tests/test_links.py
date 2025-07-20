from __future__ import annotations

import pytest

from truelink.core import TrueLinkResolver
from truelink.types import FileItem, FolderResult, LinkResult


@pytest.mark.asyncio
async def test_mediafire_folder() -> None:
    """Test that the mediafire folder link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://www.mediafire.com/folder/abdc8fr8j9nd2/K4"
    result = await resolver.resolve(url)
    assert isinstance(result, FolderResult)
    assert result.title == "K4"
    assert len(result.contents) > 0
    for file in result.contents:
        assert isinstance(file, FileItem)
        assert file.filename is not None
        assert file.url is not None


@pytest.mark.asyncio
@pytest.mark.skip(reason="Mediafire is returning 403")
async def test_mediafire_file() -> None:
    """Test that the mediafire file link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://www.mediafire.com/file/cw7xsnxna2xfg4k/K4.part7.rar/file"
    result = await resolver.resolve(url)
    assert isinstance(result, LinkResult)
    assert result.filename == "K4.part7.rar"
    assert result.url is not None


@pytest.mark.asyncio
async def test_terabox_link() -> None:
    """Test that the terabox link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://terabox.com/s/1vDkjtJWtIOcwr8swIOIBwQ"
    result = await resolver.resolve(url)
    assert isinstance(result, FolderResult)
    assert result.title is not None
    assert len(result.contents) > 0
    for file in result.contents:
        assert isinstance(file, FileItem)
        assert file.filename is not None
        assert file.url is not None
