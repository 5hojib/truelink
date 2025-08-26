#xham.py
#---------------
from typing import ClassVar
from urllib.parse import urlparse, urlunparse
from truelink.exceptions import ExtractionFailedException
from truelink.types import LinkResult
from .base import BaseResolver


class XhamResolver(BaseResolver):
    """Resolver for domain.com, domain19.com, and domain.desi via EasyDownloader API,
    normalizing host to domain00.com before processing.
    """

    DOMAINS: ClassVar[list[str]] = [
        "xhamster.com",
        "xhamster19.com",
        "xhamster.desi",
        "xhamster2.com",
        "xhaccess.com",
    ]

    API_URL: ClassVar[str] = "https://api.easydownloader.app/api-extract"
    API_KEY: ClassVar[str] = "174p81553h7m5r.eivdoi-ob-iegigrayfreprybfce-adx9XU"
    CANONICAL_HOST: ClassVar[str] = "xhamster.desi"

    def _normalize_to_canonical(self, original_url: str) -> str:
        """Replace any supported domain with the canonical host, preserving scheme, path, query, and fragment."""
        parsed = urlparse(original_url)
        # Only swap if netloc matches any of our supported domains.
        netloc = parsed.netloc
        # Handle optional leading 'www.' and port preservation
        host_port = netloc.split(":")
        host = host_port[0].lower()
        port = host_port[1] if len(host_port) == 2 else None

        base_hosts = {d.lower() for d in self.DOMAINS}
        # Strip leading www. for comparison
        cmp_host = host[4:] if host.startswith("www.") else host

        if cmp_host in base_hosts:
            new_host = self.CANONICAL_HOST
            # Keep 'www.' prefix if it existed
            if host.startswith("www."):
                new_host = "www." + new_host
            if port:
                new_host = f"{new_host}:{port}"
            replaced = parsed._replace(netloc=new_host)
            return urlunparse(replaced)

        # If it wasn't one of ours, just return original (defensive)
        return original_url

    async def resolve(self, url: str) -> LinkResult:
        # Normalize to canonical host if matched
        canonical_url = self._normalize_to_canonical(url)

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
                    )

            final_urls = data.get("final_urls", [])
            if not final_urls:
                raise ExtractionFailedException("No final_urls found in API response")

            links = final_urls[0].get("links", [])
            if not links:
                raise ExtractionFailedException("No links found inside final_urls[0]")

            preferred_qualities = ["720p", "480p", "240p"]
            selected_link = None
            for q in preferred_qualities:
                for link in links:
                    if link.get("file_quality") == q and link.get("link_url"):
                        selected_link = link["link_url"]
                        break
                if selected_link:
                    break

            if not selected_link:
                raise ExtractionFailedException(
                    "Failed to find a usable download link in preferred qualities"
                )

            return LinkResult(url=selected_link)

        except Exception as e:
            raise ExtractionFailedException(f"Failed to resolve domain URL: {e}")

    def _raise_extraction_failed(self, msg: str) -> None:
        raise ExtractionFailedException(msg)
