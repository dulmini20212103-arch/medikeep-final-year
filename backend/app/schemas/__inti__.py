#schema for creating a new user, returning user data in API responses, user login credentials, returning access tokens after login.
from .user import UserCreate, UserResponse, UserLogin, Token
from .auth import LoginRequest, RegisterRequest

#defines what gets exported when someone imports from this module
__all__ = ["UserCreate", "UserResponse", "UserLogin", "Token", "LoginRequest", "RegisterRequest"]