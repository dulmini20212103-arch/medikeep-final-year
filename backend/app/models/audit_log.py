#full audit logging model using SQLAlchemy ORM
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
#to create controlled, type-safe values
import enum
from ..database import Base

#Defines allowed actions that can be logged
#Enum is safer than strings and easier to filter nad analyze logs
class AuditAction(enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    DOWNLOAD = "download"
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD = "upload"
    ASSIGN = "assign"
    PROCESS = "process"
    EXPORT = "export"

#Identifies what kind of entity the action was performed on.
#avoids creating separate audit tables per entity.
class AuditEntityType(enum.Enum):
    USER = "user"
    PATIENT = "patient"
    DOCUMENT = "document"
    CLINIC = "clinic"
    EXTRACTION = "extraction"
    SYSTEM = "system"

#Declares a SQLAlchemy model mapped to the audit_logs table.
class AuditLog(Base):
    __tablename__ = "audit_logs"
#primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User performing the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) #inks to the user table if the user still exists.
    user_email = Column(String, nullable=True)  # Store email for deleted users
    user_role = Column(String, nullable=True) #captures authorization context at the time of action.
    
    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    entity_type = Column(Enum(AuditEntityType), nullable=False)
    entity_id = Column(String, nullable=True)  # Store as string to handle different ID types
    entity_name = Column(String, nullable=True)  # Human-readable identifier
    

    # Context
    #Adds business context to the action.
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    
    # Details
    description = Column(Text, nullable=False) #Human-readable explanation
    changes = Column(JSON, nullable=True)  # Before/after values for updates
    metadata = Column(JSON, nullable=True)  # Additional context
    
    # Request information
    #Captures how and from where the action was triggered.
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_path = Column(String, nullable=True)
    
    # Status
    success = Column(String, default=True)  # True for success, False for failures
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    #Database-controlled timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    #enable ORM-level access
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    clinic = relationship("Clinic", foreign_keys=[clinic_id])
    patient = relationship("Patient", foreign_keys=[patient_id])



    #Using JSON:Makes logs machine-readable, Supports analytics and debugging, Avoids schema changes for new metadata