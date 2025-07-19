from __future__ import annotations

from typing import ClassVar
from urllib.parse import urlparse

from truelink import mimetypes
from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class RanozResolver(BaseResolver):
    """Resolver for Ranoz.gg URLs"""

    DOMAINS: ClassVar[list[str]] = ["ranoz.gg"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Ranoz.gg URL"""
        try:
            file_id = urlparse(url).path.split("/")[-1]
            api_url = f"https://ranoz.gg/api/v1/files/{file_id}"

            async with await self._get(api_url) as response:
                response.raise_for_status()
                data = (await response.json(content_type=None))["data"]

                file_name = data["filename"]
                file_size = data["size"]
                download_url = f"https://st1.ranoz.gg/{file_id}-{file_name}"

                mime_type, _ = mimetypes.guess_type(file_name)

                return LinkResult(
                    url=download_url,
                    filename=file_name,
                    mime_type=mime_type,
                    size=file_size,
                )

        except Exception as e:
            raise ExtractionFailedException(
                f"Failed to resolve Ranoz URL: {e}"
            ) from e
