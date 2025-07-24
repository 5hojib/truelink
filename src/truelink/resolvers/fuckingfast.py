"""Resolver for FuckingFast URLs."""

from __future__ import annotations

import re
from typing import ClassVar

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class FuckingFastResolver(BaseResolver):
    """Resolver for FuckingFast URLs."""

    DOMAINS: ClassVar[list[str]] = ["fuckingfast.co"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve FuckingFast URL."""
        try:
            async with await self._get(url) as response:
                content = await response.text()

            pattern = r'window\.open\((["\'])(https://fuckingfast\.co/dl/[^"\']+)\1'
            match = re.search(pattern, content)

            if not match:
                self._raise_extraction_failed("Could not find download link in page")

            download_url = match.group(2)
            filename, size, mime_type = await self._fetch_file_details(download_url)

            return LinkResult(
                url=download_url, filename=filename, mime_type=mime_type, size=size
            )

        except ExtractionFailedException as e:
            msg = f"Failed to resolve FuckingFast URL: {e}"
            raise ExtractionFailedException(
                msg,
            ) from e

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)
