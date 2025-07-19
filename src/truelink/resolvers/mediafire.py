from __future__ import annotations

import asyncio
import base64
import contextlib
import os.path as ospath
import re
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import unquote, urlparse

import cloudscraper
from lxml.etree import HTML

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

if TYPE_CHECKING:
    from collections.abc import Callable


class MediaFireResolver(BaseResolver):
    """Resolver for MediaFire URLs (files and folders)"""

    DOMAINS: ClassVar[list[str]] = ["mediafire.com"]

    async def _run_sync(
        self, func: Callable[..., Any], *args: object, **kwargs: object
    ) -> object:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        password = ""
        if "::" in url:
            url, password = url.split("::", 1)

        parsed_url = urlparse(url)
        base_url = (
            f"{parsed_url.scheme}://{parsed_url.netloc}{unquote(parsed_url.path)}"
        )

        return await (
            self._resolve_folder if "/folder/" in base_url else self._resolve_file
        )(url, password)

    async def _get_content(
        self,
        scraper: cloudscraper.CloudScraper,
        url: str,
        method: str = "get",
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict | str:
        func = scraper.post if method == "post" else scraper.get
        response = await self._run_sync(
            func, url, data=data, params=params, timeout=20
        )
        response.raise_for_status()
        return response.json() if method == "post" or "api" in url else response.text

    async def _decode_url(
        self, html: HTML, scraper: cloudscraper.CloudScraper
    ) -> str:
        """Decode MediaFire download URL from HTML using new method"""
        enc_url = html.xpath('//a[@id="downloadButton"]')
        if not enc_url:
            raise ExtractionFailedException(
                "Download button not found in the HTML content. It may have been blocked by Cloudflare's anti-bot protection."
            )

        final_link = enc_url[0].attrib.get("href")
        scrambled = enc_url[0].attrib.get("data-scrambled-url")

        if final_link and scrambled:
            try:
                return base64.b64decode(scrambled).decode("utf-8")
            except Exception as e:
                raise ExtractionFailedException(
                    f"Failed to decode final link. {e.__class__.__name__}"
                ) from e
        elif final_link and final_link.startswith("http"):
            return final_link
        elif final_link and final_link.startswith("//"):
            return await self._resolve_file(f"https:{final_link}", "", scraper)
        else:
            raise ExtractionFailedException("No download link found")

    async def _repair_download(
        self, scraper: cloudscraper.CloudScraper, url: str, password: str
    ) -> LinkResult:
        if url.startswith("//"):
            url = f"https:{url}"
        elif not url.startswith("http"):
            url = f"https://www.mediafire.com/{url.lstrip('/')}"
        return await self._resolve_file(url, password, scraper)

    async def _resolve_file(
        self,
        url: str,
        password: str,
        scraper: cloudscraper.CloudScraper | None = None,
    ) -> LinkResult:
        if re.search(r"https?://download\d+\.mediafire\.com/.+/.+/.+", url):
            filename, size, mime_type = await self._fetch_file_details(url)
            return LinkResult(
                url=url, filename=filename, size=size, mime_type=mime_type
            )

        scraper = scraper or cloudscraper.create_scraper()
        scraper.headers.update({"User-Agent": BaseResolver.USER_AGENT})

        try:
            parsed_url = urlparse(url)
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

            html = HTML(await self._get_content(scraper, url))
            if error := html.xpath('//p[@class="notranslate"]/text()'):
                raise ExtractionFailedException(f"MediaFire error: {error[0]}")

            if html.xpath("//div[@class='passwordPrompt']"):
                if not password:
                    raise ExtractionFailedException(
                        f"ERROR: This link is password protected. Please provide the password for: {url}"
                    )
                html = HTML(
                    await self._get_content(
                        scraper, url, method="post", data={"downloadp": password}
                    )
                )
                if html.xpath("//div[@class='passwordPrompt']"):
                    raise ExtractionFailedException(
                        "MediaFire error: Wrong password."
                    )

            # Use the new decoding method
            final_link = await self._decode_url(html, scraper)

            # Handle recursive cases
            if final_link.startswith("//"):
                return await self._resolve_file(
                    f"https:{final_link}", password, scraper
                )
            if "mediafire.com" in urlparse(final_link).hostname and not re.match(
                r"https?://download\d+\.mediafire\.com", final_link
            ):
                return await self._resolve_file(final_link, password, scraper)

            filename, size, mime_type = await self._fetch_file_details(final_link)
            return LinkResult(
                url=final_link, filename=filename, size=size, mime_type=mime_type
            )

        except cloudscraper.exceptions.CloudflareException as e:
            raise ExtractionFailedException(
                f"MediaFire Cloudflare challenge failed: {e}"
            ) from e
        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire file '{url}': {e}"
            ) from e
        finally:
            if scraper and not isinstance(scraper, cloudscraper.CloudScraper):
                await self._run_sync(scraper.close)

    async def _api_request(
        self,
        scraper: cloudscraper.CloudScraper,
        method: str,
        url: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        json_data = await self._get_content(
            scraper, url, method=method, data=data, params=params
        )
        response_data = json_data.get("response", {})
        if response_data.get("result") == "Error" or "message" in response_data:
            message = response_data.get("message", "Unknown API error")
            if "error" in response_data:
                message += f" (Code: {response_data['error']})"
            raise ExtractionFailedException(f"MediaFire API error: {message}")
        return response_data

    async def _decode_folder_file_url(
        self, html: HTML, scraper: cloudscraper.CloudScraper
    ) -> str | None:
        """Decode URL for files within folders"""
        enc_url = html.xpath('//a[@id="downloadButton"]')
        if not enc_url:
            return None

        final_link = enc_url[0].attrib.get("href")
        scrambled = enc_url[0].attrib.get("data-scrambled-url")

        if final_link and scrambled:
            with contextlib.suppress(Exception):
                return base64.b64decode(scrambled).decode("utf-8")
        elif final_link and final_link.startswith("http"):
            return final_link
        elif final_link and final_link.startswith("//"):
            with contextlib.suppress(Exception):
                return await self._resolve_file(f"https:{final_link}", "", scraper)
        return None

    async def _scrape_folder_file(
        self, url: str, password: str, scraper: cloudscraper.CloudScraper
    ) -> LinkResult | None:
        """Scrape individual file from folder"""
        try:
            parsed_url = urlparse(url)
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

            html = HTML(await self._get_content(scraper, url))

            if html.xpath("//div[@class='passwordPrompt']"):
                if not password:
                    raise ExtractionFailedException(
                        f"ERROR: This link is password protected. Please provide the password for: {url}"
                    )
                html = HTML(
                    await self._get_content(
                        scraper, url, method="post", data={"downloadp": password}
                    )
                )
                if html.xpath("//div[@class='passwordPrompt']"):
                    return None

            final_link = await self._decode_folder_file_url(html, scraper)
            if not final_link:
                return None

            filename, size, mime_type = await self._fetch_file_details(final_link)
            return LinkResult(
                url=final_link, filename=filename, size=size, mime_type=mime_type
            )
        except Exception:
            return None

    async def _resolve_folder(self, url: str, password: str) -> FolderResult:
        scraper = cloudscraper.create_scraper()
        scraper.headers.update({"User-Agent": BaseResolver.USER_AGENT})

        try:
            folder_keys = url.split("/", 4)[-1].split("/", 1)[0].split(",")
            if not folder_keys[0]:
                raise InvalidURLException(f"Invalid folder key in URL: {url}")

            folder_info = await self._api_request(
                scraper,
                "post",
                "https://www.mediafire.com/api/1.5/folder/get_info.php",
                data={
                    "recursive": "yes",
                    "folder_key": ",".join(folder_keys),
                    "response_format": "json",
                },
            )

            folders = folder_info.get("folder_infos") or [
                folder_info.get("folder_info")
            ]
            if not folders:
                raise ExtractionFailedException("No folder info found from API.")

            folder_title = folders[0].get("name", "MediaFire Folder")
            all_files: list[FileItem] = []
            total_size = 0

            async def collect_files(folder_key: str, path_prefix: str) -> None:
                nonlocal total_size
                files_data = await self._api_request(
                    scraper,
                    "get",
                    "https://www.mediafire.com/api/1.5/folder/get_content.php",
                    params={
                        "content_type": "files",
                        "folder_key": folder_key,
                        "response_format": "json",
                    },
                )
                files = files_data.get("folder_content", {}).get("files", [])
                for file in files:
                    url = file.get("links", {}).get("normal_download")
                    if not url:
                        continue
                    try:
                        # Use the new scraping method for folder files
                        result = await self._scrape_folder_file(
                            url, password, scraper
                        )
                        if result:
                            file_item = FileItem(
                                url=result.url,
                                filename=result.filename,
                                size=result.size,
                                mime_type=result.mime_type,
                                path=ospath.join(path_prefix, result.filename),
                            )
                            all_files.append(file_item)
                            total_size += result.size or 0
                    except ExtractionFailedException:
                        continue

                subfolders_data = await self._api_request(
                    scraper,
                    "get",
                    "https://www.mediafire.com/api/1.5/folder/get_content.php",
                    params={
                        "content_type": "folders",
                        "folder_key": folder_key,
                        "response_format": "json",
                    },
                )
                for subfolder in subfolders_data.get("folder_content", {}).get(
                    "folders", []
                ):
                    await collect_files(
                        subfolder["folderkey"],
                        ospath.join(path_prefix, subfolder["name"]),
                    )

            for folder in folders:
                await collect_files(folder["folderkey"], folder["name"])

            if not all_files:
                raise ExtractionFailedException(
                    f"No files found in MediaFire folder: {url}"
                )

            return FolderResult(
                title=folder_title, contents=all_files, total_size=total_size
            )

        except cloudscraper.exceptions.CloudflareException as e:
            raise ExtractionFailedException(
                f"MediaFire Cloudflare challenge failed: {e}"
            ) from e
        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire folder '{url}': {e}"
            ) from e
        finally:
            await self._run_sync(scraper.close)
