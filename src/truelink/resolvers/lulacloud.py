from __future__ import annotations

from typing import ClassVar

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class LulaCloudResolver(BaseResolver):
    """Resolver for LulaCloud URLs"""

    DOMAINS: ClassVar[list[str]] = ["lulacloud.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve LulaCloud URL"""
        try:
            headers = {"Referer": url}
            async with await self._post(
                url,
                headers=headers,
                allow_redirects=False,
            ) as response:
                location = response.headers.get("location")
                if not location:
                    raise ExtractionFailedException("No redirect location found")

                filename, size, mime_type = await self._fetch_file_details(location)

                return LinkResult(
                    url=location, filename=filename, mime_type=mime_type, size=size
                )

        except Exception as e:
            raise ExtractionFailedException(
                f"Failed to resolve LulaCloud URL: {e}",
            ) from e
