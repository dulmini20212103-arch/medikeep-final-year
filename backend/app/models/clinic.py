#Define table columns and types.
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
#Provides database functions for timestamps.
from sqlalchemy.sql import func
#Sets up ORM relationships between models.
from sqlalchemy.orm import relationship
from ..database import Base

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    license_number = Column(String, unique=True, nullable=False)
    address = Column(Text)
    phone = Column(String)
    email = Column(String)
    admin_user_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    #Timestamp of creation, set by the database automatically.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    #Timestamp updated automatically whenever the record changes.
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    #back_populates allows bidirectional access 
    users = relationship("User", back_populates="clinic")
    patients = relationship("Patient", back_populates="clinic")
    documents = relationship("Document", back_populates="clinic")