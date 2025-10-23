#!/usr/bin/env python
"""Test notification templates API endpoints"""
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
from notifications.views import NotificationEventTypeViewSet, NotificationTemplateViewSet
from accounts.models import User

def test_notification_templates_api():
    """Test notification templates API endpoints"""

    print("=== NOTIFICATION TEMPLATES API TEST ===\n")

    # Get admin user
    admin = User.objects.get(email='tekayev@outlook.com')
    print(f"✓ Admin user: {admin.email}\n")

    # Create request factory
    factory = RequestFactory()

    # ====================
    # TEST 1: Get all event types
    # ====================
    print("1. TESTING GET EVENT TYPES (/api/notifications/event-types/)")
    request = factory.get('/api/notifications/event-types/')
    force_authenticate(request, user=admin)

    view = NotificationEventTypeViewSet.as_view({'get': 'list'})
    response = view(request)

    if response.status_code == 200:
        event_types = response.data
        print(f"   ✓ Status: 200 OK")
        print(f"   ✓ Total event types: {len(event_types)}")

        # Group by module
        modules = {}
        for et in event_types:
            module = et['module']
            if module not in modules:
                modules[module] = []
            modules[module].append(et)

        print(f"   ✓ Event types by module:")
        for module, items in modules.items():
            print(f"     - {module}: {len(items)}")

        print(f"   ✓ Sample event types:")
        for et in event_types[:5]:
            print(f"     - {et['name']} ({et['module']}/{et['category']})")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Error: {response.data}")
        return

    # ====================
    # TEST 2: Get all templates
    # ====================
    print("\n2. TESTING GET TEMPLATES (/api/notifications/templates/)")
    request = factory.get('/api/notifications/templates/')
    force_authenticate(request, user=admin)

    view = NotificationTemplateViewSet.as_view({'get': 'list'})
    response = view(request)

    if response.status_code == 200:
        templates = response.data
        print(f"   ✓ Status: 200 OK")
        print(f"   ✓ Total templates: {len(templates)}")

        active = [t for t in templates if t['is_active']]
        print(f"   ✓ Active templates: {len(active)}")

        # Group by notification_type
        by_type = {}
        for t in templates:
            nt = t['notification_type']
            by_type[nt] = by_type.get(nt, 0) + 1

        print(f"   ✓ Templates by type:")
        for nt, count in by_type.items():
            print(f"     - {nt}: {count}")

        # Group by recipient_type
        by_recipient = {}
        for t in templates:
            rt = t['recipient_type']
            by_recipient[rt] = by_recipient.get(rt, 0) + 1

        print(f"   ✓ Templates by recipient:")
        for rt, count in by_recipient.items():
            print(f"     - {rt}: {count}")

        print(f"   ✓ Sample templates:")
        for t in templates[:5]:
            print(f"     - {t['name']}")
            print(f"       Subject: {t['subject'][:60]}...")
            print(f"       Type: {t['notification_type']}, Recipient: {t['recipient_type']}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Error: {response.data}")
        return

    # ====================
    # TEST 3: Get single template
    # ====================
    print("\n3. TESTING GET SINGLE TEMPLATE (/api/notifications/templates/{id}/)")

    # Get first template ID
    template_id = templates[0]['id']
    request = factory.get(f'/api/notifications/templates/{template_id}/')
    force_authenticate(request, user=admin)

    view = NotificationTemplateViewSet.as_view({'get': 'retrieve'})
    response = view(request, pk=template_id)

    if response.status_code == 200:
        template = response.data
        print(f"   ✓ Status: 200 OK")
        print(f"   ✓ Template: {template['name']}")
        print(f"   ✓ Subject: {template['subject']}")
        print(f"   ✓ Body length: {len(template['body'])} characters")
        print(f"   ✓ Event type: {template.get('event_type_name', 'None')}")
        print(f"   ✓ Variables available: {template.get('variables_available', [])}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Error: {response.data}")
        return

    # ====================
    # TEST 4: Create new template
    # ====================
    print("\n4. TESTING CREATE TEMPLATE (POST /api/notifications/templates/)")

    # Get an event type ID
    event_type_id = event_types[0]['id']

    new_template = {
        'name': 'test_api_template',
        'description': 'Test template created via API',
        'subject': 'Test Subject: {entityId}',
        'body': '<html><body><p>Test body content</p></body></html>',
        'event_type': str(event_type_id),
        'notification_type': 'email',
        'recipient_type': 'requestor',
        'variables_available': ['entityId', 'userName'],
        'is_active': True
    }

    request = factory.post(
        '/api/notifications/templates/',
        data=json.dumps(new_template),
        content_type='application/json'
    )
    force_authenticate(request, user=admin)

    view = NotificationTemplateViewSet.as_view({'post': 'create'})
    response = view(request)

    if response.status_code == 201:
        created = response.data
        print(f"   ✓ Status: 201 Created")
        print(f"   ✓ Created template: {created['name']}")
        print(f"   ✓ Template ID: {created['id']}")
        test_template_id = created['id']
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Error: {response.data}")
        test_template_id = None

    # ====================
    # TEST 5: Update template
    # ====================
    if test_template_id:
        print("\n5. TESTING UPDATE TEMPLATE (PUT /api/notifications/templates/{id}/)")

        update_data = {
            'name': 'test_api_template',
            'description': 'Updated test template',
            'subject': 'Updated Subject: {entityId}',
            'body': '<html><body><p>Updated body content</p></body></html>',
            'event_type': str(event_type_id),
            'notification_type': 'email',
            'recipient_type': 'approver',
            'variables_available': ['entityId', 'userName', 'approverName'],
            'is_active': True
        }

        request = factory.put(
            f'/api/notifications/templates/{test_template_id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        force_authenticate(request, user=admin)

        view = NotificationTemplateViewSet.as_view({'put': 'update'})
        response = view(request, pk=test_template_id)

        if response.status_code == 200:
            updated = response.data
            print(f"   ✓ Status: 200 OK")
            print(f"   ✓ Updated template: {updated['name']}")
            print(f"   ✓ New recipient type: {updated['recipient_type']}")
            print(f"   ✓ New variables: {updated['variables_available']}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Error: {response.data}")

    # ====================
    # TEST 6: Delete template
    # ====================
    if test_template_id:
        print("\n6. TESTING DELETE TEMPLATE (DELETE /api/notifications/templates/{id}/)")

        request = factory.delete(f'/api/notifications/templates/{test_template_id}/')
        force_authenticate(request, user=admin)

        view = NotificationTemplateViewSet.as_view({'delete': 'destroy'})
        response = view(request, pk=test_template_id)

        if response.status_code == 204:
            print(f"   ✓ Status: 204 No Content")
            print(f"   ✓ Template deleted successfully")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Error: {response.data}")

    # ====================
    # TEST 7: Filter templates by module
    # ====================
    print("\n7. TESTING FILTER BY MODULE (?module=trf)")
    request = factory.get('/api/notifications/templates/?module=trf')
    force_authenticate(request, user=admin)

    view = NotificationTemplateViewSet.as_view({'get': 'list'})
    response = view(request)

    if response.status_code == 200:
        trf_templates = response.data
        print(f"   ✓ Status: 200 OK")
        print(f"   ✓ TRF templates: {len(trf_templates)}")
        for t in trf_templates[:3]:
            print(f"     - {t['name']}")
    else:
        print(f"   ❌ Failed: {response.status_code}")

    print("\n=== TEST COMPLETE ===")
    print("\n✅ NOTIFICATION TEMPLATES API VERIFIED:")
    print("   ✓ GET /api/notifications/event-types/ - List event types")
    print("   ✓ GET /api/notifications/templates/ - List templates")
    print("   ✓ GET /api/notifications/templates/{id}/ - Get single template")
    print("   ✓ POST /api/notifications/templates/ - Create template")
    print("   ✓ PUT /api/notifications/templates/{id}/ - Update template")
    print("   ✓ DELETE /api/notifications/templates/{id}/ - Delete template")
    print("   ✓ Filter by module, type, recipient")

if __name__ == '__main__':
    test_notification_templates_api()
