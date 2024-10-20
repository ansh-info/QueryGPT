from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import qdrant_client
from qdrant_client.http import models
import requests
import uvicorn
import json

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Qdrant client
qdrant_client = qdrant_client.QdrantClient("localhost", port=6333)

# Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api"

class Query(BaseModel):
    text: str

def encode_text(text):
    response = requests.post(
        f"{OLLAMA_API_URL}/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    if response.status_code == 200:
        return response.json()['embedding']
    else:
        raise HTTPException(status_code=500, detail=f"Error getting embedding: {response.text}")

def search_qdrant(query, limit=5):
    query_vector = encode_text(query)
    
    search_result = qdrant_client.search(
        collection_name="knowledge_base",
        query_vector=query_vector,
        limit=limit
    )
    return search_result

def query_ollama(prompt):
    response = requests.post(
        f"{OLLAMA_API_URL}/generate",
        json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False
        }
    )
    if response.status_code == 200:
        return response.json()['response']
    else:
        raise HTTPException(status_code=500, detail=f"Error generating response: {response.text}")

def extract_relevant_info(result):
    payload = result.payload
    content = payload.get('original_content', '')
    summary = payload.get('summary', '')
    keywords = payload.get('keywords', [])
    
    return f"Content: {content}\nSummary: {summary}\nKeywords: {', '.join(keywords)}"

@app.post("/search")
async def search(query: Query):
    try:
        search_results = search_qdrant(query.text)
        results = []
        context = ""
        
        for result in search_results:
            relevant_info = extract_relevant_info(result)
            context += relevant_info + "\n\n"
            results.append({
                "content": relevant_info,
                "score": result.score
            })
        
        prompt = f"""Based on the following context, answer the question. If the answer is not in the context, say "I don't have enough information to answer that question."

Context:
{context}

Question: {query.text}

Answer:"""
        
        ai_response = query_ollama(prompt)
        
        return {
            "search_results": results,
            "ai_response": ai_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)