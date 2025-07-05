import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    
    # Example URLs (replace with actual URLs)
    urls = [
        "https://buzzheavier.com/example123",
        "https://fuckingfast.co/example456",
        "https://lulacloud.com/example789",
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

if __name__ == "__main__":
    asyncio.run(main())
