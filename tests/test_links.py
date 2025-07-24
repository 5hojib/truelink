"""Tests for specific links."""

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
    assert isinstance(result, FolderResult)  # noqa: S101
    assert result.title == "K4"  # noqa: S101
    assert len(result.contents) > 0  # noqa: S101
    for file in result.contents:
        assert isinstance(file, FileItem)  # noqa: S101
        assert file.filename is not None  # noqa: S101
        assert file.url is not None  # noqa: S101


@pytest.mark.asyncio
@pytest.mark.skip(reason="Mediafire is returning 403")
async def test_mediafire_file() -> None:
    """Test that the mediafire file link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://www.mediafire.com/file/cw7xsnxna2xfg4k/K4.part7.rar/file"
    result = await resolver.resolve(url)
    assert isinstance(result, LinkResult)  # noqa: S101
    assert result.filename == "K4.part7.rar"  # noqa: S101
    assert result.url is not None  # noqa: S101


@pytest.mark.asyncio
async def test_terabox_link() -> None:
    """Test that the terabox link resolves correctly."""
    resolver = TrueLinkResolver()
    url = "https://terabox.com/s/1vDkjtJWtIOcwr8swIOIBwQ"
    result = await resolver.resolve(url)
    assert isinstance(result, FolderResult)  # noqa: S101
    assert result.title is not None  # noqa: S101
    assert len(result.contents) > 0  # noqa: S101
    for file in result.contents:
        assert isinstance(file, FileItem)  # noqa: S101
        assert file.filename is not None  # noqa: S101
        assert file.url is not None  # noqa: S101
