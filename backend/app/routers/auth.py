from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User,UserRole
from ..models.clinic import Clinic
from ..schemas.auth import LoginRequest, RegisterRequest
from ..schemas.user import Token, UserResponse
from ..utils.auth import verify_password, get_password_hash, create_access_token
from ..utils.deps import get_current_active_user
from ..config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user exists
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    #Passwords are stored securely (hashed)
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create clinic if user is clinic admin
    if user_data.role == UserRole.CLINIC_ADMIN:
        if not user_data.clinic_name or not user_data.clinic_license:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clinic name and license required for clinic admin"
            )
        
        db_clinic = Clinic(
            name=user_data.clinic_name,
            license_number=user_data.clinic_license,
            admin_user_id=db_user.id
        )
        db.add(db_clinic)
        db.commit()
    
    #Returns user data without exposing sensitive fields
    return UserResponse.from_orm(db_user)

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    #Validates email and password
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    #Checks if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": UserResponse.from_orm(user)
    }

@router.post("/login/json", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """JSON login endpoint for frontend."""
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": UserResponse.from_orm(user)
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile."""
    return UserResponse.from_orm(current_user)