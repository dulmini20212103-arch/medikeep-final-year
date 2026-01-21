#Define table columns and types.
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
#Provides database functions for timestamps
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
#to define controlled value sets.
import enum
from ..database import Base

class UserRole(enum.Enum):
    ADMIN = "admin"
    CLINIC_ADMIN = "clinic_admin"
    CLINIC_STAFF = "clinic_staff"
    PATIENT = "patient"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="[AuditLog.user_id]")
    
    # Relationships
    clinic = relationship("Clinic", back_populates="users", uselist=False)
    patient_profile = relationship("Patient", back_populates="user", uselist=False)