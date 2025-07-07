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

    COOKIE_FILE = (
        "hxfile.txt"  # Assuming this file is in the current working directory
    )

    def _load_cookies_from_file(self) -> dict[str, str] | None:
        """
        Loads cookies from a Netscape formatted cookie file (hxfile.txt).
        Returns a dictionary of cookie_name: cookie_value.
        """
        if not os.path.isfile(self.COOKIE_FILE):
            # Original code raises an exception here.
            # Depending on strictness, we could return None and let the resolve logic handle it,
            # or raise an exception immediately.
            # For now, matching original: raise if file not found.
            raise ExtractionFailedException(
                f"HxFile error: Cookie file '{self.COOKIE_FILE}' not found.",
            )

        cookies_dict = {}
        try:
            jar = http.cookiejar.MozillaCookieJar(self.COOKIE_FILE)
            jar.load(ignore_discard=True, ignore_expires=True)
            for cookie in jar:
                cookies_dict[cookie.name] = cookie.value
            if not cookies_dict:  # File might be empty or invalid
                # Allow proceeding without cookies if file is empty/invalid but exists?
                # Or raise? Original logic would likely result in failure later if cookies are required.
                # For now, if file exists but no cookies loaded, it's like no cookies.
                return None  # Let the request proceed without specific cookies from file
            return cookies_dict
        except Exception as e:
            # Original code raises generic DirectDownloadLinkException here
            raise ExtractionFailedException(
                f"HxFile error: Failed to load cookies from '{self.COOKIE_FILE}': {e!s}",
            )

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve HxFile.co URL"""

        loaded_cookies = (
            self._load_cookies_from_file()
        )  # This might raise if file not found

        try:
            # Normalize URL: remove .html if present
            normalized_url = url[:-5] if url.strip().endswith(".html") else url

            file_code_match = normalized_url.split("/")
            if not file_code_match:
                raise ExtractionFailedException(
                    "HxFile error: Could not extract file code from URL.",
                )
            file_code = file_code_match[-1]

            post_data = {"op": "download2", "id": file_code}

            # The cookies parameter in aiohttp's post takes a dict
            async with await self._post(
                normalized_url,  # POST to the (potentially normalized) URL
                data=post_data,
                cookies=loaded_cookies,  # Pass loaded cookies here
            ) as response:
                response_text = await response.text()

            html = fromstring(response_text)

            direct_link_elements = html.xpath("//a[@class='btn btn-dow']/@href")
            if not direct_link_elements:
                # Check for common error messages if link not found
                error_message = html.xpath(
                    "//div[contains(@class,'alert-danger')]/text()",
                )
                if error_message:
                    raise ExtractionFailedException(
                        f"HxFile error: {error_message[0].strip()}",
                    )
                # Check for login/premium messages
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

            # Original returned header: ["Referer: {url}"]
            # We'll use this referer for _fetch_file_details
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
