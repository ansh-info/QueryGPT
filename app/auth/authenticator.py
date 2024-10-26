import streamlit as st
import yaml
from yaml.loader import SafeLoader
import os

class Authenticator:
    def __init__(self, config_path: str):
        with open(config_path) as file:
            self.config = yaml.load(file, Loader=SafeLoader)
    
    def login(self):
        """Handle the login process"""
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = None
        if 'username' not in st.session_state:
            st.session_state.username = None

        if st.session_state.authentication_status is not True:
            title = st.empty()
            title.title('Welcome to Knowledge Base Search')
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                username = st.text_input('Username')
            with col2:
                password = st.text_input('Password', type='password')

            if st.button('Login'):
                if username in self.config['credentials']['usernames']:
                    if self.config['credentials']['usernames'][username]['password'] == password:
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