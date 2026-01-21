#controls what parts of the internal security system are publicly exposed to the rest of the application
from .auth import create_access_token, verify_token, get_password_hash, verify_password
from .deps import get_current_user, get_current_active_user

__all__ = [
    "create_access_token", 
    "verify_token", 
    "get_password_hash", 
    "verify_password",
    "get_current_user",
    "get_current_active_user"
]


#This file exposes a controlled authentication interface for the application. 
# It prevents tight coupling to internal security implementations and enforces a clean separation between authentication logic and route-level authorization.