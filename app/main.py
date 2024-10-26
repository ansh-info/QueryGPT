import streamlit as st
from auth.authenticator import setup_auth
from core.logging import setup_logging
from core.cache import CacheManager
from services.qdrant_service import QdrantService
from services.ollama_service import OllamaService
from services.query_service import QueryProcessor
from database.session import get_db_session
from utils.analysis import FeedbackAnalyzer
import time
from datetime import datetime

# Setup and configuration
logger = setup_logging()
cache_manager = CacheManager()

def initialize_session_state():
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'chats' not in st.session_state:
        st.session_state.chats = []
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None

def render_message(message, message_index: int):
    if message["type"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    elif message["type"] == "ai":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            
            if message.get("is_from_knowledge_base"):
                st.info(f"Source: Knowledge Base (Relevance: {message['relevance_score']*100:.2f}%)")
                
                if message.get("search_results"):
                    with st.expander("View Related Information"):
                        for result in message["search_results"]:
                            st.markdown(f"**Content:** {result['content']}")
                            st.markdown(f"**Score:** {result['score']:.4f}")
                            if result.get('category'):
                                st.markdown(f"**Category:** {result['category']}")
                            if result.get('source'):
                                st.markdown(f"**Source:** {result['source']}")
                            st.markdown("---")
            
            timestamp = int(time.time() * 1000)
            col1, col2 = st.columns([1, 20])
            with col1:
                if st.button("👍", key=f"thumbs_up_{message_index}_{timestamp}"):
                    feedback_analyzer.store_feedback(
                        message["content"], 
                        "positive",
                        datetime.now()
                    )
                if st.button("👎", key=f"thumbs_down_{message_index}_{timestamp}"):
                    feedback_analyzer.store_feedback(
                        message["content"], 
                        "negative",
                        datetime.now()
                    )

def main():
    st.set_page_config(
        page_title="Knowledge Base Search",
        page_icon="🔍",
        layout="wide"
    )

    # Initialize services
    qdrant_service = QdrantService()
    ollama_service = OllamaService()
    query_processor = QueryProcessor()
    feedback_analyzer = FeedbackAnalyzer()
    
    initialize_session_state()

    # Sidebar
    with st.sidebar:
        st.title("Knowledge Base Search")
        
        if st.button("New Chat"):
            st.session_state.conversation = []
            st.session_state.current_chat_id = time.time()
            st.rerun()
        
        st.markdown("---")
        
        if st.button("Show Knowledge Base Summary"):
            summary = qdrant_service.get_knowledge_base_summary()
            st.info(summary)
        
        st.markdown("### Chat History")
        for chat in st.session_state.chats:
            if st.button(f"Chat {chat['id']}", key=f"chat_{chat['id']}"):
                st.session_state.current_chat_id = chat['id']
                st.session_state.conversation = chat.get('messages', [])
                st.rerun()

        # Analytics section
        if st.checkbox("Show Analytics"):
            st.markdown("### Analytics")
            feedback_stats = feedback_analyzer.analyze_feedback()
            st.metric("Satisfaction Rate", f"{feedback_stats['satisfaction_rate']:.2%}")
            st.metric("Total Responses", feedback_stats['total_responses'])

    # Main chat interface
    st.title("Chat Interface")

    # Display conversation
    for idx, message in enumerate(st.session_state.conversation):
        render_message(message, idx)

    # Chat input
    if query := st.chat_input("Ask a question..."):
        # Check cache first
        cached_response = cache_manager.get_cached_response(query)
        
        if cached_response:
            response = cached_response
            st.success("Retrieved from cache")
        else:
            # Process new query
            with st.spinner("Processing your query..."):
                response = query_processor.process_query(
                    query,
                    qdrant_service,
                    ollama_service
                )
                cache_manager.cache_response(query, response)

        # Update conversation
        st.session_state.conversation.extend([
            {"type": "user", "content": query},
            response
        ])

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