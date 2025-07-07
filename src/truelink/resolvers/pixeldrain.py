from __future__ import annotations

from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class PixelDrainResolver(BaseResolver):
    """Resolver for PixelDrain URLs"""

    # Note: The original resolver uses "pd.cybar.xyz".
    # This might be an unofficial proxy/mirror and could be unstable.
    # PixelDrain's official API is typically pixeldrain.com/api.
    # For now, replicating original behavior.

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve PixelDrain URL"""
        try:
            parsed_url = urlparse(url.rstrip("/"))
            path_parts = parsed_url.path.split("/")

            if not path_parts:
                raise InvalidURLException("Invalid PixelDrain URL: Empty path.")

            # Assuming the last part of the path is the file ID or list ID
            # PixelDrain URLs can be:
            # - pixeldrain.com/u/{file_id} (old, download page)
            # - pixeldrain.com/api/file/{file_id} (direct download, requires no redirect)
            # - pixeldrain.com/l/{list_id} (list of files)
            # - pixeldrain.com/file/{file_id} (current download page)
            # The original code splits by '/' and takes the last part.

            file_or_list_code = path_parts[-1]
            if (
                not file_or_list_code
            ):  # If URL ends with a slash, previous part might be the code
                if len(path_parts) > 1:
                    file_or_list_code = path_parts[-2]
                else:
                    raise InvalidURLException(
                        "Invalid PixelDrain URL: Could not extract ID.",
                    )

            # The original code uses "https://pd.cybar.xyz/" and appends the code.
            # Let's see where that request leads.
            # It's possible pd.cybar.xyz is a direct link generator itself.
            # We assume it redirects to the actual file or provides it directly.

            # If the input URL is a /l/ list URL, this approach will not work correctly
            # as it will try to treat the list ID as a file ID with pd.cybar.xyz.
            # The current resolver logic seems to only handle single files via this proxy.
            # We should check if the original URL is a list and raise if so,
            # or implement list handling if required (which is more complex).
            if parsed_url.path.startswith("/l/"):
                raise ExtractionFailedException(
                    "PixelDrain lists (/l/ URLs) are not directly supported by this resolver method."
                    " A list resolver would require iterating items.",
                )

            # Replicating: response = get("https://pd.cybar.xyz/", allow_redirects=True)
            # This seems to imply that pd.cybar.xyz itself (the root) redirects to some base.
            # And then `response.url + code` is used. This is unusual.
            # Let's test what `https://pd.cybar.xyz/` returns.
            # If it's a constant base URL, we can hardcode it.
            # For now, let's assume the intent was to use `https://pd.cybar.xyz/{code}`.

            # The original logic:
            # response = get("https://pd.cybar.xyz/", allow_redirects=True)
            # return response.url + code -> This implies pd.cybar.xyz/ redirects to a base path,
            # and then the code is appended. e.g. if it redirects to "https://somecdn.com/base/",
            # the result is "https://somecdn.com/base/THE_FILE_CODE".

            # Let's try to get the base redirect from pd.cybar.xyz
            # This is fragile as pd.cybar.xyz could change or go down.
            temp_base_url = (
                "https://pd.cybar.xyz/"  # Default if the root fetch fails
            )
            try:
                async with await self._get(
                    "https://pd.cybar.xyz/",
                    allow_redirects=True,
                ) as base_res:
                    # Ensure the final URL from pd.cybar.xyz ends with a slash if it's a base path
                    fetched_base = str(base_res.url)
                    if not fetched_base.endswith("/"):
                        fetched_base += "/"
                    temp_base_url = fetched_base
            except Exception:
                # If fetching base fails, proceed with the hardcoded one, or raise.
                # For now, let it try with the default assumption or fail at the next step.
                pass  # temp_base_url remains "https://pd.cybar.xyz/"

            # If file_or_list_code already contains query params from original URL, they'd be appended here.
            # Usually, the code is just the ID.
            direct_link = temp_base_url + file_or_list_code

            # An alternative interpretation of the original:
            # code = url.split("/")[-1].split("?", 1)[0] -> clean code
            # direct_link = "https://pixeldrain.com/api/file/" + code -> using official API
            # This would be more robust if pd.cybar.xyz is problematic.
            # Let's stick to original's apparent logic first.

            filename, size = await self._fetch_file_details(direct_link)

            # If filename is not found, try to use the code as a fallback
            if not filename:
                filename = file_or_list_code

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve PixelDrain URL '{url}': {e!s}",
            ) from e
