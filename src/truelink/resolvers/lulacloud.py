"""Resolver for LulaCloud URLs."""

from __future__ import annotations

from typing import ClassVar

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class LulaCloudResolver(BaseResolver):
    """Resolver for LulaCloud URLs."""

    DOMAINS: ClassVar[list[str]] = ["lulacloud.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve LulaCloud URL."""
        try:
            headers = {"Referer": url}
            async with await self._post(
                url,
                headers=headers,
                allow_redirects=False,
            ) as response:
                location = response.headers.get("location")
                if not location:
                    self._raise_extraction_failed("No redirect location found")

                filename, size, mime_type = await self._fetch_file_details(location)

                return LinkResult(
                    url=location, filename=filename, mime_type=mime_type, size=size
                )

        except ExtractionFailedException as e:
            msg = f"Failed to resolve LulaCloud URL: {e}"
            raise ExtractionFailedException(
                msg,
            ) from e

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)
