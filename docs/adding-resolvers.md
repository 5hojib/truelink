# How to Add a New Resolver

This guide explains how to add a new resolver to TrueLink. Resolvers are classes that handle the logic for extracting direct download links from a specific service (e.g., GoFile, MediaFire).

## 1. Understand the Basics

Before you start, it's important to understand the basic structure of a resolver. All resolvers inherit from the `BaseResolver` class, which provides common functionality like making HTTP requests.

The core of a resolver is the `resolve` method, which takes a URL as input and should return either a `LinkResult` (for a single file) or a `FolderResult` (for a folder).

## 2. Create a New Resolver File

The first step is to create a new Python file in the `src/truelink/resolvers/` directory. The filename should be descriptive of the service you are adding (e.g., `myresolver.py`).

Here is a basic structure for a new resolver:

```python
# src/truelink/resolvers/myresolver.py

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from truelink.exceptions import ExtractionFailedException
from truelink.types import LinkResult, FolderResult

from .base import BaseResolver

if TYPE_CHECKING:
    # Import any other necessary types here
    pass


class MyResolver(BaseResolver):
    """Resolver for MyService URLs."""

    DOMAINS: ClassVar[list[str]] = ["myservice.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """
        Resolve a MyService URL to a direct download link or folder.
        """
        # Your implementation here
        raise ExtractionFailedException("Not yet implemented.")
```

## 3. Implement the `resolve` Method

This is where you will add the logic to extract the direct download link. This process typically involves:

1.  **Making HTTP requests** to the service's website or API. You can use the `self._get()` and `self._post()` methods provided by the `BaseResolver`.
2.  **Parsing the response** (HTML or JSON) to find the direct download link, filename, and other details.
3.  **Returning a `LinkResult` or `FolderResult`**.

### Helper Methods

The `BaseResolver` class provides a few helper methods to make things easier:

-   `self._get(url, **kwargs)`: Makes a GET request.
-   `self._post(url, **kwargs)`: Makes a POST request.
-   `self._fetch_file_details(url)`: Fetches the filename, size, and mime type of a file from a URL.

### Example: Returning a `LinkResult`

If the URL points to a single file, you should return a `LinkResult` object:

```python
download_url = "..."  # Extracted download link
filename, size, mime_type = await self._fetch_file_details(download_url)

return LinkResult(
    url=download_url,
    filename=filename,
    size=size,
    mime_type=mime_type,
)
```

### Example: Returning a `FolderResult`

If the URL points to a folder, you should return a `FolderResult` object, which contains a list of `FileItem` objects:

```python
from truelink.types import FileItem

contents = [
    FileItem(
        url="<direct_download_link_1>",
        filename="<filename_1>",
        size=<size_in_bytes_1>,
        mime_type="<mime_type_1>",
        path="<path_inside_folder>",
    ),
    # ... more files
]

return FolderResult(
    title="<folder_title>",
    contents=contents,
    total_size=<total_size_in_bytes>,
)
```

## 4. Add the Resolver to `__init__.py`

After creating your resolver, you need to add it to the list of available resolvers in `src/truelink/resolvers/__init__.py`. This makes it accessible to the main `truelink` library.

```python
# src/truelink/resolvers/__init__.py

# ... other imports

from .myresolver import MyResolver

# ...

__all__ = [
    # ... other resolvers
    "MyResolver",
]
```

## 5. Write Tests

To ensure your resolver works correctly and doesn't break in the future, you should add tests for it. Create a new test file in the `tests/` directory (e.g., `tests/test_myresolver.py`).

Your tests should cover:

-   Valid URLs (both single file and folder, if applicable)
-   Invalid or broken URLs
-   Edge cases (e.g., password-protected links)

## 6. Update Documentation

Finally, add your new resolver to the list of supported services in the documentation.

By following these steps, you can contribute new resolvers to TrueLink and help expand its capabilities. If you have any questions, feel free to open an issue on GitHub.
