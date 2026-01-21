from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc
#Used for time-based filtering and statistics
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models.audit_log import AuditLog, AuditAction, AuditEntityType
from ..models.user import User, UserRole
from ..models.clinic import Clinic
#Controls what data is exposed
from ..schemas.audit import (
    AuditLogResponse, AuditLogListResponse, AuditLogFilter, AuditLogStats
)
#Centralized audit log creation
from ..utils.deps import get_current_active_user, require_admin
from ..utils.audit import get_audit_logger

router = APIRouter(prefix="/audit", tags=["audit"])

#Returns audit logs and Applies role-based access control
@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    #Prevents database overload
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    action: Optional[AuditAction] = None,
    entity_type: Optional[AuditEntityType] = None,
    user_id: Optional[int] = None,
    clinic_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    success: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get audit logs with filtering (role-based access)."""
    
    # Build base query
    query = db.query(AuditLog).options(joinedload(AuditLog.user))
    
    # Apply role-based filtering
    if current_user.role == UserRole.ADMIN:
        # Admins can see all logs
        pass
    elif current_user.role in [UserRole.CLINIC_ADMIN, UserRole.CLINIC_STAFF]:
        # Clinic users can only see logs from their clinic
        clinic = db.query(Clinic).filter(Clinic.admin_user_id == current_user.id).first()
        if clinic:
            query = query.filter(AuditLog.clinic_id == clinic.id)
        else:
            # If no clinic found, show only their own actions
            query = query.filter(AuditLog.user_id == current_user.id)
    elif current_user.role == UserRole.PATIENT:
        # Patients can only see logs related to themselves
        query = query.filter(
            and_(
                AuditLog.user_id == current_user.id,
                AuditLog.entity_type.in_([AuditEntityType.USER, AuditEntityType.DOCUMENT])
            )
        )
    else:
        #This enforces least-privilege access
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if clinic_id:
        query = query.filter(AuditLog.clinic_id == clinic_id)
    if patient_id:
        query = query.filter(AuditLog.patient_id == patient_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)
    if success is not None:
        query = query.filter(AuditLog.success == success)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    offset = (page - 1) * per_page
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(per_page).all()
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/stats", response_model=AuditLogStats)
async def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get audit log statistics (admin only)."""
    
    # Time ranges
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Basic counts
    total_logs = db.query(AuditLog).count()
    logs_today = db.query(AuditLog).filter(AuditLog.created_at >= today_start).count()
    logs_this_week = db.query(AuditLog).filter(AuditLog.created_at >= week_start).count()
    logs_this_month = db.query(AuditLog).filter(AuditLog.created_at >= month_start).count()
    
    # Top actions
    top_actions_query = db.query(
        AuditLog.action,
        func.count(AuditLog.id)
    ).group_by(AuditLog.action).order_by(desc(func.count(AuditLog.id))).limit(10).all()
    
    top_actions = {action.value: count for action, count in top_actions_query}
    
    # Top entity types
    top_entities_query = db.query(
        AuditLog.entity_type,
        func.count(AuditLog.id)
    ).group_by(AuditLog.entity_type).order_by(desc(func.count(AuditLog.id))).limit(10).all()
    
    top_entities = {entity.value: count for entity, count in top_entities_query}
    
    # Recent activities
    recent_logs = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(10).all()
    
    return AuditLogStats(
        total_logs=total_logs,
        logs_today=logs_today,
        logs_this_week=logs_this_week,
        logs_this_month=logs_this_month,
        top_actions=top_actions,
        top_entities=top_entities,
        recent_activities=[AuditLogResponse.from_orm(log) for log in recent_logs]
    )

#current user’s actions
@router.get("/my-activity", response_model=AuditLogListResponse)
async def get_my_activity(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's audit activity."""
    
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(per_page).all()
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page
    )

@router.post("/test")
async def create_test_audit_log(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a test audit log entry (for testing purposes)."""
    #Uses centralized logging utility
    audit_logger = get_audit_logger(db)
    
    audit_log = audit_logger.log_user_action(
        action=AuditAction.VIEW,
        user=current_user,
        description="Test audit log created via API",
        request=request,
        metadata={"test": True, "endpoint": "/audit/test"}
    )
    
    return {"message": "Test audit log created", "audit_log_id": audit_log.id}