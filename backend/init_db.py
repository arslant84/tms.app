import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import UserRole

User = get_user_model()

def create_superuser():
    """Create a superuser if one doesn't exist"""
    if not User.objects.filter(is_superuser=True).exists():
        print("Creating superuser...")
        User.objects.create_superuser(
            email='admin@example.com',
            password='admin123',
            name='Admin User',
            role=UserRole.ADMIN,
            department='Administration',
            is_admin=True
        )
        print("Superuser created successfully!")
    else:
        print("Superuser already exists.")

def create_test_users():
    """Create test users with different roles"""
    test_users = [
        {
            'email': 'employee@example.com',
            'password': 'employee123',
            'name': 'Employee User',
            'role': UserRole.EMPLOYEE,
            'department': 'IT',
            'is_admin': False
        },
        {
            'email': 'focal@example.com',
            'password': 'focal123',
            'name': 'Focal User',
            'role': UserRole.FOCAL,
            'department': 'Finance',
            'is_admin': False
        },
        {
            'email': 'hod@example.com',
            'password': 'hod123',
            'name': 'HOD User',
            'role': UserRole.HOD,
            'department': 'HR',
            'is_admin': False
        },
        {
            'email': 'ticketing@example.com',
            'password': 'ticketing123',
            'name': 'Ticketing Clerk',
            'role': UserRole.TICKETING_CLERK,
            'department': 'Travel',
            'is_admin': False
        }
    ]
    
    for user_data in test_users:
        email = user_data['email']
        if not User.objects.filter(email=email).exists():
            print(f"Creating user: {email}...")
            User.objects.create_user(**user_data)
            print(f"User {email} created successfully!")
        else:
            print(f"User {email} already exists.")

if __name__ == "__main__":
    print("Initializing database...")
    create_superuser()
    create_test_users()
    print("Database initialization completed!")
