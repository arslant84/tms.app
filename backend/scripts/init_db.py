import os
import django
import sys
import secrets
import string

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Role

User = get_user_model()

def generate_password(length=16):
    """Generate a secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))

def create_superuser():
    """Create a superuser if one doesn't exist"""
    if User.objects.filter(is_superuser=True).exists():
        print("Superuser already exists.")
        return

    # Get or create Admin role
    admin_role, _ = Role.objects.get_or_create(
        name='Admin',
        defaults={'description': 'System Administrator'}
    )

    # SECURITY: Use environment variable or generate random password
    email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    password = os.getenv('ADMIN_PASSWORD') or generate_password()

    print("Creating superuser...")
    # SECURITY: Require password change if using generated password
    require_password_change = not os.getenv('ADMIN_PASSWORD')

    User.objects.create_superuser(
        email=email,
        password=password,
        name='Admin User',
        role=admin_role,
        department='Administration',
        is_admin=True,
        password_change_required=require_password_change
    )

    print(f"✅ Superuser created: {email}")
    if require_password_change:
        print(f"⚠️  Generated password: {password}")
        print("⚠️  SAVE THIS PASSWORD - Change it on first login!")

def create_test_users():
    """Create test users with different roles - DEVELOPMENT ONLY"""
    # SECURITY: Only create test users in development
    if os.getenv('DJANGO_ENV') == 'production':
        print("⚠️  Skipping test users in production")
        return

    # Define roles and test users
    roles = {
        'Employee': 'Standard employee role',
        'Focal': 'Focal point role',
        'HOD': 'Head of Department',
        'Ticketing Clerk': 'Ticketing and booking clerk'
    }

    test_users = [
        {'email': 'employee@example.com', 'name': 'Employee User',
         'role_name': 'Employee', 'department': 'IT'},
        {'email': 'focal@example.com', 'name': 'Focal User',
         'role_name': 'Focal', 'department': 'Finance'},
        {'email': 'hod@example.com', 'name': 'HOD User',
         'role_name': 'HOD', 'department': 'HR'},
        {'email': 'ticketing@example.com', 'name': 'Ticketing Clerk',
         'role_name': 'Ticketing Clerk', 'department': 'Travel'}
    ]

    # Create roles
    for role_name, description in roles.items():
        Role.objects.get_or_create(
            name=role_name,
            defaults={'description': description}
        )

    print("\n📝 Test Users (Development Only):")
    for user_data in test_users:
        email = user_data['email']
        if User.objects.filter(email=email).exists():
            print(f"  - {email} (already exists)")
            continue

        # Get role and generate password
        role = Role.objects.get(name=user_data.pop('role_name'))
        password = generate_password()

        User.objects.create_user(
            email=email,
            password=password,
            name=user_data['name'],
            role=role,
            department=user_data['department'],
            is_admin=False,
            password_change_required=True  # SECURITY: Force password change on first login
        )
        print(f"  ✅ {email} | Password: {password} (Change required)")

if __name__ == "__main__":
    print("Initializing database...")
    create_superuser()
    create_test_users()
    print("Database initialization completed!")
