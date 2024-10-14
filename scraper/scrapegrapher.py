import json
import re
import requests
import os
from urllib.parse import urlparse
from scrapegraphai.graphs import SmartScraperGraph
from typing import Dict, Any
from dotenv import load_dotenv

from __init__ import path
path()

# Load environment variables
load_dotenv()

# Define the configuration for the scraping pipeline
graph_config = {
    "llm": {
        "url": os.getenv("LLM_URL", "http://localhost:11434/api/generate"),
        "model": os.getenv("LLM_MODEL", "ollama/llama3.1"),
    },
    "verbose": os.getenv("VERBOSE", "True").lower() == "true",
    "headless": os.getenv("HEADLESS", "True").lower() == "true",
}

FORMAT_INSTRUCTIONS = """
Please format your response as a JSON object with 'topic' and 'key_points' fields. 
The 'topic' field should be an object with 'name' and 'description' fields. 
The 'key_points' should be an array of strings.
"""

def query_llm(prompt: str, model: str, url: str) -> str:
    print("Sending prompt to LLM:", prompt)
    response = requests.post(
        url,
        json={
            "model": model.split('/')[1],
            "prompt": prompt
        },
        stream=True
    )

    full_response = ""
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            try:
                json_data = json.loads(decoded_line)
                chunk = json_data.get("response", "")
                full_response += chunk
                print("Received chunk:", chunk)
            except json.JSONDecodeError:
                print(f"Failed to decode line: {decoded_line}")

    print("Full LLM response:")
    print(full_response)
    return full_response

def parse_llm_output(output: str) -> Dict[str, Any]:
    print("Parsing LLM output:")
    print(output)
    
    json_match = re.search(r'```\s*(.*?)\s*```', output, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        try:
            parsed_json = json.loads(json_str)
            print("Extracted JSON:", json.dumps(parsed_json, indent=2))
            
            if isinstance(parsed_json.get('topic'), dict):
                topic = parsed_json['topic'].get('name', '') + ': ' + parsed_json['topic'].get('description', '')
            else:
                topic = str(parsed_json.get('topic', 'Topic not found'))
            
            key_points = parsed_json.get('key_points', [])
            
            return {
                "topic": topic,
                "key_points": key_points
            }
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
    else:
        print("No JSON found in the output")
    
    key_points_match = re.search(r'\[(.*?)\]', output, re.DOTALL)
    if key_points_match:
        key_points_str = key_points_match.group(1)
        key_points = [point.strip().strip('"') for point in key_points_str.split(',')]
        print("Extracted key points:", key_points)
    else:
        key_points = []
        print("No key points found in the output")

    topic = "Topic not found"
    if key_points:
        topic = key_points[0]

    print("Extracted topic:", topic)

    return {
        "topic": topic,
        "key_points": key_points
    }

def get_prompt_for_url(url: str) -> str:
    if "applied-computer-science" in url:
        return "What is applied computer science? Provide a brief overview and key points."
    elif "about-us" in url:
        return "What is SRH Hochschule Heidelberg? Provide a brief overview and key points about the university."
    elif "study-in-germany" in url:
        return "What are the key aspects of studying in Germany at SRH Hochschule Heidelberg? Provide an overview and main points."
    else:
        return "Provide a brief overview and key points about the content of this page."

def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    last_part = path.strip('/').split('/')[-1]
    return f"{last_part}.json" if last_part else "index.json"

def process_url(url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    content_prompt = get_prompt_for_url(url)
    full_prompt = f"{content_prompt}\n\n{FORMAT_INSTRUCTIONS}"

    smart_scraper_graph = SmartScraperGraph(
        prompt=full_prompt,
        source=url,
        config=config
    )

    llm_result = query_llm(smart_scraper_graph.prompt, config["llm"]["model"], config["llm"]["url"])

    try:
        parsed_result = parse_llm_output(llm_result)
        smart_scraper_graph.llm_response = parsed_result
    except Exception as e:
        print(f"Error parsing LLM output: {e}")
        print("Raw LLM output:")
        print(llm_result)
        smart_scraper_graph.llm_response = {"error": "Failed to parse LLM output"}

    def patched_run(self):
        self.final_state = {"llm_response": self.llm_response}
        return self.final_state

    SmartScraperGraph.run = patched_run

    return smart_scraper_graph.run()

def save_result_to_file(result: Dict[str, Any], url: str):
    output_dir = os.path.join('data', 'raw', 'llama')
    os.makedirs(output_dir, exist_ok=True)
    
    filename = get_filename_from_url(url)
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    print(f"Result saved to {filepath}")

def main():
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

    for url in urls:
        print(f"\nProcessing URL: {url}")
        result = process_url(url, graph_config)
        print("Final result:")
        print(json.dumps(result, indent=4))
        save_result_to_file(result, url)
        print("\n" + "="*50)

if __name__ == "__main__":
    main()