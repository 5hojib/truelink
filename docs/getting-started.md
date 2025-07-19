# Getting Started

This guide will walk you through the basics of using TrueLink to resolve URLs.

## Resolving a URL

The main entry point for using TrueLink is the `TrueLinkResolver` class. You can use it to resolve a single URL like this:

```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    url = "https://buzzheavier.com/rnk4ut0lci9y"

    try:
        if resolver.is_supported(url):
            result = await resolver.resolve(url)
            print(result)
        else:
            print(f"URL not supported: {url}")
    except Exception as e:
        print(f"Error processing {url}: {e}")

asyncio.run(main())
```

The `resolve()` method returns a `LinkResult` or `FolderResult` object, depending on the type of link. You can find more information about these objects in the [API Reference](core.md).

## Checking for Supported URLs

Before attempting to resolve a URL, you can check if it's supported by TrueLink using the `is_supported()` method:

```python
from truelink import TrueLinkResolver

resolver = TrueLinkResolver()

if resolver.is_supported("https://www.mediafire.com/file/somefile"):
    print("This URL is supported!")
else:
    print("This URL is not supported.")
```

## Listing Supported Domains

You can get a list of all supported domains using the `get_supported_domains()` method:

```python
from truelink import TrueLinkResolver

resolver = TrueLinkResolver()
supported_domains = resolver.get_supported_domains()
print(supported_domains)
```
