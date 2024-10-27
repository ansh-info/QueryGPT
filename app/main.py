import streamlit as st
from auth.authenticator import setup_auth, get_username, logout
from core.logging import setup_logging
from core.cache import CacheManager
from services.qdrant_service import QdrantService
from services.ollama_service import OllamaService
from services.query_service import QueryProcessor
from utils.analysis import FeedbackAnalyzer
import time
from datetime import datetime
import os
import sys
import logging

# Add the app directory to the Python path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.append(app_dir)

from app.auth.authenticator import setup_auth, get_username, logout
from app.core.cache import CacheManager
from app.services.qdrant_service import QdrantService
from app.services.ollama_service import OllamaService
from app.services.query_service import QueryProcessor
from app.utils.analysis import FeedbackAnalyzer

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', f'app_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Setup and configuration
logger = setup_logging()
cache_manager = CacheManager()
feedback_analyzer = FeedbackAnalyzer()  # Move to global scope for access in render_message

def initialize_session_state():
    """Initialize session state variables"""
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    if 'chats' not in st.session_state:
        st.session_state.chats = []
    if 'current_chat_id' not in st.session_state:
        st.session_state.current_chat_id = None
    if 'expanded_results' not in st.session_state:
        st.session_state.expanded_results = {}

def render_message(message, message_index: int):
    """Render a single message in the chat interface"""
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
                        for idx, result in enumerate(message["search_results"]):
                            result_key = f"{message_index}_{idx}"
                            if result_key not in st.session_state.expanded_results:
                                st.session_state.expanded_results[result_key] = False
                            
                            col1, col2 = st.columns([20, 1])
                            with col1:
                                st.markdown(f"**Content:** {result['content']}")
                            with col2:
                                if st.button("🔍", key=f"expand_{result_key}"):
                                    st.session_state.expanded_results[result_key] = \
                                        not st.session_state.expanded_results[result_key]
                            
                            if st.session_state.expanded_results[result_key]:
                                st.markdown(f"**Score:** {result['score']:.4f}")
                                if result.get('category'):
                                    st.markdown(f"**Category:** {result['category']}")
                                if result.get('source'):
                                    st.markdown(f"**Source:** {result['source']}")
                            st.markdown("---")
            
            # Feedback buttons
            timestamp = int(time.time() * 1000)
            col1, col2 = st.columns([1, 20])
            with col1:
                if st.button("👍", key=f"thumbs_up_{message_index}_{timestamp}"):
                    feedback_analyzer.store_feedback(
                        message["content"], 
                        "positive",
                        datetime.now()
                    )
                    st.success("Thank you for your feedback!")
                if st.button("👎", key=f"thumbs_down_{message_index}_{timestamp}"):
                    feedback_analyzer.store_feedback(
                        message["content"], 
                        "negative",
                        datetime.now()
                    )
                    st.error("Thank you for your feedback!")

def format_chat_title(chat):
    """Format the chat title for display"""
    first_message = next((m for m in chat.get('messages', []) if m['type'] == 'user'), None)
    if first_message:
        title = first_message['content'][:30] + "..." if len(first_message['content']) > 30 else first_message['content']
    else:
        title = f"Chat {chat['id']}"
    return title

def main():
    st.set_page_config(
        page_title="Knowledge Base Search",
        page_icon="🔍",
        layout="wide"
    )

    # Authentication check
    if not setup_auth():
        return

    initialize_session_state()

    # Initialize services
    try:
        qdrant_service = QdrantService()
        ollama_service = OllamaService()
        query_processor = QueryProcessor()
    except Exception as e:
        st.error(f"Error initializing services: {str(e)}")
        return

    # Sidebar
    with st.sidebar:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title("Knowledge Base")
        with col2:
            if st.button("Logout"):
                logout()
                st.rerun()
        
        if st.button("New Chat", key="new_chat"):
            st.session_state.conversation = []
            st.session_state.current_chat_id = time.time()
            st.rerun()
        
        st.markdown("---")
        
        if st.button("Show Knowledge Base Summary"):
            try:
                summary = qdrant_service.get_knowledge_base_summary()
                st.info(summary)
            except Exception as e:
                st.error(f"Error fetching summary: {str(e)}")
        
        # Chat history
        st.markdown("### Chat History")
        for chat in st.session_state.chats:
            chat_title = format_chat_title(chat)
            if st.button(chat_title, key=f"chat_{chat['id']}"):
                st.session_state.current_chat_id = chat['id']
                st.session_state.conversation = chat.get('messages', [])
                st.rerun()

        # Analytics section
        if st.checkbox("Show Analytics", key="show_analytics"):
            st.markdown("### Analytics")
            try:
                feedback_stats = feedback_analyzer.analyze_feedback()
                st.metric("Satisfaction Rate", f"{feedback_stats['satisfaction_rate']:.2%}")
                st.metric("Total Responses", feedback_stats['total_responses'])
                
                if feedback_stats.get('recent_feedback'):
                    st.markdown("### Recent Feedback")
                    for feedback in feedback_stats['recent_feedback'][:5]:
                        st.markdown(f"- {feedback['feedback']} ({feedback['timestamp'].strftime('%Y-%m-%d %H:%M')})")
            except Exception as e:
                st.error(f"Error loading analytics: {str(e)}")

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
                try:
                    response = query_processor.process_query(
                        query,
                        qdrant_service,
                        ollama_service
                    )
                    cache_manager.cache_response(query, response)
                except Exception as e:
                    logger.error(f"Error processing query: {str(e)}")
                    response = {
                        "type": "error",
                        "content": "I apologize, but I encountered an error processing your request. Please try again."
                    }

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
                    'messages': st.session_state.conversation,
                    'timestamp': datetime.now()
                })
        
        st.rerun()

if __name__ == "__main__":
    main()