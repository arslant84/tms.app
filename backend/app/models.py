import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base


class TravelType(str, enum.Enum):
    DOMESTIC = "domestic"
    OVERSEAS = "overseas"
    OVERSEAS_HLP = "overseas_hlp"
    EXTERNAL = "external"


class RequestStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    FOCAL = "focal"
    HOD = "hod"
    TICKETING_CLERK = "ticketing_clerk"
    EXTERNAL = "external"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # Keeping nullable=True for compatibility
    email = Column(String, unique=True, nullable=True)  # Keeping nullable=True for compatibility
    hashed_password = Column(String, nullable=True)  # Password hash
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE, server_default=UserRole.EMPLOYEE.name)
    department = Column(String, nullable=True, server_default="General")
    is_admin = Column(Boolean, default=False, server_default="false")  # Admin flag
    is_active = Column(Boolean, default=True, server_default="true")  # Account status
    
    # Relationships
    submitted_requests = relationship("TravelRequest", back_populates="submitter", foreign_keys="TravelRequest.submitted_by")
    reviewed_requests = relationship("TravelRequest", back_populates="reviewer", foreign_keys="TravelRequest.reviewed_by")
    approved_requests = relationship("TravelRequest", back_populates="approver", foreign_keys="TravelRequest.approved_by")


class TravelRequest(Base):
    __tablename__ = "travel_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    travel_type = Column(Enum(TravelType), nullable=False)
    form_data = Column(JSONB, nullable=False)
    status = Column(Enum(RequestStatus), nullable=False, default=RequestStatus.DRAFT, server_default=RequestStatus.DRAFT.name)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cost_center = Column(String, nullable=False)
    
    # Additional fields for tracking and workflow
    submission_date = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    approval_date = Column(DateTime, nullable=True)
    processing_date = Column(DateTime, nullable=True)
    rejection_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # For external travel requests
    authority_letter_no = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    
    # For HLP travel requests
    hlp_number = Column(String, nullable=True)
    
    # Common dates for all travel types
    travel_start_date = Column(DateTime, nullable=True)
    travel_end_date = Column(DateTime, nullable=True)
    
    # Tracking fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    submitter = relationship("User", back_populates="submitted_requests", foreign_keys=[submitted_by])
    reviewer = relationship("User", back_populates="reviewed_requests", foreign_keys=[reviewed_by])
    approver = relationship("User", back_populates="approved_requests", foreign_keys=[approved_by])
    audit_logs = relationship("AuditLog", back_populates="travel_request")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    travel_request_id = Column(UUID(as_uuid=True), ForeignKey("travel_requests.id"), nullable=False)
    action = Column(String, nullable=False)
    action_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    previous_status = Column(Enum(RequestStatus), nullable=True)
    new_status = Column(Enum(RequestStatus), nullable=True)
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
    
    # Relationships
    travel_request = relationship("TravelRequest", back_populates="audit_logs")
    user = relationship("User")