from __future__ import annotations

import asyncio
import os.path as ospath  # For ospath.join
import re
from urllib.parse import unquote, urlparse

import cloudscraper  # For Cloudflare bypass
from lxml.etree import HTML

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

PASSWORD_ERROR_MESSAGE = (
    "ERROR: This link is password protected. Please provide the password for: {}"
)


class MediaFireResolver(BaseResolver):
    """Resolver for MediaFire URLs (files and folders)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _run_sync_in_thread(self, func, *args, **kwargs):
        """Helper to run synchronous cloudscraper calls in a separate thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve MediaFire URL (file or folder)"""
        _password = ""
        if "::" in url:
            parts = url.split("::", 1)
            url = parts[0]
            _password = parts[1]

        parsed_url = urlparse(url)
        base_url_for_checks = (
            f"{parsed_url.scheme}://{parsed_url.netloc}{unquote(parsed_url.path)}"
        )

        if "/folder/" in base_url_for_checks:
            return await self._resolve_folder(url, _password)
        return await self._resolve_file(url, _password)

    async def _get_page_content(self, scraper_session, url_to_fetch: str) -> str:
        response = await self._run_sync_in_thread(scraper_session.get, url_to_fetch)
        response.raise_for_status()
        return response.text

    async def _post_page_content(
        self, scraper_session, url_to_fetch: str, data: dict
    ) -> str:
        response = await self._run_sync_in_thread(
            scraper_session.post, url_to_fetch, data=data
        )
        response.raise_for_status()
        return response.text

    async def _repair_download(
        self,
        scraper_session,
        repair_url: str,
        original_url_for_password_msg: str,
        original_password: str,
    ) -> LinkResult:
        """Helper to handle MediaFire's repair/continue links."""
        full_repair_url = repair_url
        if repair_url.startswith("//"):
            full_repair_url = f"https:{repair_url}"
        elif not repair_url.startswith("http"):
            full_repair_url = f"https://www.mediafire.com{repair_url if repair_url.startswith('/') else '/' + repair_url}"

        return await self._resolve_file(
            full_repair_url,
            original_password,
            scraper_session_override=scraper_session,
        )

    async def _resolve_file(
        self, url: str, password: str, scraper_session_override=None
    ) -> LinkResult:
        """
        Resolves a single MediaFire file link.
        Uses cloudscraper via asyncio.to_thread for network operations.
        Accepts an optional scraper_session_override to reuse a session (e.g., from _repair_download).
        """
        if re.search(r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+", url):
            try:
                filename, size = await self._fetch_file_details(url)
            except Exception:
                filename = unquote(url.split("/")[-1])
                size = None
            return LinkResult(url=url, filename=filename, size=size)

        if scraper_session_override:
            scraper = scraper_session_override
        else:
            scraper = cloudscraper.create_scraper()
            scraper.headers.update({"User-Agent": BaseResolver.USER_AGENT})

        display_url = url

        try:
            html_text = await self._get_page_content(scraper, url)
            html = HTML(html_text)

            if error_msg_list := html.xpath('//p[@class="notranslate"]/text()'):
                raise ExtractionFailedException(
                    f"MediaFire error: {error_msg_list[0]}"
                )

            if html.xpath("//div[@class='passwordPrompt']"):
                if not password:
                    raise ExtractionFailedException(
                        PASSWORD_ERROR_MESSAGE.format(display_url)
                    )

                html_text = await self._post_page_content(
                    scraper, url, data={"downloadp": password}
                )
                html = HTML(html_text)

                if html.xpath("//div[@class='passwordPrompt']"):
                    raise ExtractionFailedException(
                        "MediaFire error: Wrong password."
                    )

            if not (
                final_link_elements := html.xpath(
                    '//a[@aria-label="Download file"]/@href'
                )
            ):
                if repair_link_elements := html.xpath("//a[@class='retry']/@href"):
                    return await self._repair_download(
                        scraper,
                        repair_link_elements[0],
                        display_url,
                        password,
                    )
                raise ExtractionFailedException(
                    "ERROR: No links found in this page Try Again"
                )

            final_link = final_link_elements[0]

            if final_link.startswith("//"):
                return await self._resolve_file(
                    f"https:{final_link}", password, scraper_session_override=scraper
                )

            final_parsed = urlparse(final_link)
            if "mediafire.com" in final_parsed.hostname and not re.match(
                r"https?:\/\/download\d+\.mediafire\.com", final_link
            ):
                return await self._resolve_file(
                    final_link, password, scraper_session_override=scraper
                )

            try:
                dl_filename, dl_size = await self._fetch_file_details(final_link)
            except Exception:
                dl_filename = unquote(final_link.split("/")[-1].split("?")[0])
                dl_size = None
            return LinkResult(url=final_link, filename=dl_filename, size=dl_size)

        except cloudscraper.exceptions.CloudflareException as e:
            raise ExtractionFailedException(
                f"MediaFire Cloudflare challenge failed: {e!s}"
            ) from e
        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire file '{display_url}': {e.__class__.__name__} - {e!s}",
            ) from e
        finally:
            if not scraper_session_override and hasattr(scraper, "close"):
                await self._run_sync_in_thread(scraper.close)

    async def _api_request(
        self, scraper_session, method: str, api_url: str, data=None, params=None
    ) -> dict:
        """Helper for making API requests using cloudscraper session."""
        if method.lower() == "post":
            response_json = await self._run_sync_in_thread(
                scraper_session.post, api_url, data=data, params=params, timeout=20
            )
        else:
            response_json = await self._run_sync_in_thread(
                scraper_session.get, api_url, params=params, data=data, timeout=20
            )

        response_json.raise_for_status()
        json_data = response_json.json()

        api_res = json_data.get("response", {})
        if api_res.get("result", "").lower() == "error" or "message" in api_res:
            error_message = api_res.get("message", "Unknown API error")
            if "error" in api_res:
                error_message += f" (Code: {api_res['error']})"
            raise ExtractionFailedException(f"MediaFire API error: {error_message}")
        return api_res

    async def _resolve_folder(self, url: str, password: str) -> FolderResult:
        """Resolves a MediaFire folder link using logic from user's provided code."""
        scraper = cloudscraper.create_scraper()
        scraper.headers.update({"User-Agent": BaseResolver.USER_AGENT})

        try:
            try:
                raw = url.split("/", 4)[-1]
                folder_key_part = raw.split("/", 1)[0]
                folder_keys_list = folder_key_part.split(",")
                if not folder_keys_list or not folder_keys_list[0]:
                    raise ValueError("Empty folder key")
            except Exception as e:
                raise InvalidURLException(
                    f"ERROR: Could not parse folder key from URL '{url}': {e}"
                ) from e

            folder_key_param_for_api = ",".join(folder_keys_list)

            try:
                folder_info_response = await self._api_request(
                    scraper,
                    "post",
                    "https://www.mediafire.com/api/1.5/folder/get_info.php",
                    data={
                        "recursive": "yes",
                        "folder_key": folder_key_param_for_api,
                        "response_format": "json",
                    },
                )
            except Exception as e:
                raise ExtractionFailedException(
                    f"ERROR: {e.__class__.__name__} While getting folder info for keys '{folder_key_param_for_api}' - {e}"
                )

            processed_folder_infos = []
            if "folder_infos" in folder_info_response:
                processed_folder_infos.extend(folder_info_response["folder_infos"])
            elif "folder_info" in folder_info_response:
                processed_folder_infos.append(folder_info_response["folder_info"])
            else:
                raise ExtractionFailedException(
                    "ERROR: Malformed API response from folder/get_info (missing folder_info/folder_infos)."
                )

            if not processed_folder_infos:
                raise ExtractionFailedException(
                    "ERROR: No folder information found from API."
                )

            main_folder_title = processed_folder_infos[0].get(
                "name", "MediaFire Folder"
            )

            all_files: list[FileItem] = []
            total_size_bytes: int = 0

            async def get_folder_contents_recursive(
                current_mf_folder_key: str, current_path_prefix: str
            ):
                nonlocal total_size_bytes

                try:
                    content_api_params = {
                        "content_type": "files",
                        "folder_key": current_mf_folder_key,
                        "response_format": "json",
                    }
                    files_content_response = await self._api_request(
                        scraper,
                        "get",
                        "https://www.mediafire.com/api/1.5/folder/get_content.php",
                        params=content_api_params,
                    )
                except Exception as e:
                    raise ExtractionFailedException(
                        f"Failed to get files for folder key {current_mf_folder_key}: {e}"
                    )

                api_files = files_content_response.get("folder_content", {}).get(
                    "files", []
                )
                for file_api_data in api_files:
                    if not file_api_data.get("links") or not file_api_data[
                        "links"
                    ].get("normal_download"):
                        continue

                    file_page_url = file_api_data["links"]["normal_download"]

                    try:
                        link_result = await self._resolve_file(
                            file_page_url, password
                        )

                        item_filename = file_api_data.get("filename", "unknown_file")
                        item_size = link_result.size
                        if item_size is None and "size" in file_api_data:
                            size_str = str(file_api_data["size"])
                            if size_str.isdigit():
                                item_size = int(size_str)

                        file_item = FileItem(
                            filename=item_filename,
                            url=link_result.url,
                            size=item_size,
                            path=ospath.join(current_path_prefix, item_filename),
                        )
                        all_files.append(file_item)
                        if item_size:
                            total_size_bytes += item_size

                    except ExtractionFailedException:
                        pass
                    except Exception:
                        pass

                try:
                    subfolders_content_params = {
                        "content_type": "folders",
                        "folder_key": current_mf_folder_key,
                        "response_format": "json",
                    }
                    subfolders_response = await self._api_request(
                        scraper,
                        "get",
                        "https://www.mediafire.com/api/1.5/folder/get_content.php",
                        params=subfolders_content_params,
                    )
                except Exception as e:
                    raise ExtractionFailedException(
                        f"Failed to get subfolders for folder key {current_mf_folder_key}: {e}"
                    )

                api_subfolders = subfolders_response.get("folder_content", {}).get(
                    "folders", []
                )
                for subfolder_api_data in api_subfolders:
                    sub_folder_key = subfolder_api_data.get("folderkey")
                    sub_folder_name = subfolder_api_data.get("name")
                    if sub_folder_key and sub_folder_name:
                        new_path_prefix = ospath.join(
                            current_path_prefix, sub_folder_name
                        )
                        await get_folder_contents_recursive(
                            sub_folder_key, new_path_prefix
                        )

            for folder_data in processed_folder_infos:
                folder_key_from_api = folder_data.get("folderkey")
                folder_name_from_api = folder_data.get("name")
                if folder_key_from_api and folder_name_from_api:
                    await get_folder_contents_recursive(
                        folder_key_from_api, folder_name_from_api
                    )

            if not all_files:
                raise ExtractionFailedException(
                    f"No downloadable files found in MediaFire folder '{url}'.",
                )

            return FolderResult(
                title=main_folder_title,
                contents=all_files,
                total_size=total_size_bytes,
            )

        except cloudscraper.exceptions.CloudflareException as e:
            raise ExtractionFailedException(
                f"MediaFire Cloudflare challenge failed during folder processing: {e!s}"
            ) from e
        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire folder '{url}': {e.__class__.__name__} - {e!s}",
            ) from e
        finally:
            if hasattr(scraper, "close"):
                await self._run_sync_in_thread(scraper.close)
