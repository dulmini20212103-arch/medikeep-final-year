from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from ..models.user import UserRole #role-based access control
from ..utils.validators import SecurityValidatorMixin, SecureTextValidator

#core user identity schema
#foundation schema reused across create, response, and token payloads
class UserBase(BaseModel, SecurityValidatorMixin):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    
    # Validators
    @validator('first_name')
    def validate_first_name(cls, v):
        return SecureTextValidator.sanitize_name(v)
    
    @validator('last_name')
    def validate_last_name(cls, v):
        return SecureTextValidator.sanitize_name(v)
    
    @validator('email')
    def validate_email_security(cls, v):
        return SecureTextValidator.validate_email_field(str(v))

#registration input schema
#Extends UserBase and adds password.
class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

#partial updates
class UserUpdate(BaseModel, SecurityValidatorMixin):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    
    @validator('first_name')
    def validate_first_name(cls, v):
        return SecureTextValidator.sanitize_name(v) if v else None
    
    @validator('last_name')
    def validate_last_name(cls, v):
        return SecureTextValidator.sanitize_name(v) if v else None

#API output schema
class UserResponse(UserBase):
    #Adds system-controlled fields
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

#authentication input
class UserLogin(BaseModel):
    email: EmailStr
    password: str

#authentication response payload
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

    #strictly controls user input and output, enforces strong password and identity validation, prevents security vulnerabilities, and cleanly separates authentication, profile management, and authorization concerns.