import streamlit as st
import jwt
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

from app.database.connection import get_db, init_db
from app.database.models import User, UserSession

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Authenticator:
    def __init__(self):
        """Initialize Authenticator"""
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')
        self.session_duration = timedelta(days=1)
        init_db()  # Initialize database tables

    def signup(self, username: str, password: str, email: str, name: str) -> Tuple[bool, str]:
        """Handle user signup"""
        try:
            db = next(get_db())
            
            # Check if user exists
            if db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first():
                return False, "Username or email already exists"

            if not self._validate_password(password):
                return False, "Password does not meet requirements"

            if not self._validate_email(email):
                return False, "Invalid email format"

            # Create new user
            new_user = User(
                username=username,
                email=email,
                name=name,
                created_at=datetime.utcnow()
            )
            new_user.set_password(password)
            
            db.add(new_user)
            db.commit()
            logger.info(f"New user signed up: {username}")
            return True, "Signup successful"
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during signup: {str(e)}")
            return False, "An error occurred during signup"
        except Exception as e:
            logger.error(f"Error during signup: {str(e)}")
            return False, "An error occurred during signup"
        finally:
            db.close()

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Handle user login"""
        try:
            db = next(get_db())
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                return False, "Username not found"
            
            if not user.is_active:
                return False, "Account is deactivated"

            if user.locked_until and user.locked_until > datetime.utcnow():
                return False, f"Account is locked until {user.locked_until}"

            if not user.check_password(password):
                # Handle failed login attempts
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                db.commit()
                return False, "Incorrect password"

            # Reset failed attempts and update last login
            user.failed_login_attempts = 0
            user.last_login = datetime.utcnow()
            
            # Create session and JWT token
            token = jwt.encode(
                {
                    'username': username,
                    'exp': datetime.utcnow() + self.session_duration
                },
                self.jwt_secret,
                algorithm='HS256'
            )
            
            session = UserSession(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + self.session_duration
            )
            
            db.add(session)
            db.commit()
            
            # Store in Streamlit session state
            st.session_state.token = token
            st.session_state.username = username
            
            logger.info(f"User logged in: {username}")
            return True, "Login successful"
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during login: {str(e)}")
            return False, "An error occurred during login"
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False, "An error occurred during login"
        finally:
            db.close()

    def verify_session(self) -> Optional[Dict[str, Any]]:
        """Verify current session"""
        try:
            token = st.session_state.get('token')
            if not token:
                return None

            db = next(get_db())
            session = db.query(UserSession).filter(
                UserSession.token == token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).first()

            if not session:
                return None

            user = db.query(User).get(session.user_id)
            if not user or not user.is_active:
                return None

            return {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'name': user.name
            }

        except Exception as e:
            logger.error(f"Error verifying session: {str(e)}")
            return None
        finally:
            db.close()

    def logout_user(self):
        """Log out the current user"""
        try:
            if 'token' in st.session_state:
                db = next(get_db())
                session = db.query(UserSession).filter(
                    UserSession.token == st.session_state.token
                ).first()
                if session:
                    session.is_active = False
                    db.commit()

            # Clear session state
            st.session_state.clear()
            logger.info("User logged out successfully")
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
        finally:
            db.close()

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

# Create a global authenticator instance
_authenticator = Authenticator()

def setup_auth():
    """Setup and handle authentication in Streamlit"""
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None

    # Verify existing session
    if st.session_state.get('token'):
        user_info = _authenticator.verify_session()
        if user_info:
            st.session_state.authentication_status = True
            return True
        else:
            st.session_state.clear()

    if not st.session_state.authentication_status:
        st.title('Welcome to Knowledge Base Search')

        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input('Username')
                password = st.text_input('Password', type='password')
                
                if st.form_submit_button('Login'):
                    if username and password:
                        success, message = _authenticator.login(username, password)
                        if success:
                            st.session_state.authentication_status = True
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input('Choose Username')
                new_password = st.text_input('Choose Password', type='password',
                    help="Password must be at least 8 characters long and contain uppercase, lowercase, and numbers")
                confirm_password = st.text_input('Confirm Password', type='password')
                email = st.text_input('Email')
                name = st.text_input('Full Name')
                
                if st.form_submit_button('Sign Up'):
                    if not all([new_username, new_password, confirm_password, email, name]):
                        st.error("Please fill in all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        success, message = _authenticator.signup(new_username, new_password, email, name)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

        return False

    return True

def get_username():
    """Get the current authenticated username"""
    return st.session_state.get('username')

def get_user_info():
    """Get information about the current user"""
    try:
        db = next(get_db())
        username = get_username()
        if username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                return {
                    'username': user.username,
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'created_at': user.created_at
                }
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
    finally:
        db.close()
    return None

def logout():
    """Global logout function"""
    _authenticator.logout_user()
    st.rerun()