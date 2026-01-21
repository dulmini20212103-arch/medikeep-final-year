from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta, date

from ..database import get_db
from ..models.patient import Patient, Gender
from ..models.user import User, UserRole
from ..models.clinic import Clinic
from ..models.document import Document
from ..schemas.patient import (
    PatientCreate, PatientUpdate, PatientResponse, PatientDetailResponse,
    PatientListResponse, PatientSearchRequest, PatientStatsResponse
)
from ..utils.deps import get_current_active_user, require_clinic_access

router = APIRouter(prefix="/patients", tags=["patients"])

#Create a new patient
@router.post("/", response_model=PatientDetailResponse)
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Create a new patient with enhanced validation."""
    
    # Get clinic
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if not clinic:
        raise HTTPException(status_code=400, detail="Clinic not found")
    
    # Check if patient_id already exists in clinic
    existing = db.query(Patient).filter(
        Patient.patient_id == patient_data.patient_id,
        Patient.clinic_id == clinic.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Patient ID already exists in this clinic")
    
    # Validate user association if provided
    if patient_data.user_id:
        user = db.query(User).filter(
            User.id == patient_data.user_id,
            User.role == UserRole.PATIENT
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="Patient user not found")
    
    patient = Patient(
        **patient_data.dict(exclude={'clinic_id'}),
        clinic_id=clinic.id
    )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    # Return detailed response
    return _get_patient_detail(patient.id, db, current_user)

#List patients with filters and search
@router.get("/", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    gender: Optional[Gender] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    has_documents: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get patients with enhanced filtering and search."""
    
    # Build base query
    query = db.query(Patient).options(
        joinedload(Patient.user),
        joinedload(Patient.clinic)
    )
    
    # Apply role-based filtering
    if current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic:
            query = query.filter(Patient.clinic_id == clinic.id)
    elif current_user.role == UserRole.PATIENT:
        query = query.filter(Patient.user_id == current_user.id)
    
    # Apply search
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Patient.patient_id.ilike(search_filter),
                Patient.emergency_contact_name.ilike(search_filter),
                Patient.address.ilike(search_filter)
            )
        )
    
    # Apply filters
    if gender:
        query = query.filter(Patient.gender == gender)
    
    if age_min or age_max:
        today = date.today()
        if age_min:
            max_birth_date = today.replace(year=today.year - age_min)
            query = query.filter(Patient.date_of_birth <= max_birth_date)
        if age_max:
            min_birth_date = today.replace(year=today.year - age_max - 1)
            query = query.filter(Patient.date_of_birth >= min_birth_date)
    
    if has_documents is not None:
        if has_documents:
            query = query.filter(Patient.documents.any())
        else:
            query = query.filter(~Patient.documents.any())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    patients = query.offset(offset).limit(per_page).all()
    
    # Build detailed responses
    patient_details = []
    for patient in patients:
        detail = _build_patient_detail(patient, db)
        patient_details.append(detail)
    
    return PatientListResponse(
        patients=patient_details,
        total=total,
        page=page,
        per_page=per_page
    )

#Clinic-level patient statistics
@router.get("/stats", response_model=PatientStatsResponse)
async def get_patient_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Get patient statistics for clinic dashboard."""
    
    # Get clinic
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if not clinic:
        raise HTTPException(status_code=400, detail="Clinic not found")
    
    # Base query for clinic patients
    base_query = db.query(Patient).filter(Patient.clinic_id == clinic.id)
    
    # Total patients
    total_patients = base_query.count()
    
    # New patients this month
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_patients_this_month = base_query.filter(
        Patient.created_at >= month_start
    ).count()
    
    # Patients by gender
    gender_stats = db.query(Patient.gender, func.count(Patient.id)).filter(
        Patient.clinic_id == clinic.id
    ).group_by(Patient.gender).all()
    
    patients_by_gender = {
        str(gender.value) if gender else 'not_specified': count 
        for gender, count in gender_stats
    }
    
    # Patients by age group
    today = date.today()
    age_groups = {
        '0-18': 0, '19-30': 0, '31-50': 0, '51-70': 0, '70+': 0
    }
    
    patients_with_dob = base_query.filter(Patient.date_of_birth.isnot(None)).all()
    for patient in patients_with_dob:
        age = today.year - patient.date_of_birth.year
        if patient.date_of_birth.month > today.month or \
           (patient.date_of_birth.month == today.month and patient.date_of_birth.day > today.day):
            age -= 1
        
        if age <= 18:
            age_groups['0-18'] += 1
        elif age <= 30:
            age_groups['19-30'] += 1
        elif age <= 50:
            age_groups['31-50'] += 1
        elif age <= 70:
            age_groups['51-70'] += 1
        else:
            age_groups['70+'] += 1
    
    # Patients with documents
    patients_with_documents = base_query.filter(Patient.documents.any()).count()
    
    # Recent patients
    recent_patients = base_query.options(
        joinedload(Patient.user)
    ).order_by(Patient.created_at.desc()).limit(5).all()
    
    recent_patient_details = [_build_patient_detail(p, db) for p in recent_patients]
    
    return PatientStatsResponse(
        total_patients=total_patients,
        new_patients_this_month=new_patients_this_month,
        patients_by_gender=patients_by_gender,
        patients_by_age_group=age_groups,
        patients_with_documents=patients_with_documents,
        recent_patients=recent_patient_details
    )

#Get patient details
@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get patient details with comprehensive information."""
    return _get_patient_detail(patient_id, db, current_user)

#Update patient info
@router.put("/{patient_id}", response_model=PatientDetailResponse)
async def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update patient information with validation."""
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check permissions
    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic and patient.clinic_id != clinic.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    update_data = patient_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    db.commit()
    db.refresh(patient)
    
    return _get_patient_detail(patient.id, db, current_user)

#Delete a patient
@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Delete patient (clinic admin only)."""
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check clinic permissions
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if clinic and patient.clinic_id != clinic.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if patient has documents
    document_count = db.query(Document).filter(Document.patient_id == patient.id).count()
    if document_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete patient with {document_count} documents. Delete or reassign documents first."
        )
    
    db.delete(patient)
    db.commit()
    
    return {"message": "Patient deleted successfully"}

def _get_patient_detail(patient_id: int, db: Session, current_user: User) -> PatientDetailResponse:
    """Helper function to get patient with full details."""
    
    query = db.query(Patient).options(
        joinedload(Patient.user),
        joinedload(Patient.clinic)
    )
    
    if current_user.role == UserRole.PATIENT:
        patient = query.filter(
            Patient.id == patient_id,
            Patient.user_id == current_user.id
        ).first()
    else:
        patient = query.filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check clinic permissions for clinic users
    if current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic and patient.clinic_id != clinic.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return _build_patient_detail(patient, db)

def _build_patient_detail(patient: Patient, db: Session) -> PatientDetailResponse:
    """Build detailed patient response."""
    
    # Get documents count
    documents_count = db.query(Document).filter(Document.patient_id == patient.id).count()
    
    # Get last document upload date as proxy for last visit
    last_document = db.query(Document).filter(
        Document.patient_id == patient.id
    ).order_by(Document.upload_date.desc()).first()
    
    response_data = PatientResponse.from_orm(patient).dict()
    
    # Add additional details
    response_data.update({
        "user_first_name": patient.user.first_name if patient.user else None,
        "user_last_name": patient.user.last_name if patient.user else None,
        "user_email": patient.user.email if patient.user else None,
        "clinic_name": patient.clinic.name if patient.clinic else None,
        "documents_count": documents_count,
        "last_visit": last_document.upload_date if last_document else None
    })
    
    return PatientDetailResponse(**response_data)