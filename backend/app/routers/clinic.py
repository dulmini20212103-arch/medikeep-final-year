from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..database import get_db
from ..models.clinic import Clinic
from ..models.patient import Patient, Gender
from ..models.document import Document, DocumentType, DocumentStatus
from ..models.user import User, UserRole
from ..schemas.clinic import (
    ClinicResponse, ClinicUpdate, ClinicDashboardStats, ClinicOverview
)
from ..utils.deps import get_current_active_user, require_clinic_access

router = APIRouter(prefix="/clinic", tags=["clinic"])

#Get clinic profile
@router.get("/profile", response_model=ClinicResponse)
#Fetches the clinic associated with the logged-in user.
async def get_clinic_profile(
    db: Session = Depends(get_db),
    #Uses dependency to ensure only clinic staff/admin can access.
    current_user: User = Depends(require_clinic_access)
):
    """Get current clinic profile."""
    
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    return ClinicResponse.from_orm(clinic)

#Update clinic profile
@router.put("/profile", response_model=ClinicResponse)
async def update_clinic_profile(
    clinic_update: ClinicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Update clinic profile."""
    
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    # Update fields
    update_data = clinic_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)
    
    #Saves changes in the database
    db.commit()
    db.refresh(clinic)
    
    return ClinicResponse.from_orm(clinic)

#Clinic dashboard statistics
@router.get("/dashboard", response_model=ClinicDashboardStats)
async def get_clinic_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Get comprehensive clinic dashboard statistics."""
    
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    # Time ranges
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    
    # Basic counts
    total_patients = db.query(Patient).filter(Patient.clinic_id == clinic.id).count()
    total_documents = db.query(Document).filter(Document.clinic_id == clinic.id).count()
    
    # This month stats
    patients_this_month = db.query(Patient).filter(
        Patient.clinic_id == clinic.id,
        Patient.created_at >= month_start
    ).count()
    
    documents_this_month = db.query(Document).filter(
        Document.clinic_id == clinic.id,
        Document.upload_date >= month_start
    ).count()
    
    # Storage calculation
    storage_used = db.query(func.sum(Document.file_size)).filter(
        Document.clinic_id == clinic.id
    ).scalar() or 0
    
    # Processing queue
    processing_queue = db.query(Document).filter(
        Document.clinic_id == clinic.id,
        Document.status.in_([DocumentStatus.UPLOADED, DocumentStatus.PROCESSING])
    ).count()
    
    # Recent activity
    recent_activity = _get_recent_activity(clinic.id, db, limit=10)
    
    # Popular document types
    doc_type_stats = db.query(
        Document.document_type, 
        func.count(Document.id)
    ).filter(
        Document.clinic_id == clinic.id
    ).group_by(Document.document_type).all()
    
    popular_document_types = {
        doc_type.value: count for doc_type, count in doc_type_stats
    }
    
    # Patient demographics
    patient_demographics = _get_patient_demographics(clinic.id, db)
    
    # System alerts
    system_alerts = _get_system_alerts(clinic.id, db)
    
    return ClinicDashboardStats(
        total_patients=total_patients,
        total_documents=total_documents,
        documents_this_month=documents_this_month,
        patients_this_month=patients_this_month,
        storage_used=storage_used,
        processing_queue=processing_queue,
        recent_activity=recent_activity,
        popular_document_types=popular_document_types,
        patient_demographics=patient_demographics,
        system_alerts=system_alerts
    )

#Complete clinic overview
@router.get("/overview", response_model=ClinicOverview)
async def get_clinic_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Get complete clinic overview for dashboard."""
    
    clinic_info = await get_clinic_profile(db, current_user)
    stats = await get_clinic_dashboard_stats(db, current_user)
    
    quick_actions = [
        {"title": "Add Patient", "action": "create_patient", "icon": "user-plus"},
        {"title": "Upload Documents", "action": "upload_documents", "icon": "upload"},
        {"title": "View Reports", "action": "view_reports", "icon": "chart-bar"},
        {"title": "Clinic Settings", "action": "clinic_settings", "icon": "cog"},
    ]
    
    return ClinicOverview(
        clinic_info=clinic_info,
        stats=stats,
        quick_actions=quick_actions
    )

def _get_recent_activity(clinic_id: int, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent clinic activity."""
    
    activities = []
    
    # Recent patient registrations
    recent_patients = db.query(Patient).filter(
        Patient.clinic_id == clinic_id
    ).order_by(Patient.created_at.desc()).limit(5).all()
    
    for patient in recent_patients:
        activities.append({
            "type": "patient_registered",
            "title": f"New patient registered: {patient.patient_id}",
            "timestamp": patient.created_at,
            "icon": "user-plus",
            "color": "green"
        })
    
    # Recent document uploads
    recent_documents = db.query(Document).filter(
        Document.clinic_id == clinic_id
    ).order_by(Document.upload_date.desc()).limit(5).all()
    
    for doc in recent_documents:
        activities.append({
            "type": "document_uploaded",
            "title": f"Document uploaded: {doc.original_filename}",
            "timestamp": doc.upload_date,
            "icon": "document",
            "color": "blue"
        })
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]

def _get_patient_demographics(clinic_id: int, db: Session) -> Dict[str, Any]:
    """Get patient demographic breakdown."""
    
    # Gender distribution
    gender_stats = db.query(Patient.gender, func.count(Patient.id)).filter(
        Patient.clinic_id == clinic_id
    ).group_by(Patient.gender).all()
    
    gender_distribution = {
        str(gender.value) if gender else 'not_specified': count 
        for gender, count in gender_stats
    }
    
    # Age distribution
    from datetime import date
    today = date.today()
    age_groups = {'0-18': 0, '19-35': 0, '36-55': 0, '56-70': 0, '71+': 0}
    
    patients_with_dob = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.date_of_birth.isnot(None)
    ).all()
    
    for patient in patients_with_dob:
        age = today.year - patient.date_of_birth.year
        if patient.date_of_birth.month > today.month or \
           (patient.date_of_birth.month == today.month and patient.date_of_birth.day > today.day):
            age -= 1
        
        if age <= 18:
            age_groups['0-18'] += 1
        elif age <= 35:
            age_groups['19-35'] += 1
        elif age <= 55:
            age_groups['36-55'] += 1
        elif age <= 70:
            age_groups['56-70'] += 1
        else:
            age_groups['71+'] += 1
    
    return {
        "gender_distribution": gender_distribution,
        "age_distribution": age_groups,
        "total_with_age_data": len(patients_with_dob)
    }

def _get_system_alerts(clinic_id: int, db: Session) -> List[Dict[str, Any]]:
    """Get system alerts and notifications."""
    
    alerts = []
    
    # Check for failed document processing
    failed_docs = db.query(Document).filter(
        Document.clinic_id == clinic_id,
        Document.status == DocumentStatus.FAILED
    ).count()
    
    if failed_docs > 0:
        alerts.append({
            "type": "warning",
            "title": f"{failed_docs} document(s) failed processing",
            "message": "Review failed documents and retry processing",
            "action": "view_failed_documents"
        })
    
    # Check storage usage (if over 80% of some limit)
    storage_used = db.query(func.sum(Document.file_size)).filter(
        Document.clinic_id == clinic_id
    ).scalar() or 0
    
    storage_limit = 5 * 1024 * 1024 * 1024  # 5GB limit
    if storage_used > storage_limit * 0.8:
        alerts.append({
            "type": "info",
            "title": "Storage limit approaching",
            "message": f"Using {storage_used / 1024 / 1024:.1f}MB of storage",
            "action": "manage_storage"
        })
    
    # Check for unprocessed documents
    unprocessed = db.query(Document).filter(
        Document.clinic_id == clinic_id,
        Document.status == DocumentStatus.UPLOADED
    ).count()
    
    if unprocessed > 10:
        alerts.append({
            "type": "info",
            "title": f"{unprocessed} documents waiting for processing",
            "message": "Consider processing pending documents",
            "action": "process_documents"
        })
    
    return alerts