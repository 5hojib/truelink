# TrueLink

[![PyPI version](https://img.shields.io/pypi/v/truelink.svg)](https://pypi.org/project/truelink/)
[![Downloads](https://static.pepy.tech/badge/truelink/month)](https://pepy.tech/project/truelink)

A Python library for resolving media URLs to direct download links from various file hosting services.

## Features

- **Asynchronous**: Built with `async/await` for efficient handling of multiple requests.
- **Easy to use**: Simple API with intuitive method names.
- **Extensible**: Support for multiple file hosting platforms.
- **Caching**: Built-in caching for faster resolution of repeated requests.
- **Error handling**: Robust error handling for various edge cases.
- **URL validation**: Built-in URL validation before processing.
- **Type-hinted**: Fully type-hinted codebase for better readability and maintainability.

## Installation

```bash
pip install truelink
```

## Quick Start

```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    # Check if a URL is supported without creating an instance
    if TrueLinkResolver.is_supported("https://buzzheavier.com/rnk4ut0lci9y"):
        print("BuzzHeavier is supported!")

    resolver = TrueLinkResolver()
    url = "https://buzzheavier.com/rnk4ut0lci9y"

    try:
        result = await resolver.resolve(url)
        print(type(result))
        print(result)
    except Exception as e:
        print(f"Error processing {url}: {e}")

asyncio.run(main())
```

### Documentation

For more information, see the [documentation](https://5hojib.github.io/truelink/).
