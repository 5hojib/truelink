from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass


def custom_asdict_factory(data):
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

    def __str__(self):
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
    """Result for single file link"""

    url: str
    filename: str | None = None
    size: int | None = None


@dataclass
class FileItem(PrettyPrintDataClass):
    """Individual file in a folder"""

    filename: str
    url: str
    size: int | None = None
    path: str = ""


@dataclass
class FolderResult(PrettyPrintDataClass):
    """Result for folder/multi-file link"""

    title: str
    contents: list[FileItem]
    total_size: int = 0
