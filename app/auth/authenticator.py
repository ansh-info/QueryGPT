import streamlit as st
import yaml
from yaml.loader import SafeLoader
import os

def setup_auth():
    """Setup and handle authentication"""
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
    if 'username' not in st.session_state:
        st.session_state.username = None

    # Load config
    config_path = os.path.join('config', 'config.yaml')
    try:
        with open(config_path) as file:
            config = yaml.load(file, Loader=SafeLoader)
    except FileNotFoundError:
        st.error(f"Config file not found at {config_path}")
        return False
    except Exception as e:
        st.error(f"Error loading config: {str(e)}")
        return False

    if st.session_state.authentication_status is not True:
        title = st.empty()
        title.title('Welcome to Knowledge Base Search')
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            username = st.text_input('Username')
        with col2:
            password = st.text_input('Password', type='password')

        if st.button('Login'):
            if username in config['credentials']['usernames']:
                if config['credentials']['usernames'][username]['password'] == password:
                    st.session_state.authentication_status = True
                    st.session_state.username = username
                    title.empty()
                    st.experimental_rerun()
                else:
                    st.error('Incorrect password')
            else:
                st.error('Username not found')
        
        return False

    return True

def get_username():
    """Get the current authenticated username"""
    return st.session_state.get('username', None)

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get('authentication_status', False)

def logout():
    """Log out the current user"""
    st.session_state.authentication_status = None
    st.session_state.username = None