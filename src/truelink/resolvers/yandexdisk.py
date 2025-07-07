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
            # Original regex: r"\b(https?://(yadi\.sk|disk\.yandex\.(com|ru))\S+)"
            # We can simplify as the URL passed to resolve should be the Yandex link itself.
            # However, good to ensure it's a valid Yandex link.
            match = re.match(
                r"https?://(yadi\.sk|disk\.yandex\.(?:com|ru))/\S+",
                url,
            )
            if not match:
                # This check might be redundant if TrueLinkResolver already validated domain
                raise InvalidURLException(f"Invalid Yandex.Disk URL format: {url}")

            public_key = (
                url  # The URL itself is often used as the public_key for the API
            )

            api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={public_key}"

            async with await self._get(api_url) as response:
                if response.status != 200:
                    # Attempt to get error message from Yandex API response if available
                    error_detail = "Unknown error"
                    try:
                        json_error = await response.json()
                        error_detail = json_error.get("message", error_detail)
                        if (
                            "description" in json_error
                        ):  # Yandex sometimes uses 'description'
                            error_detail = json_error["description"]
                    except Exception:
                        pass  # Ignore if response is not JSON or parsing fails
                    raise ExtractionFailedException(
                        f"Yandex API error ({response.status}): {error_detail}",
                    )

                json_data = await response.json()

            if "href" not in json_data:
                # This case is covered by the original KeyError catch, but making it more explicit
                error_msg = json_data.get(
                    "message",
                    "Direct download link (href) not found in Yandex API response.",
                )
                if "description" in json_data:
                    error_msg = json_data["description"]
                raise ExtractionFailedException(error_msg)

            direct_link = json_data["href"]

            # Yandex links are often pre-signed and might not have standard Content-Disposition
            # _fetch_file_details might still get size, filename might be harder.
            # The API response might contain 'name' for the file.
            filename = json_data.get("name")
            size = None  # Yandex API for public links doesn't usually give size directly here.
            # _fetch_file_details will try to get it.

            # If filename wasn't in API, _fetch_file_details will try to get it.
            # If it's still None, we can try to derive from the original URL path as a last resort.
            (
                filename_from_details,
                size_from_details,
            ) = await self._fetch_file_details(direct_link)

            if filename_from_details:
                filename = filename_from_details
            if size_from_details is not None:
                size = size_from_details

            if not filename:  # Fallback if API and headers didn't provide filename
                try:
                    parsed_original_url = self.session._prepare_url(url)  # type: ignore
                    [s for s in parsed_original_url.path.split("/") if s]
                    # e.g. https://yadi.sk/i/XXXXXXXXXXXX -> no filename in path
                    # e.g. https://disk.yandex.com/d/YYYYYYYYYY -> no filename in path
                    # Yandex links often don't have filename in the public URL path.
                    # 'name' from API is the best bet.
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
