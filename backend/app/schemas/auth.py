#built-in Pydantic type that validates email format automatically.
from pydantic import BaseModel, EmailStr
from ..models.user import UserRole
#allows fields to be None
from typing import Optional

#Represents the request body for user login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

#Represents the request body for user registration.
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole
    clinic_name: Optional[str] = None  # Required if role is clinic_admin
    clinic_license: Optional[str] = None  # Required if role is clinic_admin


    #Invalid emails or missing required fields are rejected before hitting your database.
    #Prevents invalid or unexpected role values from being submitted.