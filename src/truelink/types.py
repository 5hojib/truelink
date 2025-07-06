from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class LinkResult:
    """Result for single file link"""
    url: str
    filename: Optional[str] = None
    size: Optional[int] = None

@dataclass
class FileItem:
    """Individual file in a folder"""
    filename: str
    url: str
    size: Optional[int] = None
    path: str = ""

@dataclass
class FolderResult:
    """Result for folder/multi-file link"""
    title: str
    contents: List[FileItem]
    total_size: int = 0
