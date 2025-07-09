from __future__ import annotations

import asyncio

from truelink import TrueLinkResolver


async def main():
    resolver = TrueLinkResolver()
    url = "https://streamtape.to/v/0JqVB7zqz7hmlp"

    try:
        if resolver.is_supported(url):
            result = await resolver.resolve(url)
            print(type(result))
            print(f"Result: {result}")
        else:
            print(f"URL not supported: {url}")
    except Exception as e:
        print(f"Error processing {url}: {e}")


asyncio.run(main())
