import asyncio
import json
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler

# Function to get a safe filename based on the last part of the URL
def get_filename_from_url(url):
    parsed_url = urlparse(url)
    # Split the path and get the last segment, which is the slug
    filename = parsed_url.path.strip("/").split("/")[-1]
    return filename

async def crawl_and_save(url):
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)

        # Generate filename from the last part of the URL
        filename = get_filename_from_url(url)
        
        # Save the result as a .txt file
        with open(f'{filename}.txt', 'w', encoding='utf-8') as txt_file:
            txt_file.write(result.markdown)

        # Save the result as a .json file
        with open(f'{filename}.json', 'w', encoding='utf-8') as json_file:
            json.dump(result.__dict__, json_file, ensure_ascii=False, indent=4)

async def main():
    # List of URLs to crawl
    urls = [
        "https://www.srh-hochschule-heidelberg.de/en/study-at-srh/study-in-germany/",
        "https://www.srh-hochschule-heidelberg.de/en/why-srh/about-us/",
        "https://www.srh-hochschule-heidelberg.de/en/study-at-srh/study-in-germany/coming-to-germany-and-getting-started/",
        "https://www.srh-hochschule-heidelberg.de/en/master/applied-computer-science/"
    ]

    # Run the crawler for each URL
    tasks = [crawl_and_save(url) for url in urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
