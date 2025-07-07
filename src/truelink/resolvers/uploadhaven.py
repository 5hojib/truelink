from __future__ import annotations

import asyncio

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class UploadHavenResolver(BaseResolver):
    """Resolver for UploadHaven URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve UploadHaven URL"""
        try:
            # Original code had a specific Referer.
            headers = {"Referer": "http://steamunlocked.net/"}
            async with await self._get(url, headers=headers) as response:
                response_text = await response.text()
                # Storing cookies from the response if they are needed for the POST.
                # aiohttp handles cookies automatically within a session,
                # but if specific cookie handling was implied, this might need review.
                # For now, assuming session cookies are sufficient.

            html = fromstring(response_text)

            form_elements = html.xpath('//form[@method="POST"]//input')
            if not form_elements:
                raise ExtractionFailedException(
                    "Unable to find form data for POST request",
                )

            data = {i.get("name"): i.get("value") for i in form_elements}

            # Original code: sleep(15)
            await asyncio.sleep(15)

            post_headers = {"Referer": url}  # Referer for the POST is the URL itself
            async with await self._post(
                url,
                data=data,
                headers=post_headers,
            ) as post_response:
                post_response_text = await post_response.text()

            html_post = fromstring(post_response_text)

            success_link_elements = html_post.xpath(
                '//div[@class="alert alert-success mb-0"]//a',
            )
            if not success_link_elements:
                # Attempt to find an error message if the success link isn't there
                error_elements = html_post.xpath(
                    '//div[contains(@class, "alert-danger")]/text()',
                )
                if error_elements:
                    error_message = "".join(error_elements).strip()
                    raise ExtractionFailedException(
                        f"UploadHaven error: {error_message}",
                    )
                raise ExtractionFailedException(
                    "Unable to find download link after POST",
                )

            direct_link = success_link_elements[0].get("href")
            if not direct_link:
                raise ExtractionFailedException(
                    "Found link element but href is missing",
                )

            filename, size = await self._fetch_file_details(direct_link)
            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve UploadHaven URL '{url}': {e!s}",
            ) from e
