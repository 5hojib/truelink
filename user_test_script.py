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
                # resolve() will now return a LinkResult or FolderResult object
                result = await resolver.resolve(url)
                print(result)

                # Import the result types to check isinstance
                from truelink.types import LinkResult, FolderResult


            else:
                print(f"\nURL not supported: {url}")
        except Exception as e:
            print(f"\nError processing {url}: {e}")
        print("-" * 50)

if __name__ == "__main__":
    # Example with a buzzheavier URL as requested by the user
    # You can change this or add more URLs to the list above
    # urls.append("https://buzzheavier.com/rnk4ut0lci9y")
    asyncio.run(main())
