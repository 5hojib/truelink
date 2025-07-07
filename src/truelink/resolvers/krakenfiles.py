from __future__ import annotations

from urllib.parse import urljoin  # For constructing full URLs if needed

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class KrakenFilesResolver(BaseResolver):
    """Resolver for KrakenFiles.com URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve KrakenFiles.com URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()

            html = fromstring(response_text)

            post_url_elements = html.xpath('//form[@id="dl-form"]/@action')
            if not post_url_elements:
                # Fallback: Try to find form action by other means if ID is missing/changed
                post_url_elements = html.xpath(
                    '//form[contains(@action, "/download/")]/@action',
                )
                if not post_url_elements:
                    raise ExtractionFailedException(
                        "KrakenFiles error: Unable to find post form action URL.",
                    )

            post_url_path = post_url_elements[0]
            # Ensure post_url is absolute
            if post_url_path.startswith("//"):
                post_url = f"{response.url.scheme}:{post_url_path}"
            elif post_url_path.startswith("/"):
                post_url = (
                    f"{response.url.scheme}://{response.url.host}{post_url_path}"
                )
            elif not post_url_path.startswith("http"):
                post_url = urljoin(
                    str(response.url),
                    post_url_path,
                )  # Use response.url as base
            else:
                post_url = post_url_path

            token_elements = html.xpath('//input[@id="dl-token"]/@value')
            if not token_elements:
                # Fallback: look for input with name 'token'
                token_elements = html.xpath(
                    '//form[@id="dl-form"]//input[@name="token"]/@value',
                )
                if not token_elements:
                    raise ExtractionFailedException(
                        "KrakenFiles error: Unable to find token for POST request.",
                    )

            token = token_elements[0]
            post_data = {"token": token}

            # Headers for POST might be important, e.g., Referer
            post_headers = {
                "Referer": url,
                "X-Requested-With": "XMLHttpRequest",  # Often used for such POST requests
            }
            async with await self._post(
                post_url,
                data=post_data,
                headers=post_headers,
            ) as post_response:
                try:
                    json_response = await post_response.json()
                except (
                    Exception
                ) as json_error:  # More specific error for JSON parsing
                    # Check if response text contains clues if not JSON
                    text_response_snippet = await post_response.text()
                    if "captcha" in text_response_snippet.lower():
                        raise ExtractionFailedException(
                            f"KrakenFiles error: Captcha encountered. {text_response_snippet[:200]}",
                        )
                    raise ExtractionFailedException(
                        f"KrakenFiles error: Failed to parse JSON response from POST. Error: {json_error}. Response: {text_response_snippet[:200]}",
                    )

            if json_response.get("status") != "ok":
                error_message = json_response.get(
                    "message",
                    "POST request did not return 'ok' status.",
                )
                if (
                    "url" not in json_response
                ):  # If status is not ok AND no url, it's likely an error
                    raise ExtractionFailedException(
                        f"KrakenFiles error: {error_message}",
                    )
                # If status is not 'ok' but 'url' exists, we might try to use it, but it's risky.
                # For now, strict check on status == 'ok'.

            if "url" not in json_response:
                raise ExtractionFailedException(
                    "KrakenFiles error: 'url' not found in JSON response after POST.",
                )

            direct_link = json_response["url"]

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve KrakenFiles.com URL '{url}': {e!s}",
            ) from e
