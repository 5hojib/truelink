# Advanced Usage

This section covers some of the more advanced features of TrueLink.

## Batch Processing

You can process multiple URLs concurrently using `asyncio.gather`. This is the most efficient way to resolve a large number of URLs.

```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    urls = [
        "https://buzzheavier.com/rnk4ut0lci9y",
        "https://www.mediafire.com/file/somefile",
        "https://www.terabox.com/sharing/link?surl=...",
    ]

    tasks = [resolver.resolve(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            print(f"Error resolving {url}: {result}")
        else:
            print(f"Successfully resolved {url}: {result}")

asyncio.run(main())
```
