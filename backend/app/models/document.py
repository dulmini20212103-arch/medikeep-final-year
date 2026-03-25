from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, BigInteger, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from ..database import Base

class DocumentType(enum.Enum):
    LAB_REPORT = "lab_report"
    PRESCRIPTION = "prescription"
    MEDICAL_RECORD = "medical_record"
    IMAGING_REPORT = "imaging_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    OTHER = "other"

class DocumentStatus(enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    clinic_id = Column(Integer, ForeignKey("clinics.id"))
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger)
    mime_type = Column(String)
    document_type = Column(Enum(DocumentType))
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    processed_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    is_patient_upload = Column(Boolean, default=False, server_default="false", nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="documents")
    clinic = relationship("Clinic", back_populates="documents")
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by_user_id])
    extractions = relationship("Extraction", back_populates="document")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", passive_deletes=True)
