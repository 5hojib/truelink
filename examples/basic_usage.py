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
                # resolve() will now return a JSON string directly
                json_result_str = await resolver.resolve(url)
                print(json_result_str)
            else:
                print(f"\nURL not supported: {url}")
        except Exception as e:
            print(f"\nError processing {url}: {e}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
