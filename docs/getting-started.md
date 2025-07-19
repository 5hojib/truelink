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

## Caching

TrueLink has a built-in caching mechanism to speed up repeated requests for the same URL. To use it, simply pass the `use_cache=True` argument to the `resolve()` method:

```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    url = "https://buzzheavier.com/rnk4ut0lci9y"

    # The first time, the URL will be resolved and the result will be cached
    result1 = await resolver.resolve(url, use_cache=True)
    print(f"First result: {result1}")

    # The second time, the result will be loaded from the cache
    result2 = await resolver.resolve(url, use_cache=True)
    print(f"Second result: {result2}")

asyncio.run(main())
```

## Checking for Supported URLs

You can check if a URL is supported by TrueLink using the static method `is_supported()` without creating an instance of `TrueLinkResolver`:

```python
from truelink import TrueLinkResolver

if TrueLinkResolver.is_supported("https://www.mediafire.com/file/somefile"):
    print("This URL is supported!")
else:
    print("This URL is not supported.")
```

## Listing Supported Domains

You can get a list of all supported domains using the static method `get_supported_domains()`:

```python
from truelink import TrueLinkResolver

supported_domains = TrueLinkResolver.get_supported_domains()
print(supported_domains)
```
