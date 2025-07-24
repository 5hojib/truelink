"""Resolver for Yandex.Disk URLs."""

from __future__ import annotations

import re
from typing import ClassVar

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver

YANDEX_DISK_URL_PATTERN = re.compile(
    r"https?://(yadi\.sk|disk\.yandex\.(?:com|ru))/\S+"
)


class YandexDiskResolver(BaseResolver):
    """Resolver for Yandex.Disk URLs."""

    DOMAINS: ClassVar[list[str]] = ["yadi.sk", "disk.yandex."]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Yandex.Disk URL."""
        if not YANDEX_DISK_URL_PATTERN.match(url):
            msg = f"Invalid Yandex.Disk URL format: {url}"
            raise InvalidURLException(msg)

        api_url = (
            "https://cloud-api.yandex.net/v1/disk/public/resources/download"
            f"?public_key={url}"
        )

        try:
            async with await self._get(api_url) as response:
                json_data = await response.json()

                if response.status != 200:
                    error_msg = (
                        json_data.get("description")
                        or json_data.get("message")
                        or "Unknown error"
                    )
                    self._raise_extraction_failed(
                        f"Yandex API error ({response.status}): {error_msg}",
                    )

                direct_link = json_data.get("href")
                if not direct_link:
                    error_msg = (
                        json_data.get("description")
                        or json_data.get("message")
                        or "Direct download link (href) not found in Yandex API response."
                    )
                    self._raise_extraction_failed(error_msg)

            filename, size, mime_type = await self._fetch_file_details(direct_link)
            return LinkResult(
                url=direct_link, filename=filename, mime_type=mime_type, size=size
            )

        except (InvalidURLException, ExtractionFailedException, ValueError) as e:
            if isinstance(e, (InvalidURLException, ExtractionFailedException)):
                raise
            if isinstance(e, KeyError) and "href" in str(e):
                msg = "Yandex error: File not found or download limit reached (missing 'href')."
                raise ExtractionFailedException(msg) from e
            msg = f"Failed to resolve Yandex.Disk URL '{url}': {e!s}"
            raise ExtractionFailedException(msg) from e

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)
