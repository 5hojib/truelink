import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    
    urls = [
        "https://www.lulacloud.com/d/nuNbCVcYq31-fbi-s07e14-hitched-awafim-tv-mkv",
    ]
    
    for url in urls:
        try:
            if resolver.is_supported(url):
                result = await resolver.resolve(url)
                print(f"URL: {url}")
                print(f"Result: {result}")
                print("-" * 50)
            else:
                print(f"URL not supported: {url}")
        except Exception as e:
            print(f"Error processing {url}: {e}")

await main()
