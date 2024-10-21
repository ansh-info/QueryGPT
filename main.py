from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import qdrant_client
from qdrant_client.http import models
import requests
import uvicorn
from typing import List, Optional
from datetime import datetime
import logging
from functools import lru_cache
import time
from collections import Counter

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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
RATE_LIMIT = 10  # requests
RATE_LIMIT_DURATION = 60  # seconds
request_history = {}

class Query(BaseModel):
    text: str
    filters: Optional[dict] = None

class SearchResult(BaseModel):
    content: str
    score: float
    category: Optional[str] = None
    source: Optional[str] = None
    date: Optional[datetime] = None

def rate_limit(request: Request):
    client = request.client.host
    current_time = time.time()
    if client in request_history:
        request_times = request_history[client]
        request_times = [t for t in request_times if current_time - t < RATE_LIMIT_DURATION]
        if len(request_times) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    else:
        request_times = []
    request_times.append(current_time)
    request_history[client] = request_times

def preprocess_query(query: str) -> str:
    # Simple preprocessing: lowercase and strip whitespace
    return query.lower().strip()

def expand_query(query: str) -> List[str]:
    # Simple query expansion
    expanded = [query]
    if "srh" in query:
        expanded.append(query.replace("srh", "srh hochschule heidelberg"))
    return expanded

@lru_cache(maxsize=100)
def encode_text(text):
    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()['embedding']
    except requests.RequestException as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting embedding")

def search_qdrant(query: str, filters: Optional[dict] = None, limit: int = 5):
    query_vector = encode_text(query)
    
    filter_conditions = []
    if filters:
        for key, value in filters.items():
            filter_conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                )
            )
    
    try:
        search_result = qdrant_client.search(
            collection_name="knowledge_base",
            query_vector=query_vector,
            query_filter=models.Filter(
                must=filter_conditions
            ) if filter_conditions else None,
            limit=limit
        )
        return search_result
    except Exception as e:
        logger.error(f"Error searching Qdrant: {str(e)}")
        raise HTTPException(status_code=500, detail="Error searching knowledge base")

@lru_cache(maxsize=100)
def query_ollama(prompt):
    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()['response']
    except requests.RequestException as e:
        logger.error(f"Error generating response: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating AI response")

def extract_relevant_info(result) -> SearchResult:
    payload = result.payload
    return SearchResult(
        content=payload.get('original_content', ''),
        score=result.score,
        category=payload.get('category'),
        source=payload.get('source'),
        date=payload.get('date')
    )

def get_knowledge_base_summary():
    try:
        # Fetch all entries from the Qdrant collection
        entries = qdrant_client.scroll(
            collection_name="knowledge_base",
            limit=1000  # Adjust based on your knowledge base size
        )[0]

        # Extract categories and keywords
        categories = Counter()
        all_keywords = Counter()
        entry_count = len(entries)
        
        for entry in entries:
            payload = entry.payload
            categories[payload.get('category', 'Uncategorized')] += 1
            keywords = payload.get('keywords', [])
            all_keywords.update(keywords)

        # Get top categories and keywords
        top_categories = categories.most_common(5)
        top_keywords = all_keywords.most_common(10)

        # Generate summary
        summary = f"My knowledge base contains {entry_count} entries covering various topics. "
        summary += "The main categories include: " + ", ".join(f"{cat} ({count})" for cat, count in top_categories) + ". "
        summary += "Some key topics covered are: " + ", ".join(keyword for keyword, _ in top_keywords) + "."

        return summary
    except Exception as e:
        logger.error(f"Error generating knowledge base summary: {str(e)}")
        return "I have information about SRH Hochschule Heidelberg and Applied Computer Science, but I'm unable to provide a detailed summary of my knowledge base at the moment."

@app.post("/search")
async def search(query: Query, request: Request):
    rate_limit(request)
    
    try:
        # Check if the query is a simple greeting
        if query.text.lower() in ["hi", "hello", "hey"]:
            return {
                "search_results": [],
                "ai_response": "Hello! How can I assist you with information about SRH Hochschule Heidelberg today?"
            }

        # Check if the query is about the knowledge base content
        if query.text.lower() in ["what is in your knowledge base?", "what do you know?", "what information do you have?"]:
            summary = get_knowledge_base_summary()
            return {
                "search_results": [],
                "ai_response": summary
            }

        preprocessed_query = preprocess_query(query.text)
        expanded_queries = expand_query(preprocessed_query)
        
        all_results = []
        for expanded_query in expanded_queries:
            search_results = search_qdrant(expanded_query, query.filters)
            all_results.extend(search_results)
        
        # Deduplicate and sort results
        unique_results = list({r.id: r for r in all_results}.values())
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        results = [extract_relevant_info(result) for result in unique_results[:5]]
        
        context = "\n\n".join([r.content for r in results])
        
        if not results:
            ai_response = "I couldn't find any specific information related to your query. Can you please provide more details or ask a more specific question about SRH Hochschule Heidelberg?"
        else:
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
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")

@app.post("/feedback")
async def submit_feedback(feedback: dict, request: Request):
    rate_limit(request)
    # Implement feedback collection (e.g., store in a database or file)
    logger.info(f"Received feedback: {feedback}")
    return {"status": "Feedback received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)