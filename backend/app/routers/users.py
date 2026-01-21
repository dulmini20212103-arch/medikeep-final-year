from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
#provides a database session per request
from ..database import get_db
from ..models.user import User, UserRole
#To prevent accidental exposure of sensitive fields
from ..schemas.user import UserResponse, UserUpdate
from ..utils.deps import get_current_active_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])

#Only admins can access it
@router.get("/", response_model=List[UserResponse])
async def get_users(
    #skip and limit is used for pagination support
    skip: int = 0,
    limit: int = 100,
    #Automatically blocks non-admin users
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    #Fetches users from the database using SQLAlchemy
    """Get all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    #Converts SQLAlchemy objects into safe API responses
    return [UserResponse.from_orm(user) for user in users]

#Returns only the authenticated user’s own profile
@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile."""
    return UserResponse.from_orm(current_user)

#Allows users to update their own profile and prevents updating restricted fields
@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    update_data = user_update.dict(exclude_unset=True)
    
    #get updated allowed fields
    for field, value in update_data.items():
        setattr(current_user, field, value)

   #Saves changes to the database and refreshe the object with updated values 
    db.commit()
    db.refresh(current_user)
    return UserResponse.from_orm(current_user)