import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    
    urls = [
        "https://www.lulacloud.com/d/nuNbCVcYq31-fbi-s07e14-hitched-awafim-tv-mkv",
    ]
    
    print("--- Output from resolver ---")
    for url in urls:
        try:
            if resolver.is_supported(url):
                print(f"\nProcessing URL: {url}")
                result = await resolver.resolve(url)

                from truelink.types import LinkResult, FolderResult

                if isinstance(result, LinkResult):
                    print(f"Type: LinkResult")
                    print(f"  URL: {result.url}")
                    print(f"  Filename: {result.filename}")
                    print(f"  Size: {result.size}")
                elif isinstance(result, FolderResult):
                    print(f"Type: FolderResult")
                    print(f"  Title: {result.title}")
                    print(f"  Total Size: {result.total_size}")
                    print(f"  Contents:")
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
