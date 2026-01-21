from pydantic import BaseModel, validator
from typing import Optional, List, Dict
from datetime import datetime
#Custom security validators are applied at the schema level
from ..utils.validators import SecurityValidatorMixin, SecureTextValidator

#foundation schema shared by create, update, and response models
class ClinicBase(BaseModel, SecurityValidatorMixin):
    name: str
    license_number: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    #Optional avoids forcing unnecessary data during onboarding
    
    @validator('name')
    def validate_name(cls, v):
        return SecureTextValidator.sanitize_name(v)
    
    @validator('phone')
    def validate_phone(cls, v):
        return SecureTextValidator.validate_phone_field(v) if v else None
    
    @validator('email')
    def validate_email(cls, v):
        return SecureTextValidator.validate_email_field(v) if v else None
    
    @validator('address')
    def validate_address(cls, v):
        return SecureTextValidator.sanitize_notes(v) if v else None

#clinic creation schema
#Inherits all validated fields from ClinicBase
class ClinicCreate(ClinicBase):
    admin_user_id: int

#partial update schema
class ClinicUpdate(BaseModel, SecurityValidatorMixin):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

#API output model
#Adds system-managed fields
class ClinicResponse(ClinicBase):
    id: int
    admin_user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

#analytics model
#read-only and aggregation-focused.
#Real-time operational overview for clinic admins
class ClinicDashboardStats(BaseModel):
    total_patients: int
    total_documents: int
    documents_this_month: int
    patients_this_month: int
    storage_used: int
    processing_queue: int
    #Advanced insights
    recent_activity: List[Dict]
    popular_document_types: Dict[str, int]
    patient_demographics: Dict[str, any]
    system_alerts: List[Dict]

#composite response model
class ClinicOverview(BaseModel):
    clinic_info: ClinicResponse
    stats: ClinicDashboardStats
    quick_actions: List[Dict[str, str]]



#enforces security, data integrity, and clean API contracts while remaining flexible enough for dashboards and future analytics