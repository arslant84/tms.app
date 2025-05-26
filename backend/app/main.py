from fastapi import FastAPI, Depends, HTTPException, Request, Body, Path, Query, status, Security
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import json
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from . import crud, models, schemas
from .database import SessionLocal, engine

# Create all database tables
models.Base.metadata.create_all(bind=engine)

# JWT Configuration
SECRET_KEY = "your-secret-key-for-jwt-token-generation"  # Should be stored in env variables in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

app = FastAPI(
    title="Travel Request Management System API",
    description="API for managing travel requests with different types and workflows",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "*"],  # Allow Angular dev server and any origin for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Authorization"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Root endpoint redirects to docs
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT Token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # Try to convert user_id to int, but handle the case where it might not be convertible
        try:
            user_id_int = int(user_id)
        except ValueError:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user(db, user_id=user_id_int)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    return current_user

# Role-based access control
def has_role(required_roles: List[models.UserRole]):
    async def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have sufficient permissions. Required roles: {required_roles}"
            )
        return current_user
    return role_checker

# Authentication endpoints
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "role": user.role,
        "is_admin": user.is_admin
    }

# User endpoints
@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only admins can create new users
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create new users"
        )
        
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    return crud.create_user(db=db, user=user)

# Special endpoint for initial admin creation (should be disabled in production)
@app.post("/admin/setup", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_initial_admin(user: schemas.UserCreate, setup_key: str = Query(...), db: Session = Depends(get_db)):
    # Check if the setup key matches the secret key (this is a simple security measure)
    if setup_key != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid setup key"
        )
        
    # Check if any users exist
    users_count = db.query(models.User).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin setup has already been completed"
        )
        
    # Force the user to be an admin
    user_dict = user.dict()
    user_dict["is_admin"] = True
    admin_user = schemas.UserCreate(**user_dict)
    
    return crud.create_user(db=db, user=admin_user)

@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check permissions - only admins can update other users
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this user"
        )
        
    # Only admins can change admin status
    if "is_admin" in user_update.dict(exclude_unset=True) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change admin status"
        )
        
    updated_user = crud.update_user(db=db, user_id=user_id, user_update=user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return updated_user

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

# Travel Request endpoints
@app.post("/trf/submit", response_model=schemas.TravelRequestResponse, status_code=status.HTTP_201_CREATED)
def create_travel_request(
    travel_request: schemas.TravelRequestCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Validate travel request based on type
    try:
        # Create the travel request
        db_travel_request = crud.create_travel_request(db=db, travel_request=travel_request, user_id=current_user.id)
        return db_travel_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/trf/{id}/submit", response_model=schemas.TravelRequestResponse)
def submit_travel_request(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        db_travel_request = crud.submit_travel_request(db=db, travel_request_id=id, user_id=current_user.id)
        if db_travel_request is None:
            raise HTTPException(status_code=404, detail="Travel request not found or not in draft status")
        return db_travel_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/trf/pending", response_model=List[schemas.TravelRequestResponse])
def get_pending_travel_requests(
    role: Optional[models.UserRole] = Query(None),
    travel_type: Optional[models.TravelType] = Query(None),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # If role is not provided, use the current user's role
    user_role = role if role else current_user.role
    
    # Only certain roles can view pending requests
    allowed_roles = [models.UserRole.FOCAL, models.UserRole.HOD, models.UserRole.TICKETING_CLERK]
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role {user_role} is not allowed to view pending requests"
        )
    
    # Get pending requests based on role, department and optional travel type
    pending_requests = crud.get_pending_travel_requests(
        db=db,
        role=user_role,
        department=current_user.department,
        travel_type=travel_type,
        skip=skip,
        limit=limit
    )
    return pending_requests

@app.get("/trf/{id}", response_model=schemas.TravelRequestDetailResponse)
def get_travel_request(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_travel_request = crud.get_travel_request_with_details(db=db, travel_request_id=id)
    if db_travel_request is None:
        raise HTTPException(status_code=404, detail="Travel request not found")
    
    # Check if user has access to this travel request
    is_owner = db_travel_request.submitted_by == current_user.id
    is_reviewer = db_travel_request.reviewed_by == current_user.id
    is_approver = db_travel_request.approved_by == current_user.id
    is_admin = current_user.role in [models.UserRole.HOD, models.UserRole.TICKETING_CLERK]
    is_focal = current_user.role == models.UserRole.FOCAL and current_user.department == db_travel_request.submitter.department
    
    if not (is_owner or is_reviewer or is_approver or is_admin or is_focal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this travel request"
        )
    
    # Mask sensitive data for non-HODs if needed
    if current_user.role != models.UserRole.HOD and not is_owner:
        # Implement masking of sensitive fields here if needed
        # For example, bank details in advance forms
        pass
    
    return db_travel_request

@app.put("/trf/{id}/review", response_model=schemas.TravelRequestResponse)
def review_travel_request(
    id: uuid.UUID,
    comments: Optional[str] = Body(None),
    current_user: models.User = Security(has_role([models.UserRole.FOCAL])),
    db: Session = Depends(get_db)
):
    db_travel_request = crud.review_travel_request(
        db=db,
        travel_request_id=id,
        reviewer_id=current_user.id,
        comments=comments
    )
    if db_travel_request is None:
        raise HTTPException(status_code=404, detail="Travel request not found or not in submitted status")
    return db_travel_request

@app.put("/trf/{id}/approve", response_model=schemas.TravelRequestResponse)
def approve_travel_request(
    id: uuid.UUID,
    comments: Optional[str] = Body(None),
    current_user: models.User = Security(has_role([models.UserRole.HOD])),
    db: Session = Depends(get_db)
):
    db_travel_request = crud.approve_travel_request(
        db=db,
        travel_request_id=id,
        approver_id=current_user.id,
        comments=comments
    )
    if db_travel_request is None:
        raise HTTPException(status_code=404, detail="Travel request not found or not ready for approval")
    
    # Trigger notifications to ticketing clerk (e.g., email/SMS)
    # This would be implemented with a background task or message queue in a real application
    
    return db_travel_request

@app.put("/trf/{id}/reject", response_model=schemas.TravelRequestResponse)
def reject_travel_request(
    id: uuid.UUID,
    comments: str = Body(...),
    current_user: models.User = Security(has_role([models.UserRole.FOCAL, models.UserRole.HOD])),
    db: Session = Depends(get_db)
):
    db_travel_request = crud.reject_travel_request(
        db=db,
        travel_request_id=id,
        user_id=current_user.id,
        comments=comments
    )
    if db_travel_request is None:
        raise HTTPException(status_code=404, detail="Travel request not found or not in submitted status")
    return db_travel_request

@app.put("/trf/{id}/process", response_model=schemas.TravelRequestResponse)
def process_travel_request(
    id: uuid.UUID,
    comments: Optional[str] = Body(None),
    current_user: models.User = Security(has_role([models.UserRole.TICKETING_CLERK])),
    db: Session = Depends(get_db)
):
    # Get the travel request
    db_travel_request = crud.get_travel_request(db=db, travel_request_id=id)
    if db_travel_request is None or db_travel_request.status != models.RequestStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Travel request not found or not approved")
    
    # Update status to processed and set processing date
    update_data = schemas.TravelRequestUpdate(
        status=models.RequestStatus.PROCESSED,
        processing_date=datetime.now()
    )
    db_travel_request = crud.update_travel_request(db=db, travel_request_id=id, travel_request_update=update_data)
    
    # Create audit log
    audit_log = schemas.AuditLogCreate(
        travel_request_id=id,
        action="process",
        action_by=current_user.id,
        previous_status=models.RequestStatus.APPROVED,
        new_status=models.RequestStatus.PROCESSED,
        comments=comments or "Travel request processed"
    )
    crud.create_audit_log(db=db, audit_log=audit_log)
    
    return db_travel_request

@app.get("/trf/{id}/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_travel_request_audit_logs(
    id: uuid.UUID,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # First check if user has access to this travel request
    db_travel_request = crud.get_travel_request(db=db, travel_request_id=id)
    if db_travel_request is None:
        raise HTTPException(status_code=404, detail="Travel request not found")
    
    is_owner = db_travel_request.submitted_by == current_user.id
    is_admin = current_user.role in [models.UserRole.HOD, models.UserRole.TICKETING_CLERK]
    is_focal = current_user.role == models.UserRole.FOCAL
    
    if not (is_owner or is_admin or is_focal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view audit logs for this travel request"
        )
    
    # Get audit logs
    audit_logs = crud.get_audit_logs_by_travel_request(db=db, travel_request_id=id)
    return audit_logs

@app.get("/trf/my-requests", response_model=List[schemas.TravelRequestResponse])
def get_my_travel_requests(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    travel_requests = crud.get_travel_requests_by_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return travel_requests