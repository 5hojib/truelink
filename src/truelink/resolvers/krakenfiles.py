from __future__ import annotations

from urllib.parse import urljoin

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


# todo
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
                post_url_elements = html.xpath(
                    '//form[contains(@action, "/download/")]/@action',
                )
                if not post_url_elements:
                    raise ExtractionFailedException(
                        "KrakenFiles error: Unable to find post form action URL.",
                    )

            post_url_path = post_url_elements[0]
            if post_url_path.startswith("//"):
                post_url = f"{response.url.scheme}:{post_url_path}"
            elif post_url_path.startswith("/"):
                post_url = (
                    f"{response.url.scheme}://{response.url.host}{post_url_path}"
                )
            elif not post_url_path.startswith("http"):
                post_url = urljoin(str(response.url), post_url_path)
            else:
                post_url = post_url_path

            token_elements = html.xpath('//input[@id="dl-token"]/@value')
            if not token_elements:
                token_elements = html.xpath(
                    '//form[@id="dl-form"]//input[@name="token"]/@value',
                )
                if not token_elements:
                    raise ExtractionFailedException(
                        "KrakenFiles error: Unable to find token for POST request.",
                    )

            token = token_elements[0]
            post_data = {"token": token}

            post_headers = {
                "Referer": url,
                "X-Requested-With": "XMLHttpRequest",
            }
            async with await self._post(
                post_url,
                data=post_data,
                headers=post_headers,
            ) as post_response:
                try:
                    json_response = await post_response.json()
                except Exception as json_error:
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
                if "url" not in json_response:
                    raise ExtractionFailedException(
                        f"KrakenFiles error: {error_message}",
                    )

            if "url" not in json_response:
                raise ExtractionFailedException(
                    "KrakenFiles error: 'url' not found in JSON response after POST.",
                )

            direct_link = json_response["url"]

            filename, size, _ = await self._fetch_file_details(
                direct_link,
                headers={"Referer": url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve KrakenFiles.com URL '{url}': {e!s}",
            ) from e
