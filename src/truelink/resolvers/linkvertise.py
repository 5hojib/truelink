"""Resolver for linkvertise.com."""
from __future__ import annotations

import json
from typing import ClassVar

import aiohttp

from truelink.exceptions import ExtractionFailedException
from truelink.types import LinkResult

from .base import BaseResolver


class LinkvertiseResolver(BaseResolver):
    """Resolver for Linkvertise URLs using bypass.vip API."""

    DOMAINS: ClassVar[list[str]] = [
        "linkvertise.com",
        "linkvertise.net",
        "up-to-down.net",
        "link-hub.net",  # add more if needed
    ]

    async def resolve(self, url: str) -> LinkResult:
        """Resolve a Linkvertise URL.

        Args:
            url: The Linkvertise URL to resolve.

        Returns:
            A LinkResult object.

        """
        api_url = f"https://api.bypass.vip/bypass?url={url}"
        try:
            async with await self._get(api_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._raise_extraction_failed(
                        f"Bypass.vip API error ({response.status}): {error_text[:200]}",
                    )

                try:
                    json_response = await response.json()
                except json.JSONDecodeError as json_error:
                    snippet = await response.text()
                    msg = f"Failed to parse JSON: {json_error} - Response: {snippet[:200]}"
                    self._raise_extraction_failed(msg, from_exc=json_error)

            if (
                json_response.get("status") != "success"
                or "result" not in json_response
            ):
                msg = f"Bypass.vip API error: {json_response.get('message', 'Unknown error')}"
                self._raise_extraction_failed(msg)

            bypassed_url = json_response["result"]
            # Optionally, fetch further details if needed
            return LinkResult(url=bypassed_url)

        except ExtractionFailedException:
            raise
        except aiohttp.ClientError as e:
            msg = f"Failed to resolve Linkvertise URL: {e}"
            self._raise_extraction_failed(msg, from_exc=e)

    def _raise_extraction_failed(
        self,
        msg: str,
        *,
        from_exc: Exception | None = None,
    ) -> None:
        raise ExtractionFailedException(msg) from from_exc
