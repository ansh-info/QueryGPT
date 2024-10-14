import asyncio
import json
import os
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

from __init__ import path
path()

# Load environment variables from .env file in the project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_filename_from_url(url):
    parsed_url = urlparse(url)
    filename = parsed_url.path.strip("/").split("/")[-1]
    return filename

async def crawl_and_save(url):
    async with AsyncWebCrawler(verbose=os.getenv('VERBOSE', 'True').lower() == 'true') as crawler:
        result = await crawler.arun(url=url)

        filename = get_filename_from_url(url)
        
        output_dir = os.path.join('data', 'raw', 'async')
        os.makedirs(output_dir, exist_ok=True)
        
        txt_file = os.path.join(output_dir, f'{filename}.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(result.markdown)

        json_file = os.path.join(output_dir, f'{filename}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result.__dict__, f, ensure_ascii=False, indent=4)

async def main():
    config_path = os.path.join('scraper', 'config.json')
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            urls = config.get('urls', [])
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        return
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {config_path}")
        return

    if not urls:
        print("No URLs found in the config file.")
        return

    tasks = [crawl_and_save(url) for url in urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())