from __future__ import annotations

import asyncio

from truelink import TrueLinkResolver


async def main():
    resolver = TrueLinkResolver()

    urls = [
        "https://www.lulacloud.com/d/nuNbCVcYq31-fbi-s07e14-hitched-awafim-tv-mkv",
    ]
    urls.append("https://buzzheavier.com/rnk4ut0lci9y")

    print("--- Output from resolver ---")
    for url in urls:
        try:
            if resolver.is_supported(url):
                print(f"\nProcessing URL: {url}")
                result = await resolver.resolve(url)
                print(result)

            else:
                print(f"\nURL not supported: {url}")
        except Exception as e:
            print(f"\nError processing {url}: {e}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
