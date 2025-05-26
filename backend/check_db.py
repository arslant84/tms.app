"""
Script to check if admin user exists in the database
"""
from app.database import SessionLocal
from app.models import User

def check_admin_user():
    """Check if admin user exists in the database."""
    db = SessionLocal()
    try:
        admin_users = db.query(User).filter(User.email == "admin@tms.com").all()
        print(f"Found {len(admin_users)} admin users:")
        for user in admin_users:
            print(f"ID: {user.id}, Email: {user.email}, Name: {user.name}, Role: {user.role}, Is Admin: {user.is_admin}")
        
        # Check all users in the database
        all_users = db.query(User).all()
        print(f"\nTotal users in database: {len(all_users)}")
        for user in all_users:
            print(f"ID: {user.id}, Email: {user.email}, Name: {user.name}, Role: {user.role}, Is Admin: {user.is_admin}")
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_user()
