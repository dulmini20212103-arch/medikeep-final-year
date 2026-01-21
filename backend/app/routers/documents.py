from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pathlib import Path
import os

from ..database import get_db
from ..models.document import Document, DocumentStatus, DocumentType
from ..models.patient import Patient
from ..models.user import User, UserRole
from ..schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, 
    DocumentListResponse, DocumentAssignmentRequest, DocumentUploadResponse
)
from ..models.clinic import Clinic
from ..utils.deps import get_current_active_user, require_clinic_access
from ..utils.file_handler import save_upload_file, delete_file, get_file_info

router = APIRouter(prefix="/documents", tags=["documents"])

#Upload a document
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    patient_id: Optional[int] = None,
    document_type: Optional[DocumentType] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Upload a new document."""
    
    # Save file to storage
    try:
        file_path, unique_filename, file_size = await save_upload_file(file)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    # Get clinic_id based on user role
    clinic_id = None
    if current_user.role == UserRole.CLINIC_ADMIN or current_user.role == UserRole.CLINIC_STAFF:
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if not clinic:
            # For clinic staff, find clinic through relationships
            # This should be improved with proper clinic-user relationships
            clinic_id = 1  # Default for now - should be properly implemented
        else:
            clinic_id = clinic.id
    
    if not clinic_id:
        raise HTTPException(status_code=400, detail="Cannot determine clinic association")
    
    # Validate patient assignment
    if patient_id:
        patient = db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id
        ).first()
        if not patient:
            # Clean up uploaded file
            delete_file(file_path)
            raise HTTPException(status_code=404, detail="Patient not found in your clinic")
    
    # Create document record
    document = Document(
        patient_id=patient_id,
        clinic_id=clinic_id,
        filename=unique_filename,
        original_filename=file.filename or "unknown",
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        document_type=document_type or DocumentType.OTHER,
        status=DocumentStatus.UPLOADED,
        notes=notes
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return DocumentUploadResponse(
        message="Document uploaded successfully",
        document=DocumentResponse.from_orm(document)
    )

#List documents with filters
@router.get("/", response_model=DocumentListResponse)
async def get_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_id: Optional[int] = None,
    status: Optional[DocumentStatus] = None,
    document_type: Optional[DocumentType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get documents with filtering and pagination."""
    
    # Build query based on user role
    query = db.query(Document)
    
    if current_user.role == UserRole.PATIENT:
        # Patients can only see their own documents
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        query = query.filter(Document.patient_id == patient.id)
    
    elif current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        # Clinic users see documents from their clinic
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic:
            query = query.filter(Document.clinic_id == clinic.id)
        else:
            # For clinic staff, implement proper clinic association
            pass
    
    # Apply filters
    if patient_id:
        query = query.filter(Document.patient_id == patient_id)
    if status:
        query = query.filter(Document.status == status)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    documents = query.offset(offset).limit(per_page).all()
    
    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        page=page,
        per_page=per_page
    )

#Retrieve a single document
@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get document by ID."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or document.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    elif current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic and document.clinic_id != clinic.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return DocumentResponse.from_orm(document)

#Download document file
@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download document file."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions (same logic as get_document)
    if current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or document.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    elif current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic and document.clinic_id != clinic.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type
    )

#Assign document to a patient
@router.put("/{document_id}/assign", response_model=DocumentResponse)
async def assign_document_to_patient(
    document_id: int,
    assignment: DocumentAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Assign document to a patient."""
    
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check clinic permission
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if clinic and document.clinic_id != clinic.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate patient
    patient = db.query(Patient).filter(
        Patient.id == assignment.patient_id,
        Patient.clinic_id == document.clinic_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found in clinic")
    
    # Update assignment
    document.patient_id = assignment.patient_id
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)

#Update document metadata
@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Update document metadata."""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if clinic and document.clinic_id != clinic.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Only updates fields that are provided
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)

#Delete a document
@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinic_access)
):
    """Delete document."""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
    if clinic and document.clinic_id != clinic.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete file from storage
    delete_file(document.file_path)
    
    # Delete database record
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}