from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..models.document import DocumentType, DocumentStatus
from ..utils.validators import SecurityValidatorMixin, SecureTextValidator

#shared foundation
class DocumentBase(BaseModel, SecurityValidatorMixin):
    original_filename: str
    document_type: Optional[DocumentType] = None
    notes: Optional[str] = None
    
    @validator('original_filename')
    def validate_filename(cls, v):
        return SecureTextValidator.validate_filename(v)
    
    @validator('notes')
    def validate_notes(cls, v):
        return SecureTextValidator.sanitize_notes(v) if v else None


#upload contract
#protects your system before a file is accepted.
class DocumentCreate(DocumentBase):
    patient_id: Optional[int] = None
    clinic_id: int
    mime_type: str
    file_size: int
    file_hash: Optional[str] = None
    
    @validator('mime_type')
    def validate_mime_type(cls, v):
        allowed_types = [
            'application/pdf',
            'image/jpeg',
            'image/jpg', 
            'image/png',
            'image/tiff',
            'image/bmp'
        ]
        if v not in allowed_types:
            raise ValueError(f'Unsupported file type: {v}')
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError('File size exceeds maximum allowed size of 50MB')
        return v

#Allows safe edits
class DocumentUpdate(BaseModel, SecurityValidatorMixin):
    document_type: Optional[DocumentType] = None
    notes: Optional[str] = None
    patient_id: Optional[int] = None
    
    @validator('notes')
    def validate_notes(cls, v):
        return SecureTextValidator.sanitize_notes(v) if v else None

#standard API output
class DocumentResponse(DocumentBase):
    id: int
    patient_id: Optional[int]
    clinic_id: int
    file_path: str
    mime_type: str
    file_size: int
    file_hash: Optional[str]
    status: DocumentStatus
    upload_date: datetime
    processed_date: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Additional computed fields
    patient_name: Optional[str] = None
    clinic_name: Optional[str] = None
    has_extractions: Optional[bool] = False
    extraction_count: Optional[int] = 0
    last_extraction_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

#deep inspection view
class DocumentDetailResponse(DocumentResponse):
    # Patient information
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    patient_id_number: Optional[str] = None
    
    # Clinic information
    clinic_name: Optional[str] = None
    clinic_license: Optional[str] = None
    
    # Extraction summary
    total_extractions: Optional[int] = 0
    successful_extractions: Optional[int] = 0
    failed_extractions: Optional[int] = 0
    latest_extraction_status: Optional[str] = None
    
    # Medical data summary
    medical_entities_count: Optional[int] = 0
    abnormal_findings_count: Optional[int] = 0
    critical_findings_count: Optional[int] = 0
    
    # Processing metadata
    average_confidence_score: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    file_security_status: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    upload_url: Optional[str] = None
    processing_started: bool = False
    estimated_processing_time: Optional[int] = None  # seconds

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_previous: bool

class DocumentSearchRequest(BaseModel, SecurityValidatorMixin):
    query: Optional[str] = None
    document_type: Optional[DocumentType] = None
    status: Optional[DocumentStatus] = None
    patient_id: Optional[int] = None
    clinic_id: Optional[int] = None
    upload_date_from: Optional[datetime] = None
    upload_date_to: Optional[datetime] = None
    has_extractions: Optional[bool] = None
    has_abnormal_findings: Optional[bool] = None
    file_size_min: Optional[int] = None
    file_size_max: Optional[int] = None
    
    @validator('query')
    def sanitize_query(cls, v):
        return SecureTextValidator.sanitize_notes(v)[:100] if v else None

class DocumentStatsResponse(BaseModel):
    total_documents: int
    documents_by_status: Dict[str, int]
    documents_by_type: Dict[str, int]
    total_file_size: int
    average_file_size: float
    documents_this_month: int
    documents_with_extractions: int
    processing_success_rate: float
    
    # Recent activity
    recent_uploads: List[DocumentResponse]
    recent_processed: List[DocumentResponse]
    
    # Quality metrics
    average_confidence_score: Optional[float] = None
    documents_with_abnormal_findings: int = 0
    documents_with_critical_findings: int = 0

class DocumentProcessingStats(BaseModel):
    document_id: int
    processing_history: List[Dict[str, Any]]
    total_processing_time: Optional[float] = None
    success_rate: float
    quality_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]

class DocumentExtractionSummary(BaseModel):
    document_id: int
    total_extractions: int
    successful_extractions: int
    failed_extractions: int
    
    # Latest extraction info
    latest_extraction_id: Optional[int] = None
    latest_extraction_status: Optional[str] = None
    latest_extraction_date: Optional[datetime] = None
    latest_confidence_score: Optional[float] = None
    
    # Medical data summary
    medical_entities: Dict[str, int]  # type -> count
    abnormal_findings: int
    critical_findings: int
    
    # Key findings
    key_findings: List[Dict[str, Any]]
    clinical_alerts: List[Dict[str, Any]]

class DocumentValidationResponse(BaseModel):
    document_id: int
    is_valid: bool
    validation_errors: List[str]
    security_check_passed: bool
    file_integrity_verified: bool
    metadata_extracted: bool
    
    # File analysis
    file_analysis: Dict[str, Any]
    mime_type_verified: str
    file_size_valid: bool
    
    # Security analysis
    malware_scan_result: Optional[str] = None
    suspicious_patterns: List[str] = []
    
    # Quality assessment
    readability_score: Optional[float] = None
    text_quality_score: Optional[float] = None
    image_quality_score: Optional[float] = None

class DocumentSecurityResponse(BaseModel):
    document_id: int
    security_status: str  # clean, suspicious, malware, quarantined
    scan_date: datetime
    scan_results: Dict[str, Any]
    threats_detected: List[str]
    quarantine_reason: Optional[str] = None
    safe_for_processing: bool

class DocumentMedicalSummary(BaseModel):
    document_id: int
    document_type: str
    processing_summary: Dict[str, Any]
    
    # Medical content analysis
    medical_content_detected: bool
    document_complexity: str  # simple, moderate, complex
    primary_medical_categories: List[str]
    
    # Key medical findings
    lab_values: List[Dict[str, Any]]
    medications: List[Dict[str, Any]]
    diagnoses: List[Dict[str, Any]]
    vital_signs: List[Dict[str, Any]]
    procedures: List[Dict[str, Any]]
    
    # Clinical significance
    abnormal_findings: List[Dict[str, Any]]
    critical_values: List[Dict[str, Any]]
    clinical_recommendations: List[str]
    
    # Quality and confidence
    extraction_confidence: float
    medical_coding_accuracy: Optional[float] = None
    validation_status: str

class DocumentShareRequest(BaseModel, SecurityValidatorMixin):
    document_id: int
    recipient_email: str
    access_level: str = "view"  # view, download
    expires_in_hours: int = 24
    include_medical_data: bool = False
    custom_message: Optional[str] = None
    
    @validator('recipient_email')
    def validate_email(cls, v):
        return SecureTextValidator.validate_email_field(v)
    
    @validator('access_level')
    def validate_access_level(cls, v):
        if v not in ['view', 'download']:
            raise ValueError('Invalid access level')
        return v
    
    @validator('expires_in_hours')
    def validate_expiry(cls, v):
        if v < 1 or v > 168:  # Max 1 week
            raise ValueError('Expiry must be between 1 and 168 hours')
        return v
    
    @validator('custom_message')
    def validate_message(cls, v):
        return SecureTextValidator.sanitize_notes(v) if v else None

class DocumentShareResponse(BaseModel):
    share_id: str
    document_id: int
    recipient_email: str
    access_level: str
    expires_at: datetime
    share_url: str
    created_at: datetime

class DocumentBatchProcessRequest(BaseModel):
    document_ids: List[int]
    processing_options: Dict[str, Any]
    priority: str = "normal"  # low, normal, high
    notify_on_completion: bool = True
    
    @validator('document_ids')
    def validate_document_ids(cls, v):
        if len(v) > 50:
            raise ValueError('Cannot process more than 50 documents at once')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high']:
            raise ValueError('Invalid priority level')
        return v

class DocumentBatchProcessResponse(BaseModel):
    batch_id: str
    total_documents: int
    processing_started: bool
    estimated_completion_time: Optional[datetime] = None
    status_check_url: str

class DocumentAnalyticsRequest(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    document_types: Optional[List[DocumentType]] = None
    include_medical_analysis: bool = False
    group_by: str = "day"  # day, week, month
    
    @validator('group_by')
    def validate_group_by(cls, v):
        if v not in ['day', 'week', 'month']:
            raise ValueError('Invalid group_by value')
        return v
class DocumentAssignmentRequest(BaseModel, SecurityValidatorMixin):
    document_ids: List[int]
    assignee_id: int
    assignment_type: str = "review"  # review, process, validate, approve, archive
    priority: str = "normal"  # low, normal, high, urgent
    due_date: Optional[datetime] = None
    assignment_notes: Optional[str] = None
    
    # Assignment scope and permissions
    access_level: str = "read"  # read, write, full_access
    can_reassign: bool = False
    can_modify_document: bool = False
    can_view_medical_data: bool = True
    
    # Workflow settings
    requires_approval: bool = False
    approval_required_from: Optional[int] = None  # user_id of approver
    auto_notify: bool = True
    send_email_notification: bool = True
    send_sms_notification: bool = False
    
    # Assignment metadata
    department: Optional[str] = None
    specialty: Optional[str] = None  # cardiology, radiology, etc.
    urgency_reason: Optional[str] = None
    expected_completion_hours: Optional[int] = 24
    
    # Collaboration settings
    allow_collaboration: bool = False
    collaborate_with: Optional[List[int]] = None  # list of user_ids
    
    @validator('document_ids')
    def validate_document_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one document must be assigned')
        if len(v) > 20:
            raise ValueError('Cannot assign more than 20 documents at once')
        return v
    
    @validator('assignment_type')
    def validate_assignment_type(cls, v):
        allowed_types = [
            'review', 'process', 'validate', 'approve', 'archive', 
            'extract', 'annotate', 'correct', 'quality_check'
        ]
        if v not in allowed_types:
            raise ValueError(f'Invalid assignment type. Must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high', 'urgent']:
            raise ValueError('Priority must be: low, normal, high, or urgent')
        return v
    
    @validator('access_level')
    def validate_access_level(cls, v):
        if v not in ['read', 'write', 'full_access']:
            raise ValueError('Access level must be: read, write, or full_access')
        return v
    
    @validator('assignment_notes')
    def validate_assignment_notes(cls, v):
        return SecureTextValidator.sanitize_notes(v) if v else None
    
    @validator('urgency_reason')
    def validate_urgency_reason(cls, v):
        return SecureTextValidator.sanitize_notes(v) if v else None
    
    @validator('department')
    def validate_department(cls, v):
        return SecureTextValidator.sanitize_department_name(v) if v else None
    
    @validator('specialty')
    def validate_specialty(cls, v):
        return SecureTextValidator.sanitize_specialty_name(v) if v else None
    
    @validator('due_date')
    def validate_due_date(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Due date must be in the future')
        return v
    
    @validator('expected_completion_hours')
    def validate_completion_hours(cls, v):
        if v is not None and (v < 1 or v > 168):  # Max 1 week
            raise ValueError('Expected completion time must be between 1 and 168 hours')
        return v
    
    @validator('collaborate_with')
    def validate_collaborators(cls, v):
        if v and len(v) > 10:
            raise ValueError('Cannot collaborate with more than 10 users')
        return v


class DocumentAnalyticsResponse(BaseModel):
    time_series_data: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]
    trends: Dict[str, Any]
    medical_insights: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    processing_performance: Dict[str, Any]
    quality_trends: Dict[str, Any]
    error_analysis: Dict[str, Any]

class DocumentExportRequest(BaseModel, SecurityValidatorMixin):
    document_ids: List[int]
    export_format: str = "pdf"  # pdf, json, csv, excel
    include_metadata: bool = True
    include_extractions: bool = False
    include_medical_data: bool = False
    compression: bool = True
    
    @validator('export_format')
    def validate_format(cls, v):
        if v not in ['pdf', 'json', 'csv', 'excel']:
            raise ValueError('Invalid export format')
        return v
    
    @validator('document_ids')
    def validate_document_ids(cls, v):
        if len(v) > 100:
            raise ValueError('Cannot export more than 100 documents at once')
        return v

class DocumentExportResponse(BaseModel):
    export_id: str
    total_documents: int
    export_format: str
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    expires_at: datetime
    created_at: datetime

class DocumentComplianceReport(BaseModel):
    document_id: int
    compliance_status: str  # compliant, non_compliant, needs_review
    compliance_checks: Dict[str, Any]
    
    # HIPAA compliance
    phi_detected: bool
    phi_protection_status: str
    access_log_complete: bool
    
    # Data retention
    retention_policy_applied: bool
    retention_period: Optional[int] = None
    scheduled_deletion_date: Optional[datetime] = None
    
    # Audit trail
    audit_trail_complete: bool
    last_audit_date: Optional[datetime] = None
    
    # Recommendations
    compliance_recommendations: List[str]
    required_actions: List[str]

class DocumentVersionInfo(BaseModel):
    document_id: int
    version_number: int
    version_type: str  # original, processed, corrected, annotated
    created_at: datetime
    created_by: Optional[str] = None
    changes_summary: Optional[str] = None
    file_path: str
    file_size: int
    is_current: bool

class DocumentVersionHistory(BaseModel):
    document_id: int
    versions: List[DocumentVersionInfo]
    total_versions: int
    current_version: DocumentVersionInfo

# Template schemas for different document types
class LabReportTemplate(BaseModel):
    expected_fields: List[str]
    validation_rules: Dict[str, Any]
    reference_ranges: Dict[str, Any]
    critical_values: Dict[str, Any]

class PrescriptionTemplate(BaseModel):
    required_fields: List[str]
    medication_validation: Dict[str, Any]
    dosage_patterns: List[str]
    safety_checks: List[str]

class DocumentTemplateResponse(BaseModel):
    document_type: DocumentType
    template_name: str
    template_version: str
    field_definitions: Dict[str, Any]
    validation_rules: Dict[str, Any]
    extraction_hints: Dict[str, Any]



    #The AI operates downstream; this schema layer strictly validates, structures, and governs the data the AI consumes and produces.