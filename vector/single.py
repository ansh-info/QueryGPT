# File: knowledge_base_setup.py

import json
import requests
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

# Step 1: Set up Qdrant client
client = QdrantClient("localhost", port=6333)

# Step 2: Load and prepare your processed data
def load_processed_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file {file_path}")
        return None

processed_data = load_processed_data("data/processed/processed_applied-computer-science.json")
if processed_data is None:
    exit(1)

# Step 3: Create embeddings using nomic-embed-text via Ollama (if needed)
def create_embedding(text):
    try:
        response = requests.post('http://localhost:11434/api/embeddings', 
                                json={
                                    "model": "nomic-embed-text",
                                    "prompt": text
                                })
        response.raise_for_status()
        return response.json()['embedding']
    except requests.exceptions.RequestException as e:
        print(f"Error creating embedding: {str(e)}")
        return None

# Step 4: Create collection and insert data into Qdrant
collection_name = "knowledge_base"

# Attempt to create the collection directly
try:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
    )
    print(f"Collection '{collection_name}' created successfully.")
except UnexpectedResponse as e:
    if "already exists" in str(e):
        print(f"Collection '{collection_name}' already exists.")
    else:
        print(f"Error creating collection: {str(e)}")
        exit(1)

# Insert data
try:
    if 'embedding' in processed_data and isinstance(processed_data['embedding'], list):
        embedding = processed_data['embedding']
    else:
        embedding = create_embedding(processed_data['original_content'])
    
    if embedding is None:
        print("Failed to create embedding. Exiting.")
        exit(1)
    
    point = models.PointStruct(
        id=0,  # You might want to use a more meaningful ID
        vector=embedding,
        payload={
            'original_content': processed_data['original_content'],
            'entities': processed_data['entities'],
            'sentiment': processed_data['sentiment'],
            'summary': processed_data['summary'],
            'keywords': processed_data['keywords']
        }
    )
    
    client.upsert(collection_name=collection_name, points=[point])
    print("Data inserted successfully into the knowledge base.")
except Exception as e:
    print(f"Error processing data: {str(e)}")
    exit(1)

# Step 5: Set up querying capabilities
def query_knowledge_base(query_text, top_k=5):
    query_vector = create_embedding(query_text)
    if query_vector is None:
        print("Failed to create query embedding.")
        return []
    
    try:
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k
        )
        return [hit.payload for hit in search_result]
    except Exception as e:
        print(f"Error querying knowledge base: {str(e)}")
        return []

# Example usage
query = "What is applied computer science?"
results = query_knowledge_base(query)
print(f"Top results for query '{query}':")
for result in results:
    print("Summary:", result['summary'])
    print("Keywords:", result['keywords'])
    print("---")