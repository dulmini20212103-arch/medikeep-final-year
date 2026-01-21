#Define table columns and types.
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Enum
#Provides database functions for timestamps
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
#to define controlled value sets.
import enum
from ..database import Base

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    clinic_id = Column(Integer, ForeignKey("clinics.id"))
    patient_id = Column(String, unique=True, index=True)  # Hospital patient ID
    date_of_birth = Column(Date)
    gender = Column(Enum(Gender))
    phone = Column(String)
    address = Column(Text)
    emergency_contact_name = Column(String)
    emergency_contact_phone = Column(String)
    medical_history = Column(Text)
    allergies = Column(Text)
    current_medications = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="patient_profile")
    clinic = relationship("Clinic", back_populates="patients")
    documents = relationship("Document", back_populates="patient")
    extractions = relationship("Extraction", back_populates="patient")