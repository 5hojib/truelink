from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class StreamvidResolver(BaseResolver):
    """Resolver for Streamvid.net URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Streamvid.net URL"""
        try:
            parsed_url = urlparse(url)
            path_segments = [seg for seg in parsed_url.path.split("/") if seg]

            if not path_segments:
                raise InvalidURLException(
                    "Streamvid: Invalid URL, no path segments found.",
                )

            file_code_with_quality = path_segments[
                -1
            ]  # e.g., filecode_o or just filecode

            # Check if a specific quality is appended (e.g., _o, _h, _n, _l)
            quality_defined = False
            file_code = file_code_with_quality

            quality_suffixes = [
                "_o",
                "_h",
                "_n",
                "_l",
            ]  # _o (original), _h (high), _n (normal), _l (low)
            for suffix in quality_suffixes:
                if file_code_with_quality.endswith(suffix):
                    quality_defined = True
                    file_code = file_code_with_quality[: -len(suffix)]
                    break

            # Construct the download page URL (e.g., https://streamvid.net/d/filecode)
            # The original script forms .../d/file_code regardless of original path.
            # This implies original URL might be streamvid.net/filecode or streamvid.net/xxxx/filecode
            # We will use the extracted file_code to form the /d/ URL.
            download_page_url = f"{parsed_url.scheme}://{parsed_url.netloc}/d/{file_code_with_quality if quality_defined else file_code}"

            # If quality was defined in original URL, it's appended to the /d/ URL too.
            # e.g. streamvid.net/d/xxxxx_o

            async with await self._get(download_page_url) as page_response:
                page_html_text = await page_response.text()
            html = fromstring(page_html_text)

            if quality_defined:
                # If quality is in URL, expect a form to POST to get the actual link.
                form_inputs = html.xpath(
                    '//form[@id="F1"]//input | //form[contains(@action, "/d/")]//input',
                )  # More generic form search
                if not form_inputs:
                    # Check for errors if form not found
                    error_div = html.xpath(
                        '//div[@class="alert alert-danger"][1]/text()',
                    )
                    if (
                        error_div and len(error_div) > 1
                    ):  # Often error is second text node
                        raise ExtractionFailedException(
                            f"Streamvid error (quality page): {error_div[1].strip()}",
                        )
                    raise ExtractionFailedException(
                        "Streamvid error: No form inputs found on quality download page.",
                    )

                post_data = {}
                for i in form_inputs:
                    name = i.get("name")
                    value = i.get("value")
                    if name:  # Ensure name exists
                        post_data[name] = (
                            value if value is not None else ""
                        )  # Handle None values

                # POST to the same download_page_url
                async with await self._post(
                    download_page_url,
                    data=post_data,
                ) as post_response:
                    post_response_text = await post_response.text()

                post_html = fromstring(post_response_text)

                # Script extraction logic from original
                # Look for: document.location.href = "DIRECT_LINK_HERE";
                script_elements = post_html.xpath(
                    '//script[contains(text(),"document.location.href")]/text()',
                )
                if not script_elements:
                    error_div_post = post_html.xpath(
                        '//div[@class="alert alert-danger"][1]/text()',
                    )
                    if error_div_post and len(error_div_post) > 1:
                        raise ExtractionFailedException(
                            f"Streamvid error (after POST): {error_div_post[1].strip()}",
                        )
                    raise ExtractionFailedException(
                        "Streamvid error: Direct link script not found after POST.",
                    )

                script_content = script_elements[0]
                direct_link_match = re.search(
                    r'document\.location\.href\s*=\s*["\']([^"\']+)["\']',
                    script_content,
                )
                if not direct_link_match:
                    raise ExtractionFailedException(
                        "Streamvid error: Direct link not found in script pattern.",
                    )

                direct_link = direct_link_match.group(1)
                # Ensure link is absolute
                if not direct_link.startswith("http"):
                    direct_link = urljoin(download_page_url, direct_link)

                filename, size = await self._fetch_file_details(
                    direct_link,
                    custom_headers={"Referer": download_page_url},
                )
                return LinkResult(url=direct_link, filename=filename, size=size)

            # Quality not defined in URL, list available qualities
            qualities_urls = html.xpath('//div[@id="dl_versions"]//a/@href')
            qualities_texts = html.xpath(
                '//div[@id="dl_versions"]//a/text()[normalize-space()]',
            )  # Get non-empty text nodes

            if qualities_urls and qualities_texts:
                error_message = "Streamvid: Provide a quality to download. Append suffix to URL (e.g., _o, _h, _n, _l).\nAvailable Qualities:"

                # Clean up quality texts (sometimes they have extra spaces/newlines)
                cleaned_texts = [
                    re.sub(r"\s+", " ", text).strip()
                    for text in qualities_texts
                    if text.strip()
                ]

                # Ensure we have same number of URLs and cleaned texts
                # The original code used `zip` which stops at shortest. We should ensure they match.
                # Typically, the text is like "Original video", "1080p video" etc.
                # The URL is like /d/filecode_o

                for i, q_url_path in enumerate(qualities_urls):
                    quality_name = (
                        cleaned_texts[i]
                        if i < len(cleaned_texts)
                        else q_url_path.split("_")[-1]
                        if "_" in q_url_path
                        else "Unknown"
                    )
                    # The q_url_path is relative, e.g. /d/xxxx_o. We need the suffix part.
                    suffix_match = re.search(
                        r"(_[ohl])$",
                        q_url_path.split("/")[-1],
                    )  # _o, _h, _l
                    if not suffix_match:  # Try _n for normal or others
                        suffix_match = re.search(
                            r"(_[a-zA-Z])$",
                            q_url_path.split("/")[-1],
                        )

                    suffix_for_user = (
                        suffix_match.group(1) if suffix_match else "(see full path)"
                    )

                    # Construct the full URL for user to click or use
                    full_q_url = urljoin(download_page_url, q_url_path)
                    error_message += f"\n- {quality_name}: use suffix like `{suffix_for_user}` (Link: {full_q_url} )"

                raise ExtractionFailedException(error_message)

            # If no qualities listed, check for common errors
            error_not_found = html.xpath('//div[@class="not-found-text"]/text()')
            if error_not_found:
                raise ExtractionFailedException(
                    f"Streamvid error: {error_not_found[0].strip()}",
                )

            # General error if page structure is unexpected
            raise ExtractionFailedException(
                "Streamvid error: Page structure for quality selection not recognized, and no specific error found.",
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Streamvid.net URL '{url}': {e!s}",
            ) from e
