from __future__ import annotations

from typing import ClassVar

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
        api_url = f"https://api.bypass.vip/bypass?url={url}"
        try:
            async with await self._get(api_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._raise_extraction_failed(
                        f"Bypass.vip API error ({response.status}): {error_text[:200]}"
                    )

                try:
                    json_response = await response.json()
                except Exception as json_error:
                    snippet = await response.text()
                    msg = f"Failed to parse JSON: {json_error} - Response: {snippet[:200]}"
                    raise ExtractionFailedException(msg)

            if (
                json_response.get("status") != "success"
                or "result" not in json_response
            ):
                msg = f"Bypass.vip API error: {json_response.get('message', 'Unknown error')}"
                raise ExtractionFailedException(msg)

            bypassed_url = json_response["result"]
            # Optionally, fetch further details if needed
            return LinkResult(url=bypassed_url)

        except Exception as e:
            msg = f"Failed to resolve Linkvertise URL: {e}"
            raise ExtractionFailedException(msg)

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)
