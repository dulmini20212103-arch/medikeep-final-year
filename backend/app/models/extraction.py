#Define table columns and types.
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Enum
#Provides database functions for timestamps
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
#to define controlled value sets.
import enum
from ..database import Base

class ExtractionType(enum.Enum):
    LAB_VALUES = "lab_values"
    MEDICATIONS = "medications"
    DIAGNOSES = "diagnoses"
    VITAL_SIGNS = "vital_signs"
    DATES = "dates"
    GENERAL = "general"

class ExtractionStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    extraction_type = Column(Enum(ExtractionType))
    status = Column(Enum(ExtractionStatus), default=ExtractionStatus.PENDING)
    
    # Extracted data fields
    raw_text = Column(Text)  # OCR extracted text
    structured_data = Column(JSON)  # Structured extracted data
    confidence_score = Column(Float)  # AI confidence 0-1
    
    # Specific extraction fields
    lab_values = Column(JSON)  # {test_name: value, unit, reference_range}
    medications = Column(JSON)  # {medication: dosage, frequency, duration}
    diagnoses = Column(JSON)  # {diagnosis: code, description}
    vital_signs = Column(JSON)  # {bp: value, hr: value, temp: value}
    important_dates = Column(JSON)  # {date_type: date_value}
    
    # Metadata
    extraction_method = Column(String)  # "OCR+AI", "AI_ONLY", etc
    processing_time_seconds = Column(Float)
    error_message = Column(Text) # details if extraction failed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    document = relationship("Document", back_populates="extractions")
    patient = relationship("Patient", back_populates="extractions")