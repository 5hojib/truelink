from __future__ import annotations

import contextlib
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Self
from urllib.parse import unquote, urlparse

import aiohttp

if TYPE_CHECKING:
    from types import TracebackType

    from truelink.types import FolderResult, LinkResult


class BaseResolver(ABC):
    """Base class for all resolvers"""

    DOMAINS: ClassVar[list[str]] = []
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"

    def __init__(self, proxy: str | None = None) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.proxy = proxy

    async def __aenter__(self) -> Self:
        await self._create_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._close_session()

    async def _create_session(self) -> None:
        """Create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": self.USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=30),
                proxy=self.proxy,
            )

    async def _close_session(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _get(
        self, url: str, **kwargs: dict[str, Any]
    ) -> aiohttp.ClientResponse:
        """Make GET request"""
        if not self.session:
            await self._create_session()
        return await self.session.get(url, **kwargs)

    async def _post(
        self, url: str, **kwargs: dict[str, Any]
    ) -> aiohttp.ClientResponse:
        """Make POST request"""
        if not self.session:
            await self._create_session()
        return await self.session.post(url, **kwargs)

    @abstractmethod
    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """
        Resolve URL to direct download link(s)

        Args:
            url: The URL to resolve

        Returns:
            LinkResult or FolderResult

        Raises:
            ExtractionFailedException: If extraction fails
        """

    def _extract_filename(self, content_disposition: str) -> str | None:
        """Extract filename from Content-Disposition header"""
        match = re.search(
            r"filename\*=UTF-8''([^']+)$", content_disposition, re.IGNORECASE
        )
        if match:
            return unquote(match.group(1))

        match = re.search(
            r"filename=\"([^\"]+)\"", content_disposition, re.IGNORECASE
        )
        if match:
            return match.group(1)

        return None

    def _get_filename_from_url(self, url: str) -> str | None:
        """Extract filename from URL path"""
        parsed_url = urlparse(url)
        if parsed_url.path:
            path_filename = unquote(parsed_url.path.split("/")[-1])
            return path_filename or None
        return None

    async def _fetch_file_details(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> tuple[str | None, int | None, str | None]:
        """
        Fetch filename, size, and mime_type from URL.

        Returns:
            tuple: (filename, size, mime_type)
        """
        filename: str | None = None
        size: int | None = None
        mime_type: str | None = None

        session_created_here = False
        if not self.session:
            await self._create_session()
            session_created_here = True

        if not self.session:
            if session_created_here:
                await self._close_session()
            return None, None, None

        request_headers = headers.copy() if headers else {}

        try:
            async with self.session.head(
                url, headers=request_headers, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    content_disposition = resp.headers.get("Content-Disposition")
                    if content_disposition:
                        filename = self._extract_filename(content_disposition)

                    if not filename:
                        filename = self._get_filename_from_url(url)

                    content_length = resp.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        size = int(content_length)

                    mime_type = (
                        resp.headers.get("Content-Type", "").split(";")[0].strip()
                    )

                    if session_created_here:
                        await self._close_session()
                    return filename, size, mime_type

        except Exception:
            pass

        try:
            range_headers = request_headers.copy()
            range_headers["Range"] = "bytes=0-0"

            async with self.session.get(
                url, headers=range_headers, allow_redirects=True
            ) as resp:
                if resp.status in (200, 206):
                    if not filename:
                        content_disposition = resp.headers.get("Content-Disposition")
                        if content_disposition:
                            filename = self._extract_filename(content_disposition)

                        if not filename:
                            filename = self._get_filename_from_url(url)

                    content_range = resp.headers.get("Content-Range")
                    if content_range:
                        with contextlib.suppress(ValueError, IndexError):
                            size = int(content_range.split("/")[-1])

                    if not mime_type:
                        mime_type = (
                            resp.headers.get("Content-Type", "")
                            .split(";")[0]
                            .strip()
                        )

        except Exception:
            pass

        finally:
            if session_created_here:
                await self._close_session()

        return filename, size, mime_type
