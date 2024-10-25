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
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Knowledge Base Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Qdrant client
@st.cache_resource
def init_qdrant():
    return qdrant_client.QdrantClient("localhost", port=6333)

# Initialize Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api"

# Rate limiting
RATE_LIMIT = 10
RATE_LIMIT_DURATION = 60

# Session state initialization
def initialize_session_state():
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'chats' not in st.session_state:
        st.session_state.chats = []
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    if 'request_history' not in st.session_state:
        st.session_state.request_history = {}
    if 'expanded_results' not in st.session_state:
        st.session_state.expanded_results = {}

def rate_limit_check():
    client = "streamlit_user"  # Using a default client ID for Streamlit
    current_time = time.time()
    
    if client in st.session_state.request_history:
        request_times = st.session_state.request_history[client]
        request_times = [t for t in request_times if current_time - t < RATE_LIMIT_DURATION]
        
        if len(request_times) >= RATE_LIMIT:
            st.error("Rate limit exceeded. Please wait before making more requests.")
            return False
    else:
        request_times = []
    
    request_times.append(current_time)
    st.session_state.request_history[client] = request_times
    return True

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

def preprocess_query(query: str) -> str:
    return query.lower().strip()

def expand_query(query: str) -> List[str]:
    expanded = [query]
    if "srh" in query:
        expanded.append(query.replace("srh", "srh hochschule heidelberg"))
    return expanded

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

def process_query(query: str, client):
    if not rate_limit_check():
        return

    try:
        # Handle greetings
        if query.lower() in ["hi", "hello", "hey"]:
            return {
                "type": "ai",
                "content": "Hello! How can I assist you with information about SRH Hochschule Heidelberg today?",
                "is_from_knowledge_base": False,
                "relevance_score": 0.0,
                "search_results": [],
                "search_info": "Greeting detected"
            }

        # Handle knowledge base inquiries
        if query.lower() in ["what is in your knowledge base?", "what do you know?", "what information do you have?"]:
            summary = get_knowledge_base_summary(client)
            return {
                "type": "ai",
                "content": summary,
                "is_from_knowledge_base": True,
                "relevance_score": 1.0,
                "search_results": [],
                "search_info": "Knowledge base summary"
            }

        preprocessed_query = preprocess_query(query)
        is_relevant, relevance_score = is_query_relevant(client, preprocessed_query)

        if is_relevant:
            expanded_queries = expand_query(preprocessed_query)
            all_results = []
            for expanded_query in expanded_queries:
                search_results = search_qdrant(client, expanded_query)
                all_results.extend(search_results)
            
            results = []
            for result in all_results[:5]:
                results.append({
                    "content": result.payload.get('original_content', ''),
                    "score": result.score,
                    "category": result.payload.get('category'),
                    "source": result.payload.get('source')
                })

            context = "\n\n".join([r["content"] for r in results])
            
            prompt = f"""Based on the following context from the knowledge base, answer the question:

Context:
{context}

Question: {query}

Answer:"""
            
            ai_response = query_ollama(prompt)
        else:
            prompt = f"""You are an AI assistant for SRH Hochschule Heidelberg. Please answer this question using your general knowledge:

Question: {query}

Answer:"""
            
            ai_response = query_ollama(prompt)
            results = []

        return {
            "type": "ai",
            "content": ai_response,
            "is_from_knowledge_base": is_relevant,
            "relevance_score": relevance_score,
            "search_results": results,
            "search_info": f"Relevance: {relevance_score:.4f}"
        }

    except Exception as e:
        st.error(f"Error processing query: {str(e)}")
        return None

def render_message(message, message_index: int):
    if message["type"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    elif message["type"] == "ai":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            
            # Show source information
            if message.get("is_from_knowledge_base"):
                st.info(f"Source: Knowledge Base (Relevance: {message['relevance_score']*100:.2f}%)")
                
                # Display search results in an expander
                if message.get("search_results"):
                    with st.expander("View Related Information"):
                        for idx, result in enumerate(message["search_results"]):
                            st.markdown(f"**Content:** {result['content']}")
                            st.markdown(f"**Score:** {result['score']:.4f}")
                            if result.get('category'):
                                st.markdown(f"**Category:** {result['category']}")
                            if result.get('source'):
                                st.markdown(f"**Source:** {result['source']}")
                            st.markdown("---")
            
            # Feedback buttons with unique keys including timestamp
            timestamp = int(time.time() * 1000)  # millisecond timestamp
            col1, col2 = st.columns([1, 20])
            with col1:
                st.button("👍", key=f"thumbs_up_{message_index}_{timestamp}")
                st.button("👎", key=f"thumbs_down_{message_index}_{timestamp}")

def main():
    initialize_session_state()
    client = init_qdrant()

    # Sidebar
    with st.sidebar:
        st.title("Knowledge Base Search")
        
        if st.button("New Chat"):
            st.session_state.conversation = []
            st.session_state.current_chat_id = time.time()
            st.rerun()
        
        st.markdown("---")
        
        if st.button("Show Knowledge Base Summary"):
            summary = get_knowledge_base_summary(client)
            st.info(summary)
        
        # Chat history
        st.markdown("### Chat History")
        for chat in st.session_state.chats:
            if st.button(f"Chat {chat['id']}", key=f"chat_{chat['id']}"):
                st.session_state.current_chat_id = chat['id']
                st.session_state.conversation = chat.get('messages', [])
                st.rerun()

    # Main chat interface
    st.title("Chat Interface")

    # Display conversation with indexed messages
    for idx, message in enumerate(st.session_state.conversation):
        render_message(message, idx)

    # Chat input
    if query := st.chat_input("Ask a question..."):
        # Add user message
        user_message = {"type": "user", "content": query}
        st.session_state.conversation.append(user_message)
        
        # Process query and add AI response
        ai_response = process_query(query, client)
        if ai_response:
            st.session_state.conversation.append(ai_response)
            
            # Update chat history
            if st.session_state.current_chat_id:
                chat_exists = False
                for chat in st.session_state.chats:
                    if chat['id'] == st.session_state.current_chat_id:
                        chat['messages'] = st.session_state.conversation
                        chat_exists = True
                        break
                if not chat_exists:
                    st.session_state.chats.append({
                        'id': st.session_state.current_chat_id,
                        'messages': st.session_state.conversation
                    })
        
        st.rerun()

if __name__ == "__main__":
    main()