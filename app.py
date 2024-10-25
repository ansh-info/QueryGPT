import streamlit as st
import qdrant_client
from qdrant_client.http import models
import requests
import logging
from functools import lru_cache
from typing import List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
import time

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Qdrant client
@st.cache_resource
def init_qdrant():
    return qdrant_client.QdrantClient("localhost", port=6333)

# Initialize Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api"

# Cache for embeddings
@st.cache_data(ttl=3600)
def encode_text(text: str):
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
        st.error(f"Error getting embedding: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def query_ollama(prompt: str):
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
        st.error(f"Error generating response: {str(e)}")
        return None

def search_qdrant(client, query: str, filters: Optional[dict] = None, limit: int = 5):
    query_vector = encode_text(query)
    if query_vector is None:
        return []
    
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
        search_result = client.search(
            collection_name="knowledge_base",
            query_vector=query_vector,
            query_filter=models.Filter(
                must=filter_conditions
            ) if filter_conditions else None,
            limit=limit
        )
        return search_result
    except Exception as e:
        st.error(f"Error searching Qdrant: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def get_knowledge_base_summary(client):
    try:
        entries = client.scroll(
            collection_name="knowledge_base",
            limit=1000
        )[0]

        categories = Counter()
        all_keywords = Counter()
        entry_count = len(entries)
        
        for entry in entries:
            payload = entry.payload
            categories[payload.get('category', 'Uncategorized')] += 1
            keywords = payload.get('keywords', [])
            all_keywords.update(keywords)

        top_categories = categories.most_common(5)
        top_keywords = all_keywords.most_common(10)

        summary = f"Knowledge base contains {entry_count} entries covering various topics. "
        summary += "Main categories: " + ", ".join(f"{cat} ({count})" for cat, count in top_categories) + ". "
        summary += "Key topics: " + ", ".join(keyword for keyword, _ in top_keywords) + "."

        return summary
    except Exception as e:
        st.error(f"Error generating knowledge base summary: {str(e)}")
        return "Unable to generate knowledge base summary at the moment."

def get_database_keywords(client) -> List[str]:
    entries = client.scroll(
        collection_name="knowledge_base",
        limit=1000
    )[0]

    all_keywords = []
    for entry in entries:
        keywords = entry.payload.get('keywords', [])
        all_keywords.extend(keywords)

    return list(set(all_keywords))

def is_query_relevant(client, query: str, threshold: float = 0.05) -> Tuple[bool, float]:
    keywords = get_database_keywords(client)
    texts = keywords + [query]
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    query_vec = tfidf_matrix[-1]
    keyword_vecs = tfidf_matrix[:-1]
    similarities = cosine_similarity(query_vec, keyword_vecs)
    
    max_similarity = np.max(similarities)
    is_relevant = max_similarity > threshold
    
    return bool(is_relevant), float(max_similarity)

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_chat' not in st.session_state:
        st.session_state.current_chat = None

def main():
    st.set_page_config(
        page_title="Knowledge Base Search",
        page_icon="🔍",
        layout="wide"
    )

    initialize_session_state()
    qdrant = init_qdrant()

    # Sidebar
    with st.sidebar:
        st.title("Knowledge Base Search")
        st.markdown("---")
        
        if st.button("New Chat", key="new_chat"):
            st.session_state.messages = []
            st.session_state.current_chat = time.time()
        
        st.markdown("---")
        if st.button("Show Knowledge Base Summary"):
            summary = get_knowledge_base_summary(qdrant)
            st.info(summary)

    # Main chat interface
    st.title("Chat Interface")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "search_results" in message and message["search_results"]:
                with st.expander("Related Information"):
                    for result in message["search_results"]:
                        st.markdown(f"**Content:** {result['content']}")
                        st.markdown(f"**Score:** {result['score']:.4f}")
                        if result.get('category'):
                            st.markdown(f"**Category:** {result['category']}")
                        if result.get('source'):
                            st.markdown(f"**Source:** {result['source']}")
                        st.markdown("---")

    # Chat input
    if prompt := st.chat_input("Ask a question..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Handle greetings
        if prompt.lower() in ["hi", "hello", "hey"]:
            response = "Hello! How can I assist you with information about SRH Hochschule Heidelberg today?"
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
            return

        # Handle knowledge base inquiry
        if prompt.lower() in ["what is in your knowledge base?", "what do you know?", "what information do you have?"]:
            response = get_knowledge_base_summary(qdrant)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })
            return

        # Process regular query
        is_relevant, relevance_score = is_query_relevant(qdrant, prompt)
        
        if is_relevant:
            search_results = search_qdrant(qdrant, prompt)
            results = []
            
            for result in search_results:
                results.append({
                    "content": result.payload.get('original_content', ''),
                    "score": result.score,
                    "category": result.payload.get('category'),
                    "source": result.payload.get('source')
                })

            context = "\n\n".join([r["content"] for r in results])
            
            prompt_template = f"""Based on the following context from the knowledge base, answer the question:

Context:
{context}

Question: {prompt}

Answer:"""
            
            ai_response = query_ollama(prompt_template)
        else:
            prompt_template = f"""You are an AI assistant for SRH Hochschule Heidelberg. Please answer this question using your general knowledge:

Question: {prompt}

Answer:"""
            
            ai_response = query_ollama(prompt_template)
            results = []

        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_response,
            "search_results": results,
            "is_from_knowledge_base": is_relevant,
            "relevance_score": relevance_score
        })

if __name__ == "__main__":
    main()