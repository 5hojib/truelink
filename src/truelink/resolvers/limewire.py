from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from truelink.exceptions import ExtractionFailedException
from truelink.types import LinkResult

from .base import BaseResolver

if TYPE_CHECKING:
    import aiohttp


class LimeWireResolver(BaseResolver):
    """Resolver for limewire.com URLs."""

    DOMAINS: ClassVar[list[str]] = ["limewire.com"]

    async def resolve(self, url: str) -> LinkResult:
        """Resolve limewire.com URL."""
        async with await self._get(url) as response:
            if response.status != 200:
                raise ExtractionFailedException(
                    f"LimeWire: Failed to get response ({response.status})"
                )
            try:
                data = await response.json()
            except Exception as e:
                raise ExtractionFailedException(
                    f"LimeWire: Failed to parse response JSON. {e}"
                ) from e

        if not data.get("success"):
            raise ExtractionFailedException(
                f"LimeWire: API returned an error: {data.get('message', 'Unknown error')}"
            )

        file_url = data.get("link")
        if not file_url:
            raise ExtractionFailedException("LimeWire: No link found in response.")

        filename, size, mime_type = await self._fetch_file_details(file_url)

        return LinkResult(
            url=file_url,
            filename=filename or data.get("name"),
            size=size or data.get("size"),
            mime_type=mime_type or data.get("mimeType"),
        )
