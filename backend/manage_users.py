import argparse
import sys
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.database import SessionLocal, engine
from app.models import UserRole

def list_users():
    """List all users in the system"""
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        if not users:
            print("No users found in the database.")
            return
        
        print(f"{'ID':<5} {'Name':<20} {'Email':<30} {'Role':<15} {'Department':<20} {'Admin':<5}")
        print("-" * 95)
        for user in users:
            print(f"{user.id:<5} {user.name:<20} {user.email:<30} {user.role.value:<15} {user.department:<20} {'Yes' if user.is_admin else 'No':<5}")
    finally:
        db.close()

def create_user(name, email, password, department, role, is_admin=False):
    """Create a new user"""
    db = SessionLocal()
    try:
        # Check if email already exists
        existing_user = crud.get_user_by_email(db, email=email)
        if existing_user:
            print(f"Error: User with email {email} already exists.")
            return False
        
        # Create user
        user_data = schemas.UserCreate(
            name=name,
            email=email,
            password=password,
            department=department,
            role=role,
            is_admin=is_admin
        )
        
        user = crud.create_user(db=db, user=user_data)
        print(f"User created successfully: {user.name} ({user.email})")
        return True
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return False
    finally:
        db.close()

def update_user(user_id, name=None, email=None, password=None, department=None, role=None, is_admin=None, is_active=None):
    """Update an existing user"""
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = crud.get_user(db, user_id=user_id)
        if not existing_user:
            print(f"Error: User with ID {user_id} not found.")
            return False
        
        # Create update data
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if email is not None:
            update_data["email"] = email
        if password is not None:
            update_data["password"] = password
        if department is not None:
            update_data["department"] = department
        if role is not None:
            update_data["role"] = role
        if is_admin is not None:
            update_data["is_admin"] = is_admin
        if is_active is not None:
            update_data["is_active"] = is_active
        
        user_update = schemas.UserUpdate(**update_data)
        updated_user = crud.update_user(db=db, user_id=user_id, user_update=user_update)
        print(f"User updated successfully: {updated_user.name} ({updated_user.email})")
        return True
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return False
    finally:
        db.close()

def deactivate_user(user_id):
    """Deactivate a user (soft delete)"""
    return update_user(user_id, is_active=False)

def activate_user(user_id):
    """Activate a user"""
    return update_user(user_id, is_active=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Manage users for the Travel Request Management System")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List users command
    list_parser = subparsers.add_parser("list", help="List all users")
    
    # Create user command
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--name", required=True, help="User's full name")
    create_parser.add_argument("--email", required=True, help="User's email address")
    create_parser.add_argument("--password", required=True, help="User's password")
    create_parser.add_argument("--department", required=True, help="User's department")
    create_parser.add_argument("--role", required=True, choices=[r.value for r in UserRole], help="User's role")
    create_parser.add_argument("--admin", action="store_true", help="Set user as admin")
    
    # Update user command
    update_parser = subparsers.add_parser("update", help="Update an existing user")
    update_parser.add_argument("--id", required=True, type=int, help="User ID")
    update_parser.add_argument("--name", help="User's full name")
    update_parser.add_argument("--email", help="User's email address")
    update_parser.add_argument("--password", help="User's password")
    update_parser.add_argument("--department", help="User's department")
    update_parser.add_argument("--role", choices=[r.value for r in UserRole], help="User's role")
    update_parser.add_argument("--admin", action="store_true", help="Set user as admin")
    update_parser.add_argument("--no-admin", action="store_true", help="Remove admin status")
    
    # Deactivate user command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a user")
    deactivate_parser.add_argument("--id", required=True, type=int, help="User ID")
    
    # Activate user command
    activate_parser = subparsers.add_parser("activate", help="Activate a user")
    activate_parser.add_argument("--id", required=True, type=int, help="User ID")
    
    return parser.parse_args()

if __name__ == "__main__":
    # Create database tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    
    args = parse_args()
    
    if args.command == "list":
        list_users()
    
    elif args.command == "create":
        role_enum = UserRole(args.role)
        success = create_user(
            name=args.name,
            email=args.email,
            password=args.password,
            department=args.department,
            role=role_enum,
            is_admin=args.admin
        )
        sys.exit(0 if success else 1)
    
    elif args.command == "update":
        # Handle admin flag
        is_admin = None
        if args.admin:
            is_admin = True
        elif args.no_admin:
            is_admin = False
        
        # Convert role string to enum if provided
        role_enum = None
        if args.role:
            role_enum = UserRole(args.role)
        
        success = update_user(
            user_id=args.id,
            name=args.name,
            email=args.email,
            password=args.password,
            department=args.department,
            role=role_enum,
            is_admin=is_admin
        )
        sys.exit(0 if success else 1)
    
    elif args.command == "deactivate":
        success = deactivate_user(args.id)
        sys.exit(0 if success else 1)
    
    elif args.command == "activate":
        success = activate_user(args.id)
        sys.exit(0 if success else 1)
    
    else:
        print("Error: No command specified. Use --help for usage information.")
        sys.exit(1)
