from __future__ import annotations

import re

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver

# Assuming PASSWORD_ERROR_MESSAGE is available, similar to MediaFire
PASSWORD_ERROR_MESSAGE_FICHIER = (
    "1Fichier link {} requires a password (append ::password to the URL)."
)


class FichierResolver(BaseResolver):
    """Resolver for 1Fichier.com URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve 1Fichier.com URL"""

        # Validate URL structure (basic check)
        regex_1fichier = r"^https?://(?:www\.)?1fichier\.com/\?.+"
        if not re.match(
            regex_1fichier,
            url.split("::")[0],
        ):  # Check URL part before password
            # A more common 1fichier link is like https://1fichier.com/?xxxxxxxxxx
            # Or https://1fichier.com/?xxxxxxxxxx&e=123456 (temp links)
            # Or https://username.1fichier.com/fz/doc_id (shared from account) - this regex won't match these
            # For now, sticking to the original regex's scope.
            # Consider broadening if other 1fichier URL patterns are common.
            pass  # Allow proceeding, actual request will determine validity.

        _password = None
        request_url = url
        if "::" in url:
            parts = url.split("::", 1)
            request_url = parts[0]
            _password = parts[1]

        try:
            post_data = {}
            if _password:
                post_data["pass"] = _password

            # POST request to the URL, with password if provided
            async with await self._post(request_url, data=post_data) as response:
                if response.status == 404:
                    raise ExtractionFailedException(
                        "1Fichier error: File not found or the link you entered is wrong (404).",
                    )
                if response.status != 200:
                    raise ExtractionFailedException(
                        f"1Fichier error: Unexpected status code {response.status}.",
                    )
                response_text = await response.text()

            html = fromstring(response_text)

            # Check for direct download button
            dl_url_elements = html.xpath(
                '//a[@class="ok btn-general btn-orange"]/@href',
            )
            if dl_url_elements:
                direct_link = dl_url_elements[0]
                filename, size = await self._fetch_file_details(
                    direct_link,
                    custom_headers={"Referer": request_url},
                )
                return LinkResult(url=direct_link, filename=filename, size=size)

            # If no direct link, check for warning messages
            ct_warn_elements = html.xpath('//div[@class="ct_warn"]')
            if not ct_warn_elements:
                # This case implies the page structure is unexpected if no link and no warning
                if (
                    "In order to access this file, you will have to validate a first download."
                    in response_text
                ):
                    raise ExtractionFailedException(
                        "1Fichier error: Requires a prior validation download (often via browser). Link may be restricted.",
                    )
                raise ExtractionFailedException(
                    "1Fichier error: No download link found and no warning messages. Page structure might have changed.",
                )

            # Analyze warning messages (logic from original script)
            # Number of ct_warn elements can indicate different states

            # This logic for ct_warn is specific and might need adjustment if 1fichier changes layout.
            if len(ct_warn_elements) >= 1:
                # Check the last warning message first for common issues
                last_warn_text_content = (
                    "".join(ct_warn_elements[-1].xpath(".//text()")).lower().strip()
                )

                if "you must wait" in last_warn_text_content:
                    numbers = [
                        int(s) for s in last_warn_text_content.split() if s.isdigit()
                    ]
                    wait_time_msg = (
                        f"Please wait {numbers[0]} minute(s)."
                        if numbers
                        else "Please wait a few minutes/hours."
                    )
                    raise ExtractionFailedException(
                        f"1Fichier error: Download limit reached. {wait_time_msg}",
                    )

                if "bad password" in last_warn_text_content:
                    raise ExtractionFailedException(
                        "1Fichier error: The password you entered is wrong.",
                    )

                if "you have to create a premium account" in last_warn_text_content:
                    raise ExtractionFailedException(
                        "1Fichier error: This link may require a premium account.",
                    )

                # Check for password prompt if password was not provided
                if (
                    "protect access to this file" in last_warn_text_content
                    or "enter the password" in last_warn_text_content
                ) and not _password:
                    raise ExtractionFailedException(
                        PASSWORD_ERROR_MESSAGE_FICHIER.format(request_url),
                    )
                    # If password was provided but still see this, it might be a generic message before password check
                    # or the password check failed and led to a different error handled above.

            # If the logic above didn't catch a specific error, raise a general one.
            # The original script had more complex logic based on len(ct_warn) == 3 or 4.
            # For simplicity, if no download link and warnings exist, assume an issue.
            # Concatenate warning texts for a more informative message.
            all_warnings = " | ".join(
                ["".join(w.xpath(".//text()")).strip() for w in ct_warn_elements],
            )
            raise ExtractionFailedException(
                f"1Fichier error: Could not retrieve download link. Warnings: {all_warnings}",
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve 1Fichier.com URL '{url}': {e!s}",
            ) from e
