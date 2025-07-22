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
        "watchadsontape.com",
    ]

    # Use only streamtape.net as fallback domain
    FALLBACK_DOMAIN: ClassVar[str] = "streamtape.net"

    async def _try_with_fallback_domain(self, original_url: str, video_id: str):
        """Try accessing the URL with streamtape.net if the original fails"""
        parsed_url = urlparse(original_url)
        original_domain = parsed_url.netloc
        
        # Try original URL first
        try:
            async with await self._get(original_url, allow_redirects=True) as response:
                if response.status == 200:
                    html_content = await response.text()
                    return html_content, parsed_url
        except Exception:
            pass  # Continue to fallback
        
        # If original fails and it's not already streamtape.net, try with streamtape.net
        if original_domain != self.FALLBACK_DOMAIN:
            fallback_url = original_url.replace(original_domain, self.FALLBACK_DOMAIN)
            try:
                async with await self._get(fallback_url, allow_redirects=True) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        return html_content, urlparse(fallback_url)
            except Exception as e:
                raise ExtractionFailedException(
                    f"Both original domain and {self.FALLBACK_DOMAIN} failed"
                ) from e
        
        raise ExtractionFailedException(
            "Failed to access URL with both original and fallback domains"
        )

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Streamtape URL"""
        try:
            _id = (
                url.split("/")[4] if len(url.split("/")) >= 6 else url.split("/")[-1]
            )

            # Try with fallback domain if original fails
            html_content, parsed_url = await self._try_with_fallback_domain(url, _id)
            html = HTML(html_content)

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
            # Use the working domain for the direct URL
            direct_url = f"{parsed_url.scheme}://{parsed_url.netloc}/get_video?id={_id}{suffix}"
            
            filename, size, mime_type = await self._fetch_file_details(
                direct_url, headers={"Referer": f"{parsed_url.scheme}://{parsed_url.netloc}"}
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
