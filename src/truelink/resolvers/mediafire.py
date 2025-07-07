from __future__ import annotations

import re
from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

# Placeholder for PASSWORD_ERROR_MESSAGE, assuming it might be defined globally or passed
# For now, using a simple string. This should be revisited if it's a shared constant.
PASSWORD_ERROR_MESSAGE = "This link requires a password: {}"


class MediaFireResolver(BaseResolver):
    """Resolver for MediaFire URLs (files and folders)"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve MediaFire URL (file or folder)"""
        _password = ""
        if "::" in url:
            parts = url.split("::", 1)
            url = parts[0]
            _password = parts[1]

        if "/folder/" in url:
            return await self._resolve_folder(url, _password)
        return await self._resolve_file(url, _password)

    async def _repair_download(
        self,
        repair_url: str,
        original_password: str,
    ) -> LinkResult | FolderResult:
        """Helper to handle MediaFire's repair/continue links."""
        # The repair_url might already contain //, so ensure it's a full URL
        if repair_url.startswith("//"):
            repair_url = f"https:{repair_url}"
        elif not repair_url.startswith("http"):
            # Assuming it's a path relative to mediafire.com
            repair_url = f"https://www.mediafire.com{repair_url if repair_url.startswith('/') else '/' + repair_url}"

        # Pass the original password along, as the repair process might still need it
        return await self._resolve_file(repair_url, original_password)

    async def _resolve_file(self, url: str, password: str) -> LinkResult:
        """Resolves a single MediaFire file link."""
        parsed_url_obj = urlparse(url)
        # Normalize URL to remove query strings etc. for some checks
        normalized_url = (
            f"{parsed_url_obj.scheme}://{parsed_url_obj.netloc}{parsed_url_obj.path}"
        )

        # Check if it's already a direct download link
        if re.match(r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+", url):
            filename, size = await self._fetch_file_details(url)
            return LinkResult(url=url, filename=filename, size=size)

        try:
            async with await self._get(normalized_url) as response:
                html_text = await response.text()
            html = fromstring(html_text)

            error_elements = html.xpath('//p[@class="notranslate"]/text()')
            if error_elements:
                raise ExtractionFailedException(
                    f"MediaFire error: {error_elements[0]}",
                )

            if html.xpath("//div[@class='passwordPrompt']"):
                if not password:
                    raise ExtractionFailedException(
                        PASSWORD_ERROR_MESSAGE.format(normalized_url),
                    )

                async with await self._post(
                    normalized_url,
                    data={"downloadp": password},
                ) as pw_response:
                    html_text = await pw_response.text()
                html = fromstring(html_text)

                if html.xpath(
                    "//div[@class='passwordPrompt']",
                ):  # Password was wrong
                    raise ExtractionFailedException(
                        "MediaFire error: Wrong password.",
                    )

            final_link_elements = html.xpath(
                '//a[@aria-label="Download file"]/@href',
            )
            if not final_link_elements:
                repair_link_elements = html.xpath("//a[@class='retry']/@href")
                if repair_link_elements:
                    # The repair_link_elements[0] might be a relative path or start with //
                    return await self._repair_download(
                        repair_link_elements[0],
                        password,
                    )
                raise ExtractionFailedException(
                    "No download or repair link found on MediaFire page.",
                )

            final_link = final_link_elements[0]
            if final_link.startswith("//"):
                final_link = f"https:{final_link}"

            # If the link obtained is another mediafire page, recurse.
            # This handles cases where the first link is not the final download link.
            if "mediafire.com" in urlparse(final_link).hostname and not re.match(
                r"https?:\/\/download\d+\.mediafire\.com",
                final_link,
            ):
                return await self._resolve_file(final_link, password)

            filename, size = await self._fetch_file_details(final_link)
            return LinkResult(url=final_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire file '{url}': {e!s}",
            ) from e

    async def _fetch_folder_content_page(
        self,
        folder_key: str,
        content_type: str = "files",
    ):
        """Helper to fetch folder content (files or subfolders) via API."""
        api_url = "https://www.mediafire.com/api/1.5/folder/get_content.php"
        params = {
            "content_type": content_type,
            "folder_key": folder_key,
            "response_format": "json",
        }
        async with await self._get(api_url, params=params) as response:
            if response.status != 200:
                raise ExtractionFailedException(
                    f"Failed to get folder content API ({content_type}): {response.status}",
                )
            json_data = await response.json()

        res_api = json_data.get("response", {})
        if "message" in res_api and res_api.get("result", "").lower() == "error":
            raise ExtractionFailedException(
                f"MediaFire API error for folder content ({content_type}): {res_api['message']}",
            )
        return res_api.get("folder_content", {})

    async def _resolve_folder(self, url: str, password: str) -> FolderResult:
        """Resolves a MediaFire folder link."""
        try:
            # Extract folder key(s) from URL
            raw_path = url.split("/", 4)[-1]
            folder_key_part = raw_path.split("/", 1)[0]
            folder_keys_list = folder_key_part.split(",")
            if not folder_keys_list:
                raise InvalidURLException(
                    "Could not parse folder key from MediaFire URL.",
                )

            # For simplicity, we'll primarily use the first key for top-level info,
            # but the API might be called for each key if necessary, or for sub-folders.
            # The original script used a list `folder_infos`

            folder_api_url = "https://www.mediafire.com/api/1.5/folder/get_info.php"
            # Let's get info for the first key to find the folder title
            # The original script could handle multiple comma-separated keys in the URL for `folder_key` param.
            # We'll assume a single primary folder key for the main title for now.

            async with await self._post(
                folder_api_url,
                data={
                    "recursive": "yes",  # As per original script
                    "folder_key": folder_keys_list[
                        0
                    ],  # Using the first key for main info
                    "response_format": "json",
                },
            ) as response:
                if response.status != 200:
                    raise ExtractionFailedException(
                        f"Failed to get folder info: {response.status}",
                    )
                json_data = await response.json()

            api_response = json_data.get("response", {})
            if (
                api_response.get("result", "").lower() == "error"
                or "folder_info" not in api_response
            ):
                # Try folder_infos for multiple keys case, though we only used one key above
                if api_response.get("folder_infos"):
                    folder_title = api_response["folder_infos"][0].get(
                        "name",
                        "MediaFire Folder",
                    )
                elif "message" in api_response:
                    raise ExtractionFailedException(
                        f"MediaFire API error for folder info: {api_response['message']}",
                    )
                else:
                    raise ExtractionFailedException(
                        "MediaFire API error: Could not retrieve folder_info.",
                    )
            else:
                folder_title = api_response["folder_info"].get(
                    "name",
                    "MediaFire Folder",
                )

            all_files: list[FileItem] = []
            total_size = 0

            async def process_folder_key_contents(
                current_folder_key: str,
                current_path: str,
            ):
                nonlocal total_size  # To modify total_size from outer scope
                # Get files in the current folder
                files_content = await self._fetch_folder_content_page(
                    current_folder_key,
                    "files",
                )
                for file_info in files_content.get("files", []):
                    if "normal_download" not in file_info.get("links", {}):
                        continue

                    file_url_page = file_info["links"]["normal_download"]

                    # Resolve this file link (it's a page, not direct link yet)
                    # Need to handle potential password for each file if folder wasn't password protected but files are?
                    # Assuming folder password applies to all, or files are public if folder is accessed.
                    try:
                        link_result = await self._resolve_file(
                            file_url_page,
                            password,
                        )
                        file_item = FileItem(
                            filename=file_info.get("filename", "unknown_file"),
                            url=link_result.url,
                            size=link_result.size,  # Use size from resolved link
                            path=current_path,
                        )
                        all_files.append(file_item)
                        if link_result.size:
                            total_size += link_result.size
                    except ExtractionFailedException:
                        # Skip file if it fails to resolve, log later if needed
                        pass

                # Get subfolders and recurse
                subfolders_content = await self._fetch_folder_content_page(
                    current_folder_key,
                    "folders",
                )
                for subfolder_info in subfolders_content.get("folders", []):
                    subfolder_key = subfolder_info.get("folderkey")
                    subfolder_name = subfolder_info.get("name")
                    if subfolder_key and subfolder_name:
                        new_path = (
                            f"{current_path}/{subfolder_name}"
                            if current_path
                            else subfolder_name
                        )
                        await process_folder_key_contents(subfolder_key, new_path)

            # Process each top-level folder key provided in the URL
            for key in folder_keys_list:
                # For root folders from URL, path starts empty or with folder_title if only one key
                if (
                    len(folder_keys_list) == 1
                ):  # If only one key, use the main folder title as base path
                    pass
                # else: if multiple keys in URL, they are parallel roots, path starts empty for items inside them.
                # This part of path logic might need refinement based on desired output structure for multi-key URLs.
                # For now, items inside each key's folder will have their path relative to that folder.

                # Get initial name for path if multiple keys from URL
                # This is tricky, the original script used folder["name"] in __get_content
                # Let's assume for multiple initial keys, the path starts with that key's folder name
                current_folder_info_resp = await self._post(
                    folder_api_url,
                    data={"folder_key": key, "response_format": "json"},
                )
                current_folder_info_json = await current_folder_info_resp.json()
                current_folder_name_for_path = (
                    current_folder_info_json.get("response", {})
                    .get("folder_info", {})
                    .get("name", key)
                )

                await process_folder_key_contents(
                    key,
                    current_folder_name_for_path
                    if len(folder_keys_list) > 1
                    else folder_title,
                )

            if not all_files:
                raise ExtractionFailedException(
                    f"No downloadable files found in MediaFire folder '{url}'.",
                )

            return FolderResult(
                title=folder_title,
                contents=all_files,
                total_size=total_size,
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire folder '{url}': {e!s}",
            ) from e
