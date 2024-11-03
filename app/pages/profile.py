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