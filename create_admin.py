#!/usr/bin/env python
"""Create admin user script"""
import os
import sys
import django

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User, Role

def create_admin_user():
    """Create admin user with System Administrator role"""

    # Get System Administrator role
    try:
        admin_role = Role.objects.get(id='0ec80c3e-dc8d-4c72-bc81-7a8262c94b94')
        print(f"✓ Found role: {admin_role.name}")
    except Role.DoesNotExist:
        print("❌ System Administrator role not found!")
        return

    # Check if user already exists
    if User.objects.filter(email='tekayev@outlook.com').exists():
        print("❌ User with email 'tekayev@outlook.com' already exists!")
        user = User.objects.get(email='tekayev@outlook.com')
        print(f"  Updating password for existing user...")
        user.set_password('admin123')
        user.role = admin_role
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.status = 'Active'
        user.save()
        print(f"✓ Updated user: {user.email}")
    else:
        # Create new superuser
        user = User.objects.create_superuser(
            email='tekayev@outlook.com',
            password='admin123',
            name='Administrator',
            role=admin_role,
            department='IT',
            staff_id='ADMIN001',
            phone='+993000000',
            is_admin=True,
            is_active=True,
            status='Active'
        )
        print(f"✓ Created superuser: {user.email}")

    print(f"  Name: {user.name}")
    print(f"  Role: {user.role.name if user.role else 'None'}")
    print(f"  Email: {user.email}")
    print(f"  Password: admin123")
    print(f"  Status: {user.status}")
    print(f"\n✓ You can now login with:")
    print(f"  Email: tekayev@outlook.com")
    print(f"  Password: admin123")

if __name__ == '__main__':
    create_admin_user()
