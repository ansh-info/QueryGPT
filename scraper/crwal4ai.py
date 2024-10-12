import asyncio
import json
import os
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the root directory (one level up from the script directory)
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# Load environment variables from .env file in the script directory
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# Function to get a safe filename based on the last part of the URL
def get_filename_from_url(url):
    parsed_url = urlparse(url)
    # Split the path and get the last segment, which is the slug
    filename = parsed_url.path.strip("/").split("/")[-1]
    return filename

async def crawl_and_save(url):
    async with AsyncWebCrawler(verbose=os.getenv('VERBOSE', 'True').lower() == 'true') as crawler:
        result = await crawler.arun(url=url)

        # Generate filename from the last part of the URL
        filename = get_filename_from_url(url)
        
        # Create the data directory if it doesn't exist
        output_dir = os.path.join(ROOT_DIR, 'data', 'raw', 'async')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the result as a .txt file
        with open(os.path.join(output_dir, f'{filename}.txt'), 'w', encoding='utf-8') as txt_file:
            txt_file.write(result.markdown)

        # Save the result as a .json file
        with open(os.path.join(output_dir, f'{filename}.json'), 'w', encoding='utf-8') as json_file:
            json.dump(result.__dict__, json_file, ensure_ascii=False, indent=4)

async def main():
    # Load URLs from the config file in the script directory
    config_path = os.path.join(SCRIPT_DIR, 'config.json')
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

    # Run the crawler for each URL
    tasks = [crawl_and_save(url) for url in urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
    