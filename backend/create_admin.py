import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from accounts.models import User, Role

# Create admin user
email = 'admin@tms.com'
password = 'admin123'
name = 'System Administrator'

# Check if user already exists
if User.objects.filter(email=email).exists():
    print(f"User with email {email} already exists!")
    user = User.objects.get(email=email)
    print(f"User details: {user.name} ({user.email})")
    print("Updating password...")
    user.set_password(password)
    user.save()
    print("Password updated successfully!")
else:
    # Create the user
    user = User.objects.create_superuser(
        email=email,
        password=password,
        name=name,
        department='IT',
        staff_id='ADMIN001'
    )
    print(f"Admin user created successfully!")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"Name: {name}")
    print(f"Role: {user.role.name if user.role else 'No role assigned'}")
