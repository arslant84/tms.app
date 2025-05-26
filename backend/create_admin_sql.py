"""
Script to create an admin user directly using SQL
This bypasses the ORM to ensure we can create the user even if the schema is not fully aligned
"""
import os
import sys
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

def create_admin_user(name: str, email: str, password: str, department: str):
    """Create an admin user directly using SQL."""
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    # Hash the password
    hashed_password = hash_password(password)
    
    try:
        # Connect to the database
        with engine.connect() as conn:
            # Check if the user already exists
            result = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            )
            user = result.fetchone()
            
            if user:
                print(f"User with email {email} already exists.")
                return False
            
            # Create the user
            conn.execute(
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
            
            # Commit the transaction
            conn.commit()
            
            print(f"Admin user created successfully: {name} ({email})")
            return True
    
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python create_admin_sql.py <name> <email> <password> <department>")
        sys.exit(1)
    
    name = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    department = sys.argv[4]
    
    success = create_admin_user(name, email, password, department)
    
    sys.exit(0 if success else 1)
