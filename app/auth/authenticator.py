import streamlit as st
import yaml
from yaml.loader import SafeLoader
import os
import bcrypt
from datetime import datetime, timedelta
import jwt
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class Authenticator:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize Authenticator with config path"""
        self.config_path = config_path
        self.config = self.load_config()
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')  # In production, use env var
        self.session_duration = timedelta(days=1)

    def load_config(self) -> Dict:
        """Load configuration from yaml file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as file:
                    return yaml.load(file, Loader=SafeLoader)
            return self.create_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return self.create_default_config()

    def create_default_config(self) -> Dict:
        """Create default configuration"""
        return {
            'credentials': {
                'usernames': {}
            },
            'cookie': {
                'name': 'auth_token',
                'expiry_days': 1,
                'key': 'some_signature_key'
            }
        }

    def save_config(self):
        """Save current configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as file:
                yaml.dump(self.config, file)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

    def create_token(self, username: str) -> str:
        """Create JWT token for user"""
        try:
            payload = {
                'username': username,
                'exp': datetime.utcnow() + self.session_duration
            }
            return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        except Exception as e:
            logger.error(f"Error creating token: {str(e)}")
            raise

    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return username"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload.get('username')
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return None

    def signup(self, username: str, password: str, email: str, name: str) -> Tuple[bool, str]:
        """Handle user signup"""
        try:
            if username in self.config['credentials']['usernames']:
                return False, "Username already exists"

            if not self._validate_password(password):
                return False, "Password does not meet requirements"

            if not self._validate_email(email):
                return False, "Invalid email format"

            self.config['credentials']['usernames'][username] = {
                'email': email,
                'name': name,
                'password': self.hash_password(password),
                'created_at': datetime.now().isoformat(),
                'role': 'user'  # Default role
            }
            
            self.save_config()
            logger.info(f"New user signed up: {username}")
            return True, "Signup successful"
        except Exception as e:
            logger.error(f"Error during signup: {str(e)}")
            return False, "An error occurred during signup"

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Handle user login"""
        try:
            if username not in self.config['credentials']['usernames']:
                return False, "Username not found"
            
            user_data = self.config['credentials']['usernames'][username]
            if self.verify_password(password, user_data['password']):
                token = self.create_token(username)
                st.session_state.token = token
                logger.info(f"User logged in: {username}")
                return True, "Login successful"
            
            return False, "Incorrect password"
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False, "An error occurred during login"

    def _validate_password(self, password: str) -> bool:
        """Validate password strength"""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        return True

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        try:
            if username not in self.config['credentials']['usernames']:
                return False, "User not found"
            
            user_data = self.config['credentials']['usernames'][username]
            if not self.verify_password(old_password, user_data['password']):
                return False, "Incorrect current password"
            
            if not self._validate_password(new_password):
                return False, "New password does not meet requirements"
            
            user_data['password'] = self.hash_password(new_password)
            user_data['password_updated_at'] = datetime.now().isoformat()
            self.save_config()
            
            return True, "Password changed successfully"
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return False, "An error occurred while changing password"

    def update_user_info(self, username: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update user information"""
        try:
            if username not in self.config['credentials']['usernames']:
                return False, "User not found"
            
            user_data = self.config['credentials']['usernames'][username]
            allowed_fields = {'name', 'email'}
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'email' and not self._validate_email(value):
                        return False, "Invalid email format"
                    user_data[field] = value
            
            user_data['updated_at'] = datetime.now().isoformat()
            self.save_config()
            
            return True, "User information updated successfully"
        except Exception as e:
            logger.error(f"Error updating user info: {str(e)}")
            return False, "An error occurred while updating user information"

def setup_auth():
    """Setup and handle authentication in Streamlit"""
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False

    authenticator = Authenticator()

    if not st.session_state.authentication_status:
        st.title('Welcome to Knowledge Base Search')

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
                new_password = st.text_input('Choose Password', type='password',
                    help="Password must be at least 8 characters long and contain uppercase, lowercase, and numbers")
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
                        success, message = authenticator.signup(new_username, new_password, email, name)
                        if success:
                            st.success(message)
                            st.session_state.show_signup = False
                            st.rerun()
                        else:
                            st.error(message)

    return st.session_state.authentication_status

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
    if 'token' in st.session_state:
        del st.session_state.token