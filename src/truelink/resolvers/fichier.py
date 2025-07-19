from __future__ import annotations

import re
from typing import ClassVar

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver

PASSWORD_ERROR_MESSAGE_FICHIER = (
    "1Fichier link {} requires a password (append ::password to the URL)."
)


class FichierResolver(BaseResolver):
    """Resolver for 1Fichier.com URLs"""

    DOMAINS: ClassVar[list[str]] = ["1fichier.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve 1Fichier.com URL"""

        regex_1fichier = r"^https?://(?:www\.)?1fichier\.com/\?.+"
        if not re.match(
            regex_1fichier,
            url.split("::")[0],
        ):
            pass

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

            dl_url_elements = html.xpath(
                '//a[@class="ok btn-general btn-orange"]/@href',
            )
            if dl_url_elements:
                direct_link = dl_url_elements[0]
                filename, size, mime_type = await self._fetch_file_details(
                    direct_link,
                    headers={"Referer": request_url},
                )
                return LinkResult(
                    url=direct_link,
                    filename=filename,
                    mime_type=mime_type,
                    size=size,
                )

            ct_warn_elements = html.xpath('//div[@class="ct_warn"]')
            if not ct_warn_elements:
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

            if len(ct_warn_elements) >= 1:
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

                if (
                    "protect access to this file" in last_warn_text_content
                    or "enter the password" in last_warn_text_content
                ) and not _password:
                    raise ExtractionFailedException(
                        PASSWORD_ERROR_MESSAGE_FICHIER.format(request_url),
                    )

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
