from pydantic import BaseModel, Field, UUID4, EmailStr, model_validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from .models import TravelType, RequestStatus, UserRole

# User schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    department: str
    role: UserRole

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class UserResponse(UserBase):
    id: int
    is_admin: bool = False
    is_active: bool = True
    
    class Config:
        from_attributes = True
        
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    department: Optional[str] = None
    role: Optional[UserRole] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    
# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: Union[int, str]
    name: str
    role: UserRole
    is_admin: bool

class TokenData(BaseModel):
    user_id: Optional[int] = None

# Travel Request schemas
class TravelRequestBase(BaseModel):
    travel_type: TravelType
    form_data: Dict[str, Any]
    cost_center: str

class TravelRequestCreate(TravelRequestBase):
    # Additional fields for specific travel types
    authority_letter_no: Optional[str] = None  # For external travel
    organization: Optional[str] = None  # For external travel
    hlp_number: Optional[str] = None  # For HLP travel
    travel_start_date: Optional[datetime] = None
    travel_end_date: Optional[datetime] = None
    
    @model_validator(mode='after')
    def validate_form_data(self) -> 'TravelRequestCreate':
        travel_type = self.travel_type
        form_data = self.form_data
        
        # Common required fields for all travel types
        required_fields = ['purpose_of_travel']
        
        # Validate based on travel type
        if travel_type == TravelType.DOMESTIC:
            # Domestic travel validation
            if 'employee_details' not in form_data:
                raise ValueError("Employee details are required for domestic travel")
            if 'itinerary' not in form_data or not form_data['itinerary']:
                raise ValueError("Itinerary is required for domestic travel")
                
        elif travel_type == TravelType.OVERSEAS:
            # Overseas travel validation
            if 'employee_details' not in form_data:
                raise ValueError("Employee details are required for overseas travel")
            if 'itinerary' not in form_data or not form_data['itinerary']:
                raise ValueError("Itinerary is required for overseas travel")
                
        elif travel_type == TravelType.OVERSEAS_HLP:
            # Overseas HLP validation
            if 'employee_details' not in form_data:
                raise ValueError("Employee details are required for overseas HLP travel")
            if 'itinerary' not in form_data or not form_data['itinerary']:
                raise ValueError("Itinerary is required for overseas HLP travel")
            if not self.hlp_number:
                raise ValueError("HLP number is required for overseas HLP travel")
                
        elif travel_type == TravelType.EXTERNAL:
            # External travel validation
            if 'requestor_details' not in form_data:
                raise ValueError("Requestor details are required for external travel")
            if 'itinerary' not in form_data or not form_data['itinerary']:
                raise ValueError("Itinerary is required for external travel")
            if not self.authority_letter_no:
                raise ValueError("Authority letter number is required for external travel")
            if not self.organization:
                raise ValueError("Organization is required for external travel")
        
        # Extract travel dates from itinerary if available
        if 'itinerary' in form_data and form_data['itinerary']:
            # Sort itinerary by date
            try:
                sorted_itinerary = sorted(form_data['itinerary'], 
                                          key=lambda x: datetime.fromisoformat(x['date']) 
                                          if isinstance(x['date'], str) else x['date'])
                
                # Set travel start and end dates
                first_date = sorted_itinerary[0]['date']
                last_date = sorted_itinerary[-1]['date']
                
                self.travel_start_date = datetime.fromisoformat(first_date) if isinstance(first_date, str) else first_date
                self.travel_end_date = datetime.fromisoformat(last_date) if isinstance(last_date, str) else last_date
            except (KeyError, ValueError, TypeError):
                # If there's an error parsing dates, we'll skip setting travel dates
                pass
        
        # Validate accommodation date ranges if present
        if 'accommodation' in form_data and form_data['accommodation']:
            for accommodation in form_data['accommodation']:
                if all(k in accommodation for k in ['check_in_date', 'check_out_date']):
                    check_in = datetime.fromisoformat(accommodation['check_in_date']) \
                        if isinstance(accommodation['check_in_date'], str) \
                        else accommodation['check_in_date']
                    
                    check_out = datetime.fromisoformat(accommodation['check_out_date']) \
                        if isinstance(accommodation['check_out_date'], str) \
                        else accommodation['check_out_date']
                    
                    if check_in >= check_out:
                        raise ValueError("Check-in date must be before check-out date")
        
        # Set cost center from form data if not provided directly
        if not self.cost_center:
            if travel_type in [TravelType.DOMESTIC, TravelType.OVERSEAS, TravelType.OVERSEAS_HLP]:
                if 'employee_details' in form_data and 'dept_cost_center' in form_data['employee_details']:
                    self.cost_center = form_data['employee_details']['dept_cost_center']
            elif travel_type == TravelType.EXTERNAL:
                if 'requestor_details' in form_data and 'cost_center' in form_data['requestor_details']:
                    self.cost_center = form_data['requestor_details']['cost_center']
        
        return self

class TravelRequestUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    reviewed_by: Optional[int] = None
    approved_by: Optional[int] = None
    form_data: Optional[Dict[str, Any]] = None
    
    # Additional fields for specific travel types
    authority_letter_no: Optional[str] = None
    organization: Optional[str] = None
    hlp_number: Optional[str] = None
    
    # Tracking dates
    submission_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    approval_date: Optional[datetime] = None
    processing_date: Optional[datetime] = None
    rejection_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Travel dates
    travel_start_date: Optional[datetime] = None
    travel_end_date: Optional[datetime] = None

class TravelRequestResponse(TravelRequestBase):
    id: UUID4
    status: RequestStatus
    submitted_by: int
    reviewed_by: Optional[int] = None
    approved_by: Optional[int] = None
    
    # Additional fields for specific travel types
    authority_letter_no: Optional[str] = None  # For external travel
    organization: Optional[str] = None  # For external travel
    hlp_number: Optional[str] = None  # For HLP travel
    
    # Tracking dates
    submission_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    approval_date: Optional[datetime] = None
    processing_date: Optional[datetime] = None
    rejection_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Travel dates
    travel_start_date: Optional[datetime] = None
    travel_end_date: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TravelRequestDetailResponse(TravelRequestResponse):
    submitter: UserResponse
    reviewer: Optional[UserResponse] = None
    approver: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True

# Audit Log schemas
class AuditLogCreate(BaseModel):
    travel_request_id: UUID4
    action: str
    action_by: int
    previous_status: Optional[RequestStatus] = None
    new_status: Optional[RequestStatus] = None
    comments: Optional[str] = None

class AuditLogResponse(AuditLogCreate):
    id: UUID4
    timestamp: datetime
    
    class Config:
        from_attributes = True