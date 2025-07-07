from __future__ import annotations

import re
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class GitHubResolver(BaseResolver):
    """Resolver for GitHub Releases asset URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve GitHub Releases asset URL"""
        try:
            # Validate if it's a GitHub URL, optionally pointing to releases.
            # The original regex was: r"\bhttps?://.*github\.com.*releases\S+"
            # This is quite broad. A more specific check might be for URLs like:
            # https://github.com/user/repo/releases/download/tag/asset.zip
            # https://github.com/user/repo/releases/latest/download/asset.zip (which redirects)
            parsed_url = urlparse(url)
            if not (
                parsed_url.hostname == "github.com"
                and "/releases/" in parsed_url.path
            ):
                # This check might be too strict or too loose depending on what forms of URLs
                # are expected. For now, matching original intent.
                # Consider if only "releases/download" paths are supported.
                if not re.search(r"github\.com.*/releases/", url):
                    raise InvalidURLException(
                        f"URL '{url}' does not appear to be a GitHub Releases link.",
                    )

            # For GitHub release assets, a GET request with allow_redirects=True
            # (which is default for self._get) should lead to the final asset URL.
            # The original code used stream=True, allow_redirects=False and checked headers['location'].
            # With aiohttp, if we allow redirects, response.url will be the final URL.
            # If we specifically need to check the redirect chain, we'd use allow_redirects=False.
            # Let's try with allow_redirects=True first, as it's simpler.

            # We make a HEAD request first to get the final URL after redirects without downloading.
            # If HEAD fails or doesn't give a useful final URL, we can fall back to GET.
            final_url_after_redirects = None
            temp_filename = None
            temp_size = None

            try:
                async with await self._get(
                    url,
                    allow_redirects=True,
                ) as response:  # Try HEAD first
                    # response.url will be the URL after all redirects
                    final_url_after_redirects = str(response.url)
                    # We can also try to get filename/size from this response
                    # This assumes the final response from HEAD (after redirects) has the correct headers
                    # For GitHub assets, it usually does.
                    content_disposition = response.headers.get("Content-Disposition")
                    if content_disposition:
                        match_fn = re.search(
                            r"filename=[\"']?([^\"']+)[\"']?",
                            content_disposition,
                        )
                        if match_fn:
                            temp_filename = match_fn.group(1)

                    if (
                        not temp_filename
                    ):  # Fallback to path if no content-disposition
                        path_filename = final_url_after_redirects.split("/")[-1]
                        if path_filename:
                            temp_filename = path_filename

                    content_length = response.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        temp_size = int(content_length)

            except Exception:  # If HEAD request fails for some reason
                pass  # We will try GET or the original logic if final_url_after_redirects is still None

            if not final_url_after_redirects:
                # Fallback to original logic: GET with allow_redirects=False and check Location header
                # This is less ideal as it might start downloading the file with GET.
                # However, if the server doesn't support HEAD well or if there's an issue.
                # For GitHub, HEAD should generally work.
                # A GET request without allow_redirects=False is needed to see 'location'
                async with await self._get(url, allow_redirects=False) as response:
                    if (
                        response.status in (301, 302, 303, 307, 308)
                        and "location" in response.headers
                    ):
                        final_url_after_redirects = response.headers["location"]
                    # If it's a 200 OK, it might be the direct asset page itself (less common for /releases/download/)
                    # Or if there's no redirect, and it's not an error, the URL itself might be the direct link.
                    # This path is less certain for typical GitHub release download URLs.
                    # For now, if no redirect, assume the original URL might be it, or raise error.
                    elif response.status == 200:
                        final_url_after_redirects = (
                            url  # Or raise, as this is unusual for /download/ paths
                        )
                    else:
                        raise ExtractionFailedException(
                            f"GitHub: Could not resolve redirect or get direct link from '{url}'. Status: {response.status}",
                        )

            if not final_url_after_redirects:
                raise ExtractionFailedException(
                    f"GitHub: Unable to extract the final asset link from '{url}'.",
                )

            # Now that we have the final_url_after_redirects, fetch details if not already fetched
            if temp_filename is None or temp_size is None:
                filename, size = await self._fetch_file_details(
                    final_url_after_redirects,
                )
            else:
                filename, size = temp_filename, temp_size

            # Ensure filename is sensible if _fetch_file_details couldn't get it
            if not filename and final_url_after_redirects:
                try:
                    parsed_dl_url = urlparse(final_url_after_redirects)
                    path_segments = [s for s in parsed_dl_url.path.split("/") if s]
                    if path_segments:
                        filename = path_segments[-1]
                except Exception:
                    pass  # Ignore if filename derivation fails

            return LinkResult(
                url=final_url_after_redirects,
                filename=filename,
                size=size,
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve GitHub Releases URL '{url}': {e!s}",
            ) from e
