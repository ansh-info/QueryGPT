import json
import requests
from scrapegraphai.graphs import SmartScraperGraph

# Define the configuration for the scraping pipeline
graph_config = {
    "llm": {
        "url": "http://localhost:11434/api/generate",  # Ollama REST API URL for LLaMA
        "model": "ollama/llama3.1",
    },
    "verbose": True,
    "headless": True,
}

# Function to interact with the locally running LLM through Ollama's API and handle streaming
def query_llm(prompt, model, url):
    response = requests.post(
        url,
        json={
            "model": model.split('/')[1],  # Extract the model name (llama3.1)
            "prompt": prompt
        },
        stream=True  # Enable streaming for the response
    )

    full_response = ""
    
    # Process the streamed response line by line
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            try:
                json_data = json.loads(decoded_line)
                full_response += json_data.get("response", "")
            except json.JSONDecodeError:
                print(f"Failed to decode line: {decoded_line}")

    return full_response

# Create the SmartScraperGraph instance
smart_scraper_graph = SmartScraperGraph(
    prompt="What is this website about",
    source="https://www.srh-hochschule-heidelberg.de/en/master/applied-computer-science/",
    config=graph_config
)

# Run the pipeline using the locally running LLM (via Ollama)
llm_result = query_llm(smart_scraper_graph.prompt, graph_config["llm"]["model"], graph_config["llm"]["url"])

# Assuming SmartScraperGraph can accept an LLM result directly for further processing
smart_scraper_graph.llm_response = llm_result  # Manually set the LLM result

# Run the rest of the scraping pipeline
result = smart_scraper_graph.run()

# Print the result
print(json.dumps(result, indent=4))
