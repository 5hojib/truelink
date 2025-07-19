from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass


def custom_asdict_factory(data: object) -> object:
    """
    Recursively converts dataclass instances (including nested ones and lists of them)
    into dictionaries. Other data types are returned as is.
    """
    if isinstance(data, list):
        return [custom_asdict_factory(item) for item in data]
    if is_dataclass(data) and not isinstance(data, type):
        return {k: custom_asdict_factory(v) for k, v in asdict(data).items()}
    return data


class PrettyPrintDataClass:
    """
    A base class for dataclasses to provide a pretty-printed str representation,
    formatted as a JSON-like string, omitting None and empty list values.
    """

    def __str__(self) -> str:
        raw_dict = asdict(self)
        processed_dict = {k: custom_asdict_factory(v) for k, v in raw_dict.items()}
        filtered_dict = {
            k: v
            for k, v in processed_dict.items()
            if v is not None and (not isinstance(v, list) or v)
        }
        return json.dumps(filtered_dict, indent=4, ensure_ascii=False)


@dataclass
class LinkResult(PrettyPrintDataClass):
    """Result for single file link.

    This class represents the result type returned by the resolve() method when processing a single file link.

    Attributes:
        url (str): The direct download URL for the file.
        filename (str, optional): The original filename of the file.
        mime_type (str, optional): The MIME type of the file (e.g., "video/mp4").
        size (int, optional): Size of the file in bytes.
        headers (dict, optional): Custom headers needed for the download (e.g., {"Authorization": "Bearer token"}).

    Example:
        ```python
        {
            "url": "direct_download_url",
            "filename": "original_filename",
            "mime_type": "video/mp4",
            "size": 1234567,  # Size in bytes
            "headers": {"Authorization": "Bearer token"}
        }
        ```
    """

    url: str
    filename: str | None = None
    mime_type: str | None = None
    size: int | None = None
    headers: dict | None = None


@dataclass
class FileItem(PrettyPrintDataClass):
    """Individual file in a folder.

    This class represents a single file within a folder result.

    Attributes:
        url (str): The direct download URL for the file.
        filename (str): The name of the file.
        mime_type (str, optional): The MIME type of the file.
        size (int, optional): Size of the file in bytes.
        path (str): Relative path of the file within the folder structure.

    Example:
        ```python
        {
            "url": "direct_download_url_2",
            "filename": "file2.jpg",
            "mime_type": "image/jpeg",
            "size": 987654,
            "path": "file2.jpg"
        }
        ```
    """

    url: str
    filename: str
    mime_type: str | None = None
    size: int | None = None
    path: str = ""


@dataclass
class FolderResult(PrettyPrintDataClass):
    """Result for folder/multi-file link.

    This class represents the result type returned by the resolve() method when processing a folder or multi-file link.

    Attributes:
        title (str): The name of the folder.
        contents (list[FileItem]): List of files contained in the folder.
        total_size (int): Total size of all files in bytes.
        headers (dict, optional): Custom headers needed for downloads.

    Example:
        ```python
        {
            "title": "Folder Name",
            "contents": [
                {
                    "url": "direct_download_url_1",
                    "filename": "file1.pdf",
                    "mime_type": "application/pdf",
                    "size": 1234567,
                    "path": "subfolder/file1.pdf"
                },
                {
                    "url": "direct_download_url_2",
                    "filename": "file2.jpg",
                    "mime_type": "image/jpeg",
                    "size": 987654,
                    "path": "file2.jpg"
                }
            ],
            "total_size": 2222221,  # Total size of all files
            "headers": {"Authorization": "Bearer token"}
        }
        ```
    """

    title: str
    contents: list[FileItem]
    total_size: int = 0
    headers: dict | None = None
