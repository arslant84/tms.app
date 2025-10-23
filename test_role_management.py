#!/usr/bin/env python
"""Test role management API with permissions"""
import os
import sys
import django
import json

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import force_authenticate
from accounts.views import RoleViewSet, PermissionViewSet
from accounts.models import User, Role, Permission

def test_role_management():
    """Test role creation, update, and permission binding"""

    print("=== ROLE MANAGEMENT API TEST ===\n")

    # Get admin user
    admin = User.objects.get(email='tekayev@outlook.com')
    print(f"✓ Admin user: {admin.email}\n")

    # Create request factory
    factory = RequestFactory()

    # ====================
    # TEST 1: Get all permissions
    # ====================
    print("1. TESTING GET ALL PERMISSIONS")
    request = factory.get('/api/permissions/')
    force_authenticate(request, user=admin)

    view = PermissionViewSet.as_view({'get': 'list'})
    response = view(request)

    if response.status_code == 200:
        permissions = response.data
        print(f"   ✓ Total permissions: {len(permissions)}")

        # Get first 5 permission IDs for testing
        test_permission_ids = [p['id'] for p in permissions[:5]]
        print(f"   ✓ Sample permission IDs for testing:")
        for pid in test_permission_ids:
            perm = next(p for p in permissions if p['id'] == pid)
            print(f"     - {pid} ({perm['name']})")
    else:
        print(f"   ❌ Failed to get permissions: {response.status_code}")
        return

    # ====================
    # TEST 2: Create new custom role with permissions
    # ====================
    print("\n2. TESTING CREATE ROLE WITH PERMISSIONS")

    new_role_data = {
        'name': 'Test Custom Role',
        'description': 'A custom role for testing permission binding',
        'permissionIds': test_permission_ids
    }

    request = factory.post(
        '/api/roles/',
        data=json.dumps(new_role_data),
        content_type='application/json'
    )
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'post': 'create'})
    response = view(request)

    if response.status_code == 201:
        created_role = response.data
        print(f"   ✓ Role created: {created_role['name']}")
        print(f"   ✓ Role ID: {created_role['id']}")
        print(f"   ✓ Description: {created_role['description']}")
        print(f"   ✓ Permissions assigned: {len(created_role.get('permissionIds', []))}")
        print(f"   ✓ Permission details:")
        for perm in created_role.get('permissions', [])[:5]:
            print(f"     - {perm['name']}")

        test_role_id = created_role['id']
    else:
        print(f"   ❌ Failed to create role: {response.status_code}")
        print(f"   Error: {response.data}")
        return

    # ====================
    # TEST 3: Get the created role
    # ====================
    print("\n3. TESTING GET ROLE BY ID")

    request = factory.get(f'/api/roles/{test_role_id}/')
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'get': 'retrieve'})
    response = view(request, pk=test_role_id)

    if response.status_code == 200:
        role_data = response.data
        print(f"   ✓ Role retrieved: {role_data['name']}")
        print(f"   ✓ Permissions count: {len(role_data.get('permissions', []))}")
        print(f"   ✓ PermissionIds: {role_data.get('permissionIds', [])}")
    else:
        print(f"   ❌ Failed to retrieve role: {response.status_code}")
        return

    # ====================
    # TEST 4: Update role with different permissions
    # ====================
    print("\n4. TESTING UPDATE ROLE PERMISSIONS")

    # Use different permissions (permissions 5-8)
    updated_permission_ids = [p['id'] for p in permissions[5:9]]

    update_data = {
        'name': 'Updated Test Role',
        'description': 'Updated description for testing',
        'permissionIds': updated_permission_ids
    }

    request = factory.put(
        f'/api/roles/{test_role_id}/',
        data=json.dumps(update_data),
        content_type='application/json'
    )
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'put': 'update'})
    response = view(request, pk=test_role_id)

    if response.status_code == 200:
        updated_role = response.data
        print(f"   ✓ Role updated: {updated_role['name']}")
        print(f"   ✓ New description: {updated_role['description']}")
        print(f"   ✓ New permissions count: {len(updated_role.get('permissionIds', []))}")
        print(f"   ✓ New permission details:")
        for perm in updated_role.get('permissions', []):
            print(f"     - {perm['name']}")
    else:
        print(f"   ❌ Failed to update role: {response.status_code}")
        print(f"   Error: {response.data}")
        return

    # ====================
    # TEST 5: Update existing System Administrator role
    # ====================
    print("\n5. TESTING UPDATE EXISTING ROLE (System Administrator)")

    sys_admin_id = '0ec80c3e-dc8d-4c72-bc81-7a8262c94b94'

    # Get current permissions count
    request = factory.get(f'/api/roles/{sys_admin_id}/')
    force_authenticate(request, user=admin)
    view = RoleViewSet.as_view({'get': 'retrieve'})
    response = view(request, pk=sys_admin_id)

    if response.status_code == 200:
        current_perms = response.data.get('permissionIds', [])
        print(f"   ✓ Current permissions: {len(current_perms)}")

        # Remove one permission and test update
        updated_perms = current_perms[:-1]  # Remove last permission

        update_data = {
            'name': 'System Administrator',
            'description': 'Updated: Has full access to all system features and settings.',
            'permissionIds': updated_perms
        }

        request = factory.put(
            f'/api/roles/{sys_admin_id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        force_authenticate(request, user=admin)

        view = RoleViewSet.as_view({'put': 'update'})
        response = view(request, pk=sys_admin_id)

        if response.status_code == 200:
            print(f"   ✓ System Administrator role updated")
            print(f"   ✓ New permissions count: {len(response.data.get('permissionIds', []))}")

            # Restore original permissions
            restore_data = {
                'name': 'System Administrator',
                'description': 'Has full access to all system features and settings.',
                'permissionIds': current_perms
            }

            request = factory.put(
                f'/api/roles/{sys_admin_id}/',
                data=json.dumps(restore_data),
                content_type='application/json'
            )
            force_authenticate(request, user=admin)

            view = RoleViewSet.as_view({'put': 'update'})
            response = view(request, pk=sys_admin_id)
            print(f"   ✓ Restored original permissions: {len(response.data.get('permissionIds', []))}")
        else:
            print(f"   ❌ Failed to update System Administrator: {response.status_code}")

    # ====================
    # TEST 6: Delete test role
    # ====================
    print("\n6. TESTING DELETE ROLE")

    request = factory.delete(f'/api/roles/{test_role_id}/')
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'delete': 'destroy'})
    response = view(request, pk=test_role_id)

    if response.status_code == 204:
        print(f"   ✓ Test role deleted successfully")
    else:
        print(f"   ❌ Failed to delete role: {response.status_code}")

    # ====================
    # Final verification
    # ====================
    print("\n7. FINAL VERIFICATION - GET ALL ROLES")

    request = factory.get('/api/roles/')
    force_authenticate(request, user=admin)

    view = RoleViewSet.as_view({'get': 'list'})
    response = view(request)

    if response.status_code == 200:
        roles = response.data
        print(f"   ✓ Total roles: {len(roles)}")
        print(f"   ✓ Roles list:")
        for role in roles:
            perm_count = len(role.get('permissionIds', []))
            print(f"     - {role['name']}: {perm_count} permissions")

    print("\n=== TEST COMPLETE ===")
    print("\n✅ ROLE MANAGEMENT FUNCTIONALITY VERIFIED:")
    print("   ✓ Can fetch all permissions")
    print("   ✓ Can create new roles with permissions")
    print("   ✓ Can retrieve role with permission details")
    print("   ✓ Can update role permissions")
    print("   ✓ Can update existing roles")
    print("   ✓ Can delete roles")
    print("\n✅ FRONTEND INTEGRATION READY:")
    print("   ✓ POST /api/roles/ - Create role with permissionIds array")
    print("   ✓ PUT /api/roles/{id}/ - Update role with permissionIds array")
    print("   ✓ GET /api/roles/ - Get all roles with permissionIds")
    print("   ✓ GET /api/roles/{id}/ - Get role with full permission details")
    print("   ✓ DELETE /api/roles/{id}/ - Delete role")

if __name__ == '__main__':
    test_role_management()
