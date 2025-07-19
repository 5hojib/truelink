from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse

from lxml.etree import HTML

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class StreamtapeResolver(BaseResolver):
    """Resolver for Streamtape URLs"""

    DOMAINS: ClassVar[list[str]] = [
        "streamtape.com",
        "streamtape.co",
        "streamtape.cc",
        "streamtape.to",
        "streamtape.net",
        "streamta.pe",
        "streamtape.xyz",
    ]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Streamtape URL"""
        try:
            _id = (
                url.split("/")[4] if len(url.split("/")) >= 6 else url.split("/")[-1]
            )

            async with await self._get(url, allow_redirects=True) as response:
                html_content = await response.text()

            html = HTML(html_content)
            parsed_url = urlparse(url)

            script_elements = html.xpath(
                "//script[contains(text(),'ideoooolink')]/text()"
            ) or html.xpath("//script[contains(text(),'ideoolink')]/text()")

            if script_elements:
                script_content = script_elements[0]
            else:
                scripts = html.xpath("//script/text()")
                script_content = next(
                    (sc for sc in scripts if "get_video" in sc and "expires" in sc),
                    None,
                )
                if not script_content:
                    raise ExtractionFailedException(
                        "Streamtape error: Required script content not found."
                    )

            match = re.findall(r"(&expires\S+?)'", script_content)
            if not match:
                raise ExtractionFailedException(
                    "Streamtape error: Download link parameters not found."
                )

            suffix = match[-1]
            direct_url = f"{parsed_url.scheme}://{parsed_url.netloc}/get_video?id={_id}{suffix}"
            filename, size, mime_type = await self._fetch_file_details(
                direct_url, headers={"Referer": url}
            )

            return LinkResult(
                url=direct_url, filename=filename, mime_type=mime_type, size=size
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Unexpected error while resolving Streamtape URL: {e}"
            ) from e
