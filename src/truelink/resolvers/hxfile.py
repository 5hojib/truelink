from __future__ import annotations

import http.cookiejar  # Using this only for parsing, not for session state
import os

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import (  # FolderResult needed for type hint compliance
    FolderResult,
    LinkResult,
)

from .base import BaseResolver


class HxFileResolver(BaseResolver):
    """Resolver for HxFile.co URLs"""

    COOKIE_FILE = "hxfile.txt"

    def _load_cookies_from_file(self) -> dict[str, str] | None:
        """
        Loads cookies from a Netscape formatted cookie file (hxfile.txt).
        Returns a dictionary of cookie_name: cookie_value.
        """
        if not os.path.isfile(self.COOKIE_FILE):
            raise ExtractionFailedException(
                f"HxFile error: Cookie file '{self.COOKIE_FILE}' not found.",
            )

        cookies_dict = {}
        try:
            jar = http.cookiejar.MozillaCookieJar(self.COOKIE_FILE)
            jar.load(ignore_discard=True, ignore_expires=True)
            for cookie in jar:
                cookies_dict[cookie.name] = cookie.value
            if not cookies_dict:
                return None
            return cookies_dict
        except Exception as e:
            raise ExtractionFailedException(
                f"HxFile error: Failed to load cookies from '{self.COOKIE_FILE}': {e!s}",
            )

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve HxFile.co URL"""

        loaded_cookies = self._load_cookies_from_file()

        try:
            normalized_url = url[:-5] if url.strip().endswith(".html") else url

            file_code_match = normalized_url.split("/")
            if not file_code_match:
                raise ExtractionFailedException(
                    "HxFile error: Could not extract file code from URL.",
                )
            file_code = file_code_match[-1]

            post_data = {"op": "download2", "id": file_code}

            async with await self._post(
                normalized_url, data=post_data, cookies=loaded_cookies
            ) as response:
                response_text = await response.text()

            html = fromstring(response_text)

            direct_link_elements = html.xpath("//a[@class='btn btn-dow']/@href")
            if not direct_link_elements:
                error_message = html.xpath(
                    "//div[contains(@class,'alert-danger')]/text()",
                )
                if error_message:
                    raise ExtractionFailedException(
                        f"HxFile error: {error_message[0].strip()}",
                    )
                if (
                    "This link requires a premium account" in response_text
                    or "Login to download" in response_text
                ):
                    raise ExtractionFailedException(
                        "HxFile error: Link may require premium account or login.",
                    )
                raise ExtractionFailedException(
                    "HxFile error: Direct download link not found on page.",
                )

            direct_link = direct_link_elements[0]

            fetch_headers = {"Referer": normalized_url}
            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers=fetch_headers,
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve HxFile.co URL '{url}': {e!s}",
            ) from e
