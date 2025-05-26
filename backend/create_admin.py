import os
import sys
import argparse
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.database import SessionLocal, engine
from app.models import UserRole

def create_admin_user(name: str, email: str, password: str, department: str):
    """
    Create an admin user with the provided details.
    This should only be run once to set up the initial admin account.
    """
    # Create database tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if any users exist
        users_count = db.query(models.User).count()
        if users_count > 0:
            print("Error: Users already exist in the database. This script should only be run on a fresh installation.")
            return False
        
        # Create admin user
        admin_user = schemas.UserCreate(
            name=name,
            email=email,
            password=password,
            department=department,
            role=UserRole.HOD,  # Admin is typically a Head of Department
            is_admin=True
        )
        
        # Add to database
        user = crud.create_user(db=db, user=admin_user)
        print(f"Admin user created successfully: {user.name} ({user.email})")
        return True
    
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user for the Travel Request Management System")
    parser.add_argument("--name", required=True, help="Admin's full name")
    parser.add_argument("--email", required=True, help="Admin's email address")
    parser.add_argument("--password", required=True, help="Admin's password")
    parser.add_argument("--department", required=True, help="Admin's department")
    
    args = parser.parse_args()
    
    success = create_admin_user(
        name=args.name,
        email=args.email,
        password=args.password,
        department=args.department
    )
    
    sys.exit(0 if success else 1)
