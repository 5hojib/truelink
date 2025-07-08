from __future__ import annotations

from urllib.parse import urlparse, urlunparse
from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class Mp4UploadResolver(BaseResolver):
    """Resolver for Mp4Upload.com URLs"""

    BASE_URL = "https://www.mp4upload.com/"

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Mp4Upload.com URL"""
        try:
            parsed_url = urlparse(url)
            normalized_path = parsed_url.path
            if "embed-" in normalized_path:
                normalized_path = normalized_path.replace("embed-", "")

            page_url = urlunparse(
                (parsed_url.scheme, parsed_url.netloc, normalized_path, "", "", ""),
            )

            async with await self._get(page_url) as page_response:
                page_html_text = await page_response.text()
            html = fromstring(page_html_text)

            form1_inputs = html.xpath(
                '//form[@name="F1"]//input | //form[button/@name="submit"]//input',
            )
            if not form1_inputs:
                form1_inputs = html.xpath("//input")

            if not form1_inputs:
                if (
                    "File Not Found" in page_html_text
                    or "File was removed" in page_html_text
                ):
                    raise ExtractionFailedException(
                        "Mp4Upload error: File Not Found or removed.",
                    )
                raise ExtractionFailedException(
                    "Mp4Upload error: Could not find initial form inputs on page.",
                )

            data1 = {
                i.get("name"): i.get("value", "")
                for i in form1_inputs
                if i.get("name")
            }
            if not data1:
                raise ExtractionFailedException(
                    "Mp4Upload error: No valid data extracted for first POST.",
                )

            headers_post1 = {"Referer": self.BASE_URL}
            async with await self._post(
                page_url,
                data=data1,
                headers=headers_post1,
            ) as post1_response:
                post1_html_text = await post1_response.text()

            html_post1 = fromstring(post1_html_text)

            form2_inputs = html_post1.xpath(
                '//form[@name="F1"]//input | //form[button/@name="submit"]//input',
            )
            if not form2_inputs:
                if (
                    "File Not Found" in post1_html_text
                    or "download link generated" not in post1_html_text.lower()
                ):
                    raise ExtractionFailedException(
                        "Mp4Upload error: Second form inputs not found or page indicates an error after first POST.",
                    )
                direct_link_early = html_post1.xpath(
                    '//a[contains(@href,"mp4upload.com:183/d/")]/@href',
                )
                if direct_link_early:
                    dl = direct_link_early[0]
                    filename, size = await self._fetch_file_details(
                        dl,
                        custom_headers={"Referer": page_url},
                    )
                    return LinkResult(url=dl, filename=filename, size=size)
                raise ExtractionFailedException(
                    "Mp4Upload error: Second form inputs not found after first POST.",
                )

            data2 = {
                i.get("name"): (i.get("value") or "").replace(" ", "")
                for i in form2_inputs
                if i.get("name")
            }
            if not data2:
                raise ExtractionFailedException(
                    "Mp4Upload error: No valid data extracted for second POST.",
                )

            data2["referer"] = page_url

            async with await self._post(
                page_url,
                data=data2,
                headers=headers_post1,
            ) as post2_response:
                direct_link = str(post2_response.url)

            if (
                not direct_link
                or "mp4upload" not in urlparse(direct_link).netloc.lower()
            ):
                final_page_text = await post2_response.text()
                if (
                    "generating download link" in final_page_text.lower()
                    or "timer" in final_page_text.lower()
                ):
                    raise ExtractionFailedException(
                        "Mp4Upload error: Stuck in a loop or timer page after second POST.",
                    )
                raise ExtractionFailedException(
                    f"Mp4Upload error: Could not obtain final direct link URL after second POST. Ended at: {direct_link}",
                )

            fetch_headers = {"Referer": self.BASE_URL}
            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers=fetch_headers,
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Mp4Upload.com URL '{url}': {e!s}",
            ) from e