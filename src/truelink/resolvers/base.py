from __future__ import annotations

import contextlib
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

import aiohttp

if TYPE_CHECKING:
    from truelink.types import FolderResult, LinkResult


class BaseResolver(ABC):
    """Base class for all resolvers"""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()

    async def _create_session(self):
        """Create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": self.USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=30),
            )

    async def _close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request"""
        if not self.session:
            await self._create_session()
        return await self.session.get(url, **kwargs)

    async def _post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
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

    async def _fetch_file_details(
        self,
        url: str,
        custom_headers: dict[str, str] | None = None,
    ) -> tuple[str | None, int | None]:
        """
        Fetch filename and size from URL.
        Uses HEAD request first, then falls back to GET with Range header for size if needed.
        Attempts to extract filename from Content-Disposition or URL.
        Accepts optional custom_headers to be used for the requests.
        """
        filename: str | None = None
        size: int | None = None

        session_created_here = False
        if not self.session:
            await self._create_session()
            session_created_here = True

        if not self.session:
            if session_created_here:
                await self._close_session()
            return None, None

        request_headers = {}
        if custom_headers:
            request_headers.update(custom_headers)

        try:
            async with self.session.head(
                url,
                headers=request_headers,
                allow_redirects=True,
            ) as resp:
                if resp.status == 200:
                    content_disposition = resp.headers.get("Content-Disposition")
                    if content_disposition:
                        match_utf8 = re.search(
                            r"filename\*=UTF-8''([^']+)$",
                            content_disposition,
                            re.IGNORECASE,
                        )
                        if match_utf8:
                            filename = unquote(match_utf8.group(1))
                        else:
                            match_ascii = re.search(
                                r"filename=\"([^\"]+)\"",
                                content_disposition,
                                re.IGNORECASE,
                            )
                            if match_ascii:
                                filename = match_ascii.group(1)

                    if not filename:
                        parsed_url = urlparse(url)
                        if parsed_url.path:
                            path_filename = unquote(parsed_url.path.split("/")[-1])
                            if path_filename:
                                filename = path_filename

                    content_length = resp.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        size = int(content_length)
                        if session_created_here:
                            await self._close_session()
                        return filename, size
        except aiohttp.ClientError:
            pass
        except Exception:
            pass

        try:
            get_range_headers = request_headers.copy()
            get_range_headers["Range"] = "bytes=0-0"
            async with self.session.get(
                url,
                headers=get_range_headers,
                allow_redirects=True,
            ) as resp:
                if resp.status in (200, 206):
                    if not filename:
                        content_disposition = resp.headers.get("Content-Disposition")
                        if content_disposition:
                            match_utf8 = re.search(
                                r"filename\*=UTF-8''([^']+)$",
                                content_disposition,
                                re.IGNORECASE,
                            )
                            if match_utf8:
                                filename = unquote(match_utf8.group(1))
                            else:
                                match_ascii = re.search(
                                    r"filename=\"([^\"]+)\"",
                                    content_disposition,
                                    re.IGNORECASE,
                                )
                                if match_ascii:
                                    filename = match_ascii.group(1)
                        if not filename:
                            parsed_url = urlparse(url)
                            if parsed_url.path:
                                path_filename = unquote(
                                    parsed_url.path.split("/")[-1],
                                )
                                if path_filename:
                                    filename = path_filename

                    content_range = resp.headers.get("Content-Range")
                    if content_range:
                        with contextlib.suppress(ValueError, IndexError):
                            size = int(content_range.split("/")[-1])
        except aiohttp.ClientError:
            pass
        except Exception:
            pass

        finally:
            if session_created_here:
                await self._close_session()

        return filename, size
