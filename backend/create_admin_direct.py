"""
Script to directly create an admin user in the database.
This bypasses the ORM and uses direct SQL to create the user.
"""
import os
import sys
import argparse
import hashlib
import base64
import secrets
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

# Password hashing with hashlib
def get_password_hash(password: str) -> str:
    """Hash a password using SHA-256 with a random salt"""
    # Generate a random salt
    salt = secrets.token_hex(16)
    # Hash the password with the salt
    pwdhash = hashlib.sha256((password + salt).encode()).hexdigest()
    # Return the salt and hash together
    return f"sha256${salt}${pwdhash}"

def create_admin_user(name: str, email: str, password: str, department: str):
    """Create an admin user directly in the database using SQL."""
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # Hash the password
    hashed_password = get_password_hash(password)
    
    with engine.connect() as connection:
        # Begin a transaction
        with connection.begin():
            # Check if the user already exists
            result = connection.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            )
            user = result.fetchone()
            
            if user:
                print(f"User with email {email} already exists.")
                return False
            
            # First, ensure the users table has all required columns
            print("Ensuring users table has required columns...")
            
            # Add hashed_password column if it doesn't exist
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'hashed_password'
                    ) THEN
                        ALTER TABLE users ADD COLUMN hashed_password VARCHAR;
                    END IF;
                END
                $$;
            """))
            
            # Add is_admin column if it doesn't exist
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'is_admin'
                    ) THEN
                        ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
                    END IF;
                END
                $$;
            """))
            
            # Add is_active column if it doesn't exist
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'is_active'
                    ) THEN
                        ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
                    END IF;
                END
                $$;
            """))
            
            # Add department column if it doesn't exist
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'department'
                    ) THEN
                        ALTER TABLE users ADD COLUMN department VARCHAR DEFAULT 'General';
                    END IF;
                END
                $$;
            """))
            
            # Insert the admin user
            print("Creating admin user...")
            connection.execute(
                text("""
                    INSERT INTO users (name, email, hashed_password, department, is_admin, is_active) 
                    VALUES (:name, :email, :hashed_password, :department, TRUE, TRUE)
                """),
                {
                    "name": name,
                    "email": email,
                    "hashed_password": hashed_password,
                    "department": department
                }
            )
            
            print(f"Admin user created successfully: {name} ({email})")
            return True

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
