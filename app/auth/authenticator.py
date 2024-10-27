import streamlit as st
import yaml
from yaml.loader import SafeLoader
import os
from datetime import datetime
import bcrypt

class Authenticator:
    def __init__(self):
        self.config_path = os.path.join('config', 'config.yaml')
        self.config = self.load_config()

    def load_config(self):
        """Load the configuration file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as file:
                    return yaml.load(file, Loader=SafeLoader)
            return self.create_default_config()
        except Exception as e:
            st.error(f"Error loading config: {str(e)}")
            return self.create_default_config()

    def create_default_config(self):
        """Create a default configuration"""
        return {
            'credentials': {
                'usernames': {}
            }
        }

    def save_config(self):
        """Save the current configuration"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as file:
            yaml.dump(self.config, file)

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    def signup(self, username: str, email: str, password: str, name: str) -> tuple:
        """Handle user signup"""
        if username in self.config['credentials']['usernames']:
            return False, "Username already exists"

        # Add new user
        self.config['credentials']['usernames'][username] = {
            'email': email,
            'name': name,
            'password': self.hash_password(password),
            'created_at': datetime.now().isoformat()
        }
        
        # Save updated config
        self.save_config()
        return True, "Signup successful"

    def login(self, username: str, password: str) -> tuple:
        """Handle user login"""
        if username not in self.config['credentials']['usernames']:
            return False, "Username not found"
        
        user_data = self.config['credentials']['usernames'][username]
        if self.verify_password(password, user_data['password']):
            return True, "Login successful"
        
        return False, "Incorrect password"

def setup_auth():
    """Setup and handle authentication"""
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False

    authenticator = Authenticator()

    st.title('Welcome to Knowledge Base Search')

    # Toggle between login and signup
    if not st.session_state.show_signup:
        # Login Form
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            
            col1, col2 = st.columns([1, 1])
            with col1:
                login_submitted = st.form_submit_button('Login')
            with col2:
                if st.form_submit_button('Need to Sign Up?'):
                    st.session_state.show_signup = True
                    st.rerun()

            if login_submitted and username and password:
                success, message = authenticator.login(username, password)
                if success:
                    st.session_state.authentication_status = True
                    st.session_state.username = username
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    else:
        # Signup Form
        with st.form("signup_form"):
            st.subheader("Sign Up")
            new_username = st.text_input('Choose Username')
            new_password = st.text_input('Choose Password', type='password')
            confirm_password = st.text_input('Confirm Password', type='password')
            email = st.text_input('Email')
            name = st.text_input('Full Name')
            
            col1, col2 = st.columns([1, 1])
            with col1:
                signup_submitted = st.form_submit_button('Sign Up')
            with col2:
                if st.form_submit_button('Back to Login'):
                    st.session_state.show_signup = False
                    st.rerun()

            if signup_submitted:
                if not all([new_username, new_password, confirm_password, email, name]):
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = authenticator.signup(new_username, email, new_password, name)
                    if success:
                        st.success(message)
                        st.session_state.show_signup = False
                        st.rerun()
                    else:
                        st.error(message)

    return st.session_state.get('authentication_status', False)

def get_username():
    """Get the current authenticated username"""
    return st.session_state.get('username', None)

def get_user_info():
    """Get information about the current user"""
    authenticator = Authenticator()
    username = get_username()
    if username:
        return authenticator.config['credentials']['usernames'][username]
    return None

def logout():
    """Log out the current user"""
    st.session_state.authentication_status = None
    st.session_state.username = None
    st.session_state.show_signup = False