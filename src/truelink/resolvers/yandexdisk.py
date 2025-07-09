from __future__ import annotations

import re

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class YandexDiskResolver(BaseResolver):
    """Resolver for Yandex.Disk URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Yandex.Disk URL"""
        try:
            match = re.match(
                r"https?://(yadi\.sk|disk\.yandex\.(?:com|ru))/\S+",
                url,
            )
            if not match:
                raise InvalidURLException(f"Invalid Yandex.Disk URL format: {url}")

            public_key = url

            api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={public_key}"

            async with await self._get(api_url) as response:
                if response.status != 200:
                    error_detail = "Unknown error"
                    try:
                        json_error = await response.json()
                        error_detail = json_error.get("message", error_detail)
                        if "description" in json_error:
                            error_detail = json_error["description"]
                    except Exception:
                        pass
                    raise ExtractionFailedException(
                        f"Yandex API error ({response.status}): {error_detail}",
                    )

                json_data = await response.json()

            if "href" not in json_data:
                error_msg = json_data.get(
                    "message",
                    "Direct download link (href) not found in Yandex API response.",
                )
                if "description" in json_data:
                    error_msg = json_data["description"]
                raise ExtractionFailedException(error_msg)

            direct_link = json_data["href"]

            filename = json_data.get("name")
            size = None

            (
                filename_from_details,
                size_from_details,
            ) = await self._fetch_file_details(direct_link)

            if filename_from_details:
                filename = filename_from_details
            if size_from_details is not None:
                size = size_from_details

            if not filename:
                try:
                    parsed_original_url = self.session._prepare_url(url)  # type: ignore
                    [s for s in parsed_original_url.path.split("/") if s]
                except Exception:
                    pass

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            # Original code catches KeyError for missing 'href'
            if isinstance(e, KeyError) and "href" in str(e):
                raise ExtractionFailedException(
                    "Yandex error: File not found or download limit reached (missing 'href').",
                ) from e
            raise ExtractionFailedException(
                f"Failed to resolve Yandex.Disk URL '{url}': {e!s}",
            ) from e
