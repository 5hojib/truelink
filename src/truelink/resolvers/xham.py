# xham.py
# ---------------
from typing import ClassVar
from urllib.parse import urlparse, urlunparse
from truelink.exceptions import ExtractionFailedException
from truelink.types import FileItem, FolderResult, LinkResult
from .base import BaseResolver


class XhamResolver(BaseResolver):
    """Resolver for xhamster variants via EasyDownloader API, normalizing host to xhamster.desi before processing."""

    DOMAINS: ClassVar[list[str]] = [
        "xhamster.com",
        "xhamster19.com",
        "xhamster1.desi",
        "xhamster2.com",
        "xhaccess.com",
    ]

    API_URL: ClassVar[str] = "https://api.easydownloader.app/api-extract"
    API_KEY: ClassVar[str] = "175p40401h9m2rcmvdo-epdagr-egmadidn-eri-hcE"
    CANONICAL_HOST: ClassVar[str] = "xhamster1.desi"

    def _normalize_to_canonical(self, original_url: str) -> str:
        """Replace supported domains with xhamster.desi using netloc only; keep scheme/path/query/fragment."""
        parsed = urlparse(original_url)  # parse URL into parts [11]
        to_replace = {
            "xhamster.com",
            "xhamster19.com",
            "xhamster1.desi",
            "xhamster2.com",
            "xhaccess.com",
        }  # exact netloc matches [11]
        if parsed.netloc in to_replace:
            replaced = parsed._replace(netloc=self.CANONICAL_HOST)  # swap netloc only [11]
            return urlunparse(replaced)  # reassemble URL preserving other parts [11]
        return original_url  # not in our set; return unchanged [11]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        # Normalize to canonical host if matched
        canonical_url = self._normalize_to_canonical(url)  # netloc-based canonicalization [11]

        payload = {
            "video_url": canonical_url,
            "pagination": False,
            "key": self.API_KEY,
        }

        try:
            # POST to the EasyDownloader API
            async with await self._post(self.API_URL, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._raise_extraction_failed(
                        f"EasyDownloader API error ({response.status}): {error_text[:200]}"
                    )
                try:
                    data = await response.json()
                except Exception as e:
                    snippet = await response.text()
                    raise ExtractionFailedException(
                        f"Failed to parse JSON: {e} - Response: {snippet[:200]}"
                    ) from e

            # Expecting a structure similar to: {"final_urls": [{"links": [...], "file_name": "...", "file_type": "...", ...}]}
            final_urls = data.get("final_urls", [])
            if not isinstance(final_urls, list) or not final_urls:
                raise ExtractionFailedException("No final_urls found in API response")

            block = final_urls[0]  # take first block as in other resolvers
            links = block.get("links", [])
            if not isinstance(links, list) or not links:
                raise ExtractionFailedException("No links found inside final_urls")

            # Attempt to take filename/mime from block if present (as per API fields)
            block_filename = block.get("file_name")  # API-provided filename [2][5]
            block_mime = block.get("file_type") or "application/octet-stream"  # API-provided type or fallback [2][5]

            # Preferred quality order
            preferred_qualities = ["720p", "480p", "240p"]

            # Choose best quality link
            chosen = None
            for q in preferred_qualities:
                for link in links:
                    if link.get("file_quality") == q and link.get("link_url"):
                        chosen = link
                        break
                if chosen:
                    break

            if not chosen:
                # If no preferred quality, optionally pick the first available valid link
                for link in links:
                    if link.get("link_url"):
                        chosen = link
                        break

            if not chosen:
                raise ExtractionFailedException(
                    "Failed to find a usable download link in preferred qualities"
                )

            # Map fields from chosen link and/or block for LinkResult parity with Terabox
            link_url = chosen.get("link_url")
            # Prefer more specific per-link fields if present; otherwise use block-level metadata
            filename = chosen.get("file_name") or block_filename or None  # name source [2][5]
            mime_type = chosen.get("file_type") or block_mime or "application/octet-stream"  # MIME [2][5]
            size = chosen.get("file_size") or None  # may be absent; keep None if not provide
            return LinkResult(
                url=link_url,
                filename=filename,
                mime_type=mime_type,
                size=size,
            )

        except Exception as e:
            raise ExtractionFailedException(f"Failed to resolve domain URL: {e}") from e

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)
