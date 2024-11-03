import streamlit as st
import logging
from datetime import datetime
from typing import Tuple
from sqlalchemy import desc

from app.auth.authenticator import get_username, get_user_info, logout
from app.database.connection import get_db
from app.database.models import User, UserSession

logger = logging.getLogger(__name__)

def update_user_profile(user: User, name: str, email: str) -> Tuple[bool, str]:
    """Update user profile information"""
    try:
        db = next(get_db())
        
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(
            User.email == email,
            User.id != user.id
        ).first()
        
        if existing_user:
            return False, "Email already in use by another account"
        
        user.name = name
        user.email = email
        user.updated_at = datetime.utcnow()
        
        db.commit()
        return True, "Profile updated successfully"
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return False, "An error occurred while updating profile"
    finally:
        db.close()

def change_password(user: User, current_password: str, new_password: str) -> Tuple[bool, str]:
    """Change user password"""
    try:
        db = next(get_db())
        
        if not user.check_password(current_password):
            return False, "Current password is incorrect"
        
        if not _validate_password(new_password):
            return False, "New password does not meet requirements"
        
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        
        db.commit()
        return True, "Password changed successfully"
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return False, "An error occurred while changing password"
    finally:
        db.close()

def _validate_password(password: str) -> bool:
    """Validate password requirements"""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

def get_user_sessions(username: str, limit: int = 5):
    """Get recent user sessions"""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return []
            
        # Query sessions directly through the user object
        sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user.id)
            .order_by(desc(UserSession.created_at))
            .limit(limit)
            .all()
        )
        return sessions
    except Exception as e:
        logger.error(f"Error fetching user sessions: {str(e)}")
        return []
    finally:
        db.close()

def render_profile_page():
    """Render the profile management page"""
    st.title("User Profile")
    
    # Get current user info
    username = get_username()
    if not username:
        st.error("Please login to access your profile")
        st.stop()
    
    user_info = get_user_info()
    if not user_info:
        st.error("Unable to fetch user information")
        st.stop()
    
    # Create tabs for different sections
    profile_tab, security_tab, activity_tab = st.tabs([
        "Profile Information", 
        "Security Settings", 
        "Account Activity"
    ])
    
    # Profile Information Tab
    with profile_tab:
        st.subheader("Profile Information")
        
        with st.form("profile_form"):
            name = st.text_input("Full Name", value=user_info['name'])
            email = st.text_input("Email", value=user_info['email'])
            
            if st.form_submit_button("Update Profile"):
                db = next(get_db())
                user = db.query(User).filter(User.username == username).first()
                
                if user:
                    success, message = update_user_profile(user, name, email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                db.close()
    
    # Security Settings Tab
    with security_tab:
        st.subheader("Change Password")
        
        password_changed = False
        
        with st.form("password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password",
                help="Password must be at least 8 characters long and contain uppercase, lowercase, and numbers")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Change Password"):
                if new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    db = next(get_db())
                    user = db.query(User).filter(User.username == username).first()
                    
                    if user:
                        success, message = change_password(user, current_password, new_password)
                        if success:
                            st.success(message)
                            password_changed = True
                        else:
                            st.error(message)
                    db.close()
        
        # Re-login button outside the form
        if password_changed:
            st.info("Please log in again with your new password")
            if st.button("Re-login"):
                logout()
                st.rerun()
    
    # Account Activity Tab
    with activity_tab:
        st.subheader("Recent Account Activity")
        
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            # Display basic account information
            st.write(f"Account created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"Last login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}")
            
            # Display recent sessions
            st.subheader("Recent Sessions")
            sessions = get_user_sessions(username)
            
            if sessions:
                for session in sessions:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"Status: {'Active' if session.is_active else 'Expired'}")
                    with col2:
                        st.write(f"Expires: {session.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.divider()
            else:
                st.info("No recent session history available")
        
        db.close()

if __name__ == "__main__":
    render_profile_page()