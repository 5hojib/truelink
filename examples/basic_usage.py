from __future__ import annotations

import asyncio

from truelink import TrueLinkResolver
from truelink.types import FolderResult, LinkResult


async def main():
    resolver = TrueLinkResolver()

    urls = [
        "https://www.lulacloud.com/d/nuNbCVcYq31-fbi-s07e14-hitched-awafim-tv-mkv",
        "https://buzzheavier.com/rnk4ut0lci9y",
        "https://terabox.com/s/1vDkjtJWtIOcwr8swIOIBwQ",
        "https://teraboxapp.com/s/1SZjA6tA5qVS0XOT2zSeqlw",
        "https://1fichier.com/?te04fuktzjfv3jktkvy1",
        "https://gofile.io/d/JcxE4Y",
        "https://www.linkbox.cloud/a/f/X2WPE4l",
        "https://mediafile.cc/d689ae178d6aa83e",
        "https://pixeldra.in/u/Z4S2Upby",
        "https://tmpsend.com/jo83PlU1",
        "https://www.upload.ee/files/18302589/VID-20250705-WA0001.mp4.html",
    ]

    print("--- Output from resolver ---")
    for url in urls:
        try:
            if resolver.is_supported(url):
                print(f"\nProcessing URL: {url}")
                result = await resolver.resolve(url)

                if isinstance(result, LinkResult):
                    print("Type: LinkResult")
                    print(f"  URL: {result.url}")
                    print(f"  Filename: {result.filename}")
                    print(f"  Size: {result.size}")
                elif isinstance(result, FolderResult):
                    print("Type: FolderResult")
                    print(f"  Title: {result.title}")
                    print(f"  Total Size: {result.total_size}")
                    print("  Contents:")
                    for item in result.contents:
                        print(f"    - Filename: {item.filename}")
                        print(f"      URL: {item.url}")
                        print(f"      Size: {item.size}")
                        print(f"      Path: {item.path}")
                else:
                    print(f"Unknown result type: {type(result)}")
                    print(f"Result: {result}")

            else:
                print(f"\nURL not supported: {url}")
        except Exception as e:
            print(f"\nError processing {url}: {e}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
