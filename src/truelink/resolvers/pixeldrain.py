"""Resolver for PixelDrain URLs."""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import urlparse

import aiohttp

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class PixelDrainResolver(BaseResolver):
    """Resolver for PixelDrain URLs."""

    DOMAINS: ClassVar[list[str]] = ["pixeldrain.com", "pixeldra.in"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve PixelDrain URL."""
        try:
            parsed_url = urlparse(url.rstrip("/"))
            path_parts = parsed_url.path.split("/")

            if not path_parts:
                self._raise_invalid_url("Invalid PixelDrain URL: Empty path.")

            file_or_list_code = path_parts[-1]
            if not file_or_list_code:
                if len(path_parts) > 1:
                    file_or_list_code = path_parts[-2]
                else:
                    self._raise_invalid_url(
                        "Invalid PixelDrain URL: Could not extract ID.",
                    )

            if parsed_url.path.startswith("/l/"):
                self._raise_extraction_failed(
                    "PixelDrain lists (/l/ URLs) are not directly supported by this resolver method."
                    " A list resolver would require iterating items.",
                )

            temp_base_url = "https://pd.cybar.xyz/"
            try:
                async with await self._get(
                    "https://pd.cybar.xyz/",
                    allow_redirects=True,
                ) as base_res:
                    fetched_base = str(base_res.url)
                    if not fetched_base.endswith("/"):
                        fetched_base += "/"
                    temp_base_url = fetched_base
            except aiohttp.ClientError:
                pass

            direct_link = temp_base_url + file_or_list_code

            filename, size, mime_type = await self._fetch_file_details(direct_link)

            return LinkResult(
                url=direct_link, filename=filename, mime_type=mime_type, size=size
            )

        except (ExtractionFailedException, InvalidURLException) as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            msg = f"Failed to resolve PixelDrain URL '{url}': {e!s}"
            raise ExtractionFailedException(
                msg,
            ) from e

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)

    def _raise_invalid_url(self, msg: str) -> None:
        raise InvalidURLException(msg)
