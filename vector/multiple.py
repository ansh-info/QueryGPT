import os
import json
import requests
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

# Step 1: Set up Qdrant client
client = QdrantClient("localhost", port=6333)

# Step 2: Load and prepare your processed data
def load_processed_data(directory):
    data = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(directory, filename), 'r') as file:
                    data.append(json.load(file))
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in file {filename}")
            except Exception as e:
                print(f"Error reading file {filename}: {str(e)}")
    return data

processed_data = load_processed_data("data/processed")
if not processed_data:
    print("No valid data found. Exiting.")
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
for i, item in enumerate(processed_data):
    try:
        if 'embedding' in item and isinstance(item['embedding'], list):
            embedding = item['embedding']
        else:
            embedding = create_embedding(item['original_content'])
        
        if embedding is None:
            print(f"Failed to create embedding for item {i}. Skipping.")
            continue
        
        point = models.PointStruct(
            id=i,
            vector=embedding,
            payload={
                'original_content': item['original_content'],
                'entities': item['entities'],
                'sentiment': item['sentiment'],
                'summary': item['summary'],
                'keywords': item['keywords']
            }
        )
        
        client.upsert(collection_name=collection_name, points=[point])
        print(f"Inserted item {i} into the knowledge base.")
    except Exception as e:
        print(f"Error processing item {i}: {str(e)}")

print("All data inserted successfully into the knowledge base.")

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
print(f"\nTop results for query '{query}':")
for i, result in enumerate(results, 1):
    print(f"\nResult {i}:")
    print("Summary:", result['summary'])
    print("Keywords:", result['keywords'])
    print("---")