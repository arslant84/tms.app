from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from . import models, schemas
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import hashlib
import secrets

# Password hashing functions
def get_password_hash(password):
    """Hash a password using SHA-256 with a random salt"""
    # Generate a random salt
    salt = secrets.token_hex(16)
    # Hash the password with the salt
    pwdhash = hashlib.sha256((password + salt).encode()).hexdigest()
    # Return the salt and hash together
    return f"sha256${salt}${pwdhash}"

def verify_password(plain_password, hashed_password):
    """Verify a password against a hash"""
    if not hashed_password:
        return False
        
    # Check if it's our new SHA-256 format
    if hashed_password.startswith('sha256$'):
        # Extract the salt and hash
        parts = hashed_password.split('$')
        if len(parts) != 3:
            return False
            
        _, salt, stored_hash = parts
        # Hash the provided password with the same salt
        computed_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        # Compare the computed hash with the stored hash
        return secrets.compare_digest(computed_hash, stored_hash)
    
    # For backward compatibility with passlib hashes (if any)
    # You would need to install passlib and bcrypt for this to work
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)
    except (ImportError, Exception):
        # If passlib is not available or verification fails
        return False

# User CRUD operations
def create_user(db: Session, user: schemas.UserCreate):
    # Hash the password
    hashed_password = get_password_hash(user.password)
    
    # Create the user with hashed password
    db_user = models.User(
        name=user.name,
        email=user.email,
        role=user.role,
        department=user.department,
        hashed_password=hashed_password,
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        return None
        
    # Get update data excluding unset fields
    update_data = user_update.dict(exclude_unset=True)
    
    # Hash password if it's being updated
    if 'password' in update_data and update_data['password']:
        update_data['hashed_password'] = get_password_hash(update_data.pop('password'))
    
    # Update fields
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email=email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    if not user.is_active:
        return False
    return user

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users_by_role(db: Session, role: models.UserRole):
    return db.query(models.User).filter(models.User.role == role).all()

def get_users_by_department(db: Session, department: str):
    return db.query(models.User).filter(models.User.department == department).all()

# Travel Request CRUD operations
def create_travel_request(db: Session, travel_request: schemas.TravelRequestCreate, user_id: int):
    # Create travel request with all fields from the schema
    travel_request_data = travel_request.dict(exclude_unset=True)
    
    # Create the database model
    db_travel_request = models.TravelRequest(
        travel_type=travel_request.travel_type,
        form_data=travel_request.form_data,
        cost_center=travel_request.cost_center,
        submitted_by=user_id,
        status=models.RequestStatus.DRAFT,
        
        # Add specific fields for travel types
        authority_letter_no=travel_request.authority_letter_no,
        organization=travel_request.organization,
        hlp_number=travel_request.hlp_number,
        
        # Add travel dates if available
        travel_start_date=travel_request.travel_start_date,
        travel_end_date=travel_request.travel_end_date
    )
    
    db.add(db_travel_request)
    db.commit()
    db.refresh(db_travel_request)
    return db_travel_request

def get_travel_request(db: Session, travel_request_id: uuid.UUID):
    return db.query(models.TravelRequest).filter(models.TravelRequest.id == travel_request_id).first()

def get_travel_request_with_details(db: Session, travel_request_id: uuid.UUID):
    return db.query(models.TravelRequest).\
        options(
            joinedload(models.TravelRequest.submitter),
            joinedload(models.TravelRequest.reviewer),
            joinedload(models.TravelRequest.approver)
        ).\
        filter(models.TravelRequest.id == travel_request_id).first()

def get_travel_requests_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.TravelRequest).\
        filter(models.TravelRequest.submitted_by == user_id).\
        order_by(models.TravelRequest.created_at.desc()).\
        offset(skip).limit(limit).all()

def get_pending_travel_requests(db: Session, role: models.UserRole, department: Optional[str] = None, skip: int = 0, limit: int = 100, travel_type: Optional[models.TravelType] = None):
    query = db.query(models.TravelRequest).\
        join(models.User, models.TravelRequest.submitted_by == models.User.id)
    
    # Filter by travel type if specified
    if travel_type:
        query = query.filter(models.TravelRequest.travel_type == travel_type)
    
    if role == models.UserRole.FOCAL:
        # Focal point sees submitted requests from their department
        query = query.filter(
            and_(
                models.TravelRequest.status == models.RequestStatus.SUBMITTED,
                models.User.department == department
            )
        )
    elif role == models.UserRole.HOD:
        # HOD sees requests that have been reviewed by focal points in their department
        query = query.filter(
            and_(
                models.TravelRequest.status == models.RequestStatus.SUBMITTED,
                models.User.department == department,
                models.TravelRequest.reviewed_by.isnot(None)
            )
        )
    elif role == models.UserRole.TICKETING_CLERK:
        # Ticketing clerk sees approved requests
        query = query.filter(models.TravelRequest.status == models.RequestStatus.APPROVED)
    
    # Order by submission date (most recent first) if available, otherwise created_at
    query = query.order_by(
        models.TravelRequest.submission_date.desc().nullslast(),
        models.TravelRequest.created_at.desc()
    )
    
    return query.offset(skip).limit(limit).all()

def update_travel_request(db: Session, travel_request_id: uuid.UUID, travel_request_update: schemas.TravelRequestUpdate):
    db_travel_request = db.query(models.TravelRequest).filter(models.TravelRequest.id == travel_request_id).first()
    if db_travel_request is None:
        return None
    
    # Get update data excluding unset fields
    update_data = travel_request_update.dict(exclude_unset=True)
    
    # If status is changing to PROCESSED, set processing date
    if 'status' in update_data and update_data['status'] == models.RequestStatus.PROCESSED:
        update_data['processing_date'] = datetime.now()
    
    # Update fields
    for key, value in update_data.items():
        setattr(db_travel_request, key, value)
    
    # Always update the updated_at timestamp
    db_travel_request.updated_at = datetime.now()
    
    db.add(db_travel_request)
    db.commit()
    db.refresh(db_travel_request)
    return db_travel_request

def submit_travel_request(db: Session, travel_request_id: uuid.UUID, user_id: int):
    db_travel_request = db.query(models.TravelRequest).filter(
        and_(
            models.TravelRequest.id == travel_request_id,
            models.TravelRequest.submitted_by == user_id,
            models.TravelRequest.status == models.RequestStatus.DRAFT
        )
    ).first()
    
    if db_travel_request is None:
        return None
    
    # Validate form data based on travel type before submission
    validate_travel_request_form(db_travel_request)
    
    # Update status to submitted
    previous_status = db_travel_request.status
    db_travel_request.status = models.RequestStatus.SUBMITTED
    db_travel_request.updated_at = datetime.now()
    db_travel_request.submission_date = datetime.now()
    
    # Create audit log
    audit_log = models.AuditLog(
        travel_request_id=travel_request_id,
        action="submit",
        action_by=user_id,
        previous_status=previous_status,
        new_status=models.RequestStatus.SUBMITTED,
        comments="Travel request submitted"
    )
    
    db.add(db_travel_request)
    db.add(audit_log)
    db.commit()
    db.refresh(db_travel_request)
    return db_travel_request


def validate_travel_request_form(travel_request: models.TravelRequest):
    """Validate the form data based on travel type before submission"""
    travel_type = travel_request.travel_type
    form_data = travel_request.form_data
    
    # Common validation for all travel types
    if 'purpose_of_travel' not in form_data or not form_data['purpose_of_travel']:
        raise ValueError("Purpose of travel is required")
    
    # Type-specific validation
    if travel_type == models.TravelType.DOMESTIC:
        if 'employee_details' not in form_data or not form_data['employee_details']:
            raise ValueError("Employee details are required for domestic travel")
        if 'itinerary' not in form_data or not form_data['itinerary']:
            raise ValueError("Itinerary is required for domestic travel")
    
    elif travel_type == models.TravelType.OVERSEAS:
        if 'employee_details' not in form_data or not form_data['employee_details']:
            raise ValueError("Employee details are required for overseas travel")
        if 'itinerary' not in form_data or not form_data['itinerary']:
            raise ValueError("Itinerary is required for overseas travel")
    
    elif travel_type == models.TravelType.OVERSEAS_HLP:
        if 'employee_details' not in form_data or not form_data['employee_details']:
            raise ValueError("Employee details are required for overseas HLP travel")
        if 'itinerary' not in form_data or not form_data['itinerary']:
            raise ValueError("Itinerary is required for overseas HLP travel")
        if not travel_request.hlp_number:
            raise ValueError("HLP number is required for overseas HLP travel")
    
    elif travel_type == models.TravelType.EXTERNAL:
        if 'requestor_details' not in form_data or not form_data['requestor_details']:
            raise ValueError("Requestor details are required for external travel")
        if 'itinerary' not in form_data or not form_data['itinerary']:
            raise ValueError("Itinerary is required for external travel")
        if not travel_request.authority_letter_no:
            raise ValueError("Authority letter number is required for external travel")
        if not travel_request.organization:
            raise ValueError("Organization is required for external travel")
    
    # Validate accommodation date ranges if present
    if 'accommodation' in form_data and form_data['accommodation']:
        for accommodation in form_data['accommodation']:
            if all(k in accommodation for k in ['check_in_date', 'check_out_date']):
                try:
                    check_in = datetime.fromisoformat(accommodation['check_in_date']) \
                        if isinstance(accommodation['check_in_date'], str) \
                        else accommodation['check_in_date']
                    
                    check_out = datetime.fromisoformat(accommodation['check_out_date']) \
                        if isinstance(accommodation['check_out_date'], str) \
                        else accommodation['check_out_date']
                    
                    if check_in >= check_out:
                        raise ValueError("Check-in date must be before check-out date")
                except (ValueError, TypeError):
                    raise ValueError("Invalid date format in accommodation dates")

def review_travel_request(db: Session, travel_request_id: uuid.UUID, reviewer_id: int, comments: Optional[str] = None):
    db_travel_request = db.query(models.TravelRequest).filter(
        and_(
            models.TravelRequest.id == travel_request_id,
            models.TravelRequest.status == models.RequestStatus.SUBMITTED,
            models.TravelRequest.reviewed_by.is_(None)
        )
    ).first()
    
    if db_travel_request is None:
        return None
    
    # Update reviewer and review date
    db_travel_request.reviewed_by = reviewer_id
    db_travel_request.review_date = datetime.now()
    db_travel_request.updated_at = datetime.now()
    
    # Create audit log
    audit_log = models.AuditLog(
        travel_request_id=travel_request_id,
        action="review",
        action_by=reviewer_id,
        previous_status=db_travel_request.status,
        new_status=db_travel_request.status,
        comments=comments or "Travel request reviewed"
    )
    
    db.add(db_travel_request)
    db.add(audit_log)
    db.commit()
    db.refresh(db_travel_request)
    return db_travel_request

def approve_travel_request(db: Session, travel_request_id: uuid.UUID, approver_id: int, comments: Optional[str] = None):
    db_travel_request = db.query(models.TravelRequest).filter(
        and_(
            models.TravelRequest.id == travel_request_id,
            models.TravelRequest.status == models.RequestStatus.SUBMITTED,
            models.TravelRequest.reviewed_by.isnot(None)
        )
    ).first()
    
    if db_travel_request is None:
        return None
    
    # Update approver, status, and approval date
    previous_status = db_travel_request.status
    db_travel_request.approved_by = approver_id
    db_travel_request.status = models.RequestStatus.APPROVED
    db_travel_request.approval_date = datetime.now()
    db_travel_request.updated_at = datetime.now()
    
    # Create audit log
    audit_log = models.AuditLog(
        travel_request_id=travel_request_id,
        action="approve",
        action_by=approver_id,
        previous_status=previous_status,
        new_status=models.RequestStatus.APPROVED,
        comments=comments or "Travel request approved"
    )
    
    db.add(db_travel_request)
    db.add(audit_log)
    db.commit()
    db.refresh(db_travel_request)
    return db_travel_request

def reject_travel_request(db: Session, travel_request_id: uuid.UUID, user_id: int, comments: str):
    db_travel_request = db.query(models.TravelRequest).filter(
        and_(
            models.TravelRequest.id == travel_request_id,
            models.TravelRequest.status == models.RequestStatus.SUBMITTED
        )
    ).first()
    
    if db_travel_request is None:
        return None
    
    # Update status, rejection date, and reason
    previous_status = db_travel_request.status
    db_travel_request.status = models.RequestStatus.REJECTED
    db_travel_request.rejection_date = datetime.now()
    db_travel_request.rejection_reason = comments
    db_travel_request.updated_at = datetime.now()
    
    # Create audit log
    audit_log = models.AuditLog(
        travel_request_id=travel_request_id,
        action="reject",
        action_by=user_id,
        previous_status=previous_status,
        new_status=models.RequestStatus.REJECTED,
        comments=comments
    )
    
    db.add(db_travel_request)
    db.add(audit_log)
    db.commit()
    db.refresh(db_travel_request)
    return db_travel_request

# Audit Log CRUD operations
def create_audit_log(db: Session, audit_log: schemas.AuditLogCreate):
    db_audit_log = models.AuditLog(**audit_log.dict())
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log

def get_audit_logs_by_travel_request(db: Session, travel_request_id: uuid.UUID):
    return db.query(models.AuditLog).\
        filter(models.AuditLog.travel_request_id == travel_request_id).\
        order_by(models.AuditLog.timestamp.desc()).all()