from __future__ import annotations

import base64
from urllib.parse import urljoin

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class BerkasDriveResolver(BaseResolver):
    """Resolver for BerkasDrive.com URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve BerkasDrive.com URL"""
        try:
            async with await self._get(url) as response:
                page_html_text = await response.text()

            html = fromstring(page_html_text)

            # Original logic: html.xpath("//script")[0].text.split('"')[1]
            # This is highly specific and assumes:
            # 1. The desired link is in the *first* script tag.
            # 2. The script content, when split by double quotes, has the base64 string as the second element.
            # This can easily break if the page structure or script content changes.

            script_elements = html.xpath(
                "//script/text()",
            )  # Get text content of all script tags
            b64_encoded_link = None

            for script_content in script_elements:
                if not script_content:
                    continue

                # Try to find a base64 string that looks like a URL or part of one after decoding.
                # A common pattern might be `var someLink = "BASE64_HERE";` or similar.
                # The original split('"')[1] suggests it's directly quoted.

                # Attempt to replicate original logic more safely:
                # Find quoted strings within script, check if they are valid base64.
                potential_b64_strings = []
                # Regex to find strings in quotes:
                # - "([^"]+)"
                # - '([^']+)'
                # - `([^`]+)` (template literals, less likely for just b64 data)
                for quote_char in ['"', "'"]:
                    parts = script_content.split(quote_char)
                    if len(parts) > 1:
                        # Add every other part, starting from the second (index 1)
                        potential_b64_strings.extend(parts[1::2])

                for b64_candidate in potential_b64_strings:
                    if (
                        not b64_candidate or len(b64_candidate) < 10
                    ):  # Too short for a meaningful b64 URL
                        continue
                    # Basic check for base64 characters (A-Za-z0-9+/=)
                    # A full check is `base64.b64decode` itself.
                    is_potential_b64 = all(
                        c
                        in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
                        for c in b64_candidate.strip()
                    )
                    if (
                        not is_potential_b64 and len(b64_candidate) % 4 != 0
                    ):  # Length check for padding
                        continue

                    try:
                        # Attempt to decode. If it decodes to something URL-like, use it.
                        decoded_check = base64.b64decode(b64_candidate).decode(
                            "utf-8",
                            errors="ignore",
                        )
                        if (
                            "http://" in decoded_check
                            or "https://" in decoded_check
                            or "/" in decoded_check
                        ):
                            b64_encoded_link = b64_candidate
                            break  # Found a likely candidate
                    except Exception:
                        continue  # Not valid base64 or failed to decode as UTF-8

                if b64_encoded_link:
                    break  # Found in one of the scripts

            if not b64_encoded_link:
                # Check for error messages on page if no link found
                if (
                    "File not found" in page_html_text
                    or "has been deleted" in page_html_text
                ):
                    raise ExtractionFailedException(
                        "BerkasDrive error: File not found or has been deleted.",
                    )
                raise ExtractionFailedException(
                    "BerkasDrive error: Could not find or extract the base64 encoded link from any script tag.",
                )

            try:
                direct_link = base64.b64decode(b64_encoded_link).decode("utf-8")
            except Exception as e_decode:
                raise ExtractionFailedException(
                    f"BerkasDrive error: Failed to decode base64 string '{b64_encoded_link[:30]}...'. Error: {e_decode}",
                ) from e_decode

            # Ensure the link is absolute if it's a path
            if not direct_link.startswith("http"):
                direct_link = urljoin(
                    url,
                    direct_link,
                )  # Use original page URL as base

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve BerkasDrive.com URL '{url}': {e!s}",
            ) from e
