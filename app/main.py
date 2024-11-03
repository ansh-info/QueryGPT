import streamlit as st
import os
import sys
import logging
from datetime import datetime
import time

# Add the app directory to the Python path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.append(app_dir)

from auth.authenticator import setup_auth, get_username, get_user_info, logout
from core.cache import CacheManager
from services.qdrant_service import QdrantService
from services.ollama_service import OllamaService
from services.query_service import QueryProcessor
from services.enhanced_search_service import EnhancedSearchService, SearchFilter
from utils.analysis import FeedbackAnalyzer
from app.auth.authenticator import setup_auth, get_username, get_user_info, logout

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', f'app_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize global services
cache_manager = CacheManager()
feedback_analyzer = FeedbackAnalyzer()
qdrant_service = None
enhanced_search_service = None 

def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        'conversation': [],
        'chats': [],
        'current_chat_id': None,
        'expanded_results': {},
        'theme': 'Light',
        'show_timestamps': True,
        'show_sources': True,
        'chat_expanded': True,
        'auto_scroll': True
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_search_interface():
    """Render enhanced search interface"""
    global enhanced_search_service
    
    st.markdown("### Advanced Search")
    
    # Search input with suggestions
    query = st.text_input("Search the knowledge base...")
    
    # Search filters
    with st.expander("Search Filters"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", value=None)
        with col2:
            end_date = st.date_input("To Date", value=None)
            
        # Category filter
        categories = qdrant_service.get_categories()
        selected_categories = st.multiselect("Categories", categories)
        
        # Source filter
        sources = qdrant_service.get_sources()
        selected_sources = st.multiselect("Sources", sources)
        
    if query:
        # Create search filter with proper datetime conversion
        search_filter = SearchFilter(
            date_range=(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time())
            ) if start_date and end_date else None,
            categories=selected_categories if selected_categories else None,
            sources=selected_sources if selected_sources else None,
            max_results=10
        )
        
        # Perform search
        with st.spinner("Searching..."):
            try:
                results = enhanced_search_service.search(query, search_filter)
                
                # Display results
                if results:
                    # Show facets in sidebar
                    facets = enhanced_search_service.get_facets(results)
                    with st.sidebar:
                        st.markdown("### Search Facets")
                        st.markdown("#### Categories")
                        for category, count in facets['categories'].items():
                            st.markdown(f"- {category}: {count}")
                        
                        if facets['sources']:
                            st.markdown("#### Sources")
                            for source, count in facets['sources'].items():
                                st.markdown(f"- {source}: {count}")
                            
                    # Display results
                    st.markdown(f"Found {len(results)} results")
                    for result in results:
                        with st.container():
                            st.markdown(f"**Score**: {result.score:.2f}")
                            st.markdown(f"**Category**: {result.category}")
                            st.markdown(f"**Source**: {result.source}")
                            
                            # Show highlights
                            if result.highlights:
                                with st.expander("Matching Excerpts"):
                                    for highlight in result.highlights:
                                        st.markdown(f"...{highlight}...")
                            
                            # Show full content
                            with st.expander("Full Content"):
                                st.markdown(result.content)
                            
                            st.markdown("---")
                else:
                    st.info("No results found.")
            except Exception as e:
                logger.error(f"Search error: {str(e)}")
                st.error("An error occurred while searching. Please try again.")

def handle_error(error: Exception, error_type: str = "General"):
    """Handle errors with user-friendly messages"""
    logger.error(f"{error_type} Error: {str(error)}")
    if error_type == "Service":
        st.error("Service temporarily unavailable. Please try again later.")
    elif error_type == "Authentication":
        st.error("Authentication error. Please log in again.")
    else:
        st.error("An unexpected error occurred. Please try again.")

def format_chat_title(chat):
    """Format the chat title for display"""
    first_message = next((m for m in chat.get('messages', []) if m['type'] == 'user'), None)
    if first_message:
        title = first_message['content'][:30] + "..." if len(first_message['content']) > 30 else first_message['content']
    else:
        title = f"Chat {chat['id']}"
    return title

def manage_chat_history():
    """Manage and organize chat history"""
    if len(st.session_state.chats) > 0:
        st.sidebar.markdown("### Manage Chats")
        
        # Sort chats by date
        sorted_chats = sorted(
            st.session_state.chats,
            key=lambda x: x.get('timestamp', datetime.now()),
            reverse=True
        )
        
        # Display chats with delete option
        for chat in sorted_chats:
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                title = format_chat_title(chat)
                if st.button(title, key=f"chat_{chat['id']}"):
                    st.session_state.current_chat_id = chat['id']
                    st.session_state.conversation = chat.get('messages', [])
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{chat['id']}"):
                    st.session_state.chats.remove(chat)
                    if chat['id'] == st.session_state.current_chat_id:
                        st.session_state.current_chat_id = None
                        st.session_state.conversation = []
                    st.rerun()

def render_settings():
    """Render settings section in sidebar"""
    with st.expander("Settings"):
        # Theme settings
        theme_options = ['Light', 'Dark']
        current_theme = st.session_state.get('theme', 'Light')
        try:
            theme_index = theme_options.index(current_theme.title())
        except ValueError:
            theme_index = 0
            
        selected_theme = st.radio(
            "Theme",
            options=theme_options,
            index=theme_index,
            key='theme_setting'
        )
        st.session_state.theme = selected_theme

        # Display settings
        st.checkbox(
            "Show Timestamps",
            value=st.session_state.get('show_timestamps', True),
            key='show_timestamps'
        )
        st.checkbox(
            "Show Sources",
            value=st.session_state.get('show_sources', True),
            key='show_sources'
        )

        # Chat settings
        st.checkbox(
            "Auto-scroll Chat",
            value=st.session_state.get('auto_scroll', True),
            key='auto_scroll'
        )

def render_message(message, message_index: int):
    """Render a single message in the chat interface"""
    if message["type"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
            if st.session_state.show_timestamps and message.get("timestamp"):
                st.caption(message["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))
    
    elif message["type"] == "ai":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            
            if message.get("timestamp") and st.session_state.show_timestamps:
                st.caption(message["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))
            
            if message.get("is_from_knowledge_base") and st.session_state.show_sources:
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

def show_analytics():
    """Display analytics dashboard"""
    st.markdown("### Analytics")
    
    # Get detailed statistics
    feedback_stats = feedback_analyzer.get_detailed_stats()
    
    # Display key metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Feedback", feedback_stats.get('total_feedback', 0))
        st.metric("Positive Feedback", feedback_stats.get('positive_feedback', 0))
    with col2:
        st.metric("Satisfaction Rate", f"{feedback_stats.get('satisfaction_rate', 0):.2%}")
    
    # Display feedback timeline
    if feedback_stats.get('feedback_by_hour'):
        st.markdown("### Feedback Timeline")
        st.line_chart(feedback_stats['feedback_by_hour'])
    
    # Display recent feedback
    if feedback_stats.get('recent_feedback'):
        st.markdown("### Recent Feedback")
        for feedback in feedback_stats['recent_feedback']:
            st.markdown(
                f"- {feedback['feedback']} "
                f"({feedback['timestamp'].strftime('%Y-%m-%d %H:%M')})"
            )

def main():
    st.set_page_config(
        page_title="Knowledge Base Search",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Authentication
    if not setup_auth():
        st.stop()

    # Get user info
    username = get_username()
    user_info = get_user_info()

    initialize_session_state()

    # Initialize services
    try:
        global qdrant_service, enhanced_search_service 
        qdrant_service = QdrantService()
        ollama_service = OllamaService()
        query_processor = QueryProcessor()
        enhanced_search_service = EnhancedSearchService(qdrant_service, ollama_service)
    except Exception as e:
        handle_error(e, "Service")
        return

    # Sidebar
    with st.sidebar:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f"Welcome, {user_info['name']}")
        with col2:
            if st.button("Profile"):
                st.switch_page("pages/profile.py")
            if st.button("Logout"):
                logout()
                st.rerun()
        
        # Settings section
        render_settings()
        
        # New Chat button
        if st.button("New Chat", key="new_chat"):
            st.session_state.conversation = []
            st.session_state.current_chat_id = time.time()
            st.rerun()
        
        st.markdown("---")
        
        # Knowledge Base Summary
        if st.button("Show Knowledge Base Summary"):
            try:
                summary = qdrant_service.get_knowledge_base_summary()
                st.info(summary['text'] if isinstance(summary, dict) else summary)
            except Exception as e:
                handle_error(e, "Service")
        
        # Chat Management
        manage_chat_history()
        
        # Analytics
        if st.checkbox("Show Analytics", key="show_analytics"):
            show_analytics()

    # Main interface with tabs
    tab1, tab2 = st.tabs(["Chat", "Advanced Search"])
    
    with tab1:
        st.title("Chat Interface")
        
        # Display conversation
        for idx, message in enumerate(st.session_state.conversation):
            render_message(message, idx)

        # Chat input
        if query := st.chat_input("Ask a question..."):
            # Check cache
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

            # Add timestamp to messages
            user_message = {
                "type": "user",
                "content": query,
                "timestamp": datetime.now()
            }
            response["timestamp"] = datetime.now()

            # Update conversation
            st.session_state.conversation.extend([user_message, response])

            # Update chat history
            if st.session_state.current_chat_id:
                chat_exists = False
                for chat in st.session_state.chats:
                    if chat['id'] == st.session_state.current_chat_id:
                        chat['messages'] = st.session_state.conversation
                        chat['timestamp'] = datetime.now()
                        chat_exists = True
                        break
                if not chat_exists:
                    st.session_state.chats.append({
                        'id': st.session_state.current_chat_id,
                        'messages': st.session_state.conversation,
                        'timestamp': datetime.now()
                    })
            
            st.rerun()
            
    with tab2:
        render_search_interface()

if __name__ == "__main__":
    main()