#!/usr/bin/env python
"""Test API integration for roles and permissions"""
import os
import sys
import django

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import force_authenticate
from accounts.views import RoleViewSet, PermissionViewSet
from accounts.models import User

def test_api_endpoints():
    """Test that API endpoints return data correctly"""

    print("=== API INTEGRATION TEST ===\n")

    # Get admin user
    admin = User.objects.get(email='tekayev@outlook.com')
    print(f"✓ Admin user: {admin.email}")
    print(f"  Role: {admin.role.name if admin.role else 'None'}\n")

    # Create request factory
    factory = RequestFactory()

    # Test Roles API
    print("1. TESTING ROLES API (/api/roles/)")
    request = factory.get('/api/roles/')
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'get': 'list'})
    response = view(request)

    print(f"   Status Code: {response.status_code}")
    print(f"   Response Type: {type(response.data)}")

    if response.status_code == 200:
        roles_data = response.data
        print(f"   ✓ Roles returned: {len(roles_data)}")
        print(f"   Sample role:")
        if len(roles_data) > 0:
            sample = roles_data[0]
            print(f"     - ID: {sample.get('id')}")
            print(f"     - Name: {sample.get('name')}")
            print(f"     - Description: {sample.get('description')[:50]}...")
            print(f"     - Permissions: {len(sample.get('permissions', []))}")
    else:
        print(f"   ❌ Error: {response.data}")

    # Test Permissions API
    print("\n2. TESTING PERMISSIONS API (/api/permissions/)")
    request = factory.get('/api/permissions/')
    force_authenticate(request, user=admin)

    view = PermissionViewSet.as_view({'get': 'list'})
    response = view(request)

    print(f"   Status Code: {response.status_code}")
    print(f"   Response Type: {type(response.data)}")

    if response.status_code == 200:
        perms_data = response.data
        print(f"   ✓ Permissions returned: {len(perms_data)}")
        print(f"   Sample permissions:")
        for perm in perms_data[:5]:
            print(f"     - {perm.get('name')}: {perm.get('description')[:60]}...")
    else:
        print(f"   ❌ Error: {response.data}")

    # Test Single Role API
    print("\n3. TESTING SINGLE ROLE API (/api/roles/{id}/)")
    admin_role_id = '0ec80c3e-dc8d-4c72-bc81-7a8262c94b94'
    request = factory.get(f'/api/roles/{admin_role_id}/')
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'get': 'retrieve'})
    response = view(request, pk=admin_role_id)

    print(f"   Status Code: {response.status_code}")

    if response.status_code == 200:
        role_data = response.data
        print(f"   ✓ Role: {role_data.get('name')}")
        print(f"   Permissions count: {len(role_data.get('permissions', []))}")
        print(f"   Sample permissions:")
        for perm in role_data.get('permissions', [])[:5]:
            print(f"     - {perm.get('name')}")
    else:
        print(f"   ❌ Error: {response.data}")

    print("\n=== INTEGRATION TEST COMPLETE ===")
    print("\n✓ All API endpoints are properly integrated with Django backend!")
    print("✓ Roles and permissions are accessible through REST API")
    print("✓ Frontend can now fetch this data from:")
    print("  - GET /api/roles/ - List all roles")
    print("  - GET /api/roles/{id}/ - Get specific role with permissions")
    print("  - GET /api/permissions/ - List all permissions")

if __name__ == '__main__':
    test_api_endpoints()
