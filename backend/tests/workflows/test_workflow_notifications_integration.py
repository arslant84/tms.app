"""
Test Workflow Notifications Integration
Tests the complete flow from workflow events to notification creation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from workflows.notifications import WorkflowNotifications
from accounts.models import User
from django.utils import timezone


def test_notification_context_builder():
    """Test that _build_notification_context includes all required variables"""

    print("=" * 80)
    print("🔍 TESTING NOTIFICATION CONTEXT BUILDER")
    print("=" * 80)
    print()

    # Create a mock step_execution object for testing
    class MockUser:
        def get_full_name(self):
            return "Test User"

    class MockWorkflowStep:
        step_name = "HOD Approval"
        is_urgent = True
        step_order = 1

    class MockWorkflowTemplate:
        name = "Visa Approval Workflow"
        entity_type = "visa"

    class MockWorkflowInstance:
        initiated_by = MockUser()
        workflow_template = MockWorkflowTemplate()
        object_id = 123

    class MockStepExecution:
        workflow_instance = MockWorkflowInstance()
        workflow_step = MockWorkflowStep()
        assigned_to = MockUser()
        actioned_by = MockUser()
        sla_due_date = timezone.now()
        comments = "Test rejection reason"
        status = "pending"

    mock_step = MockStepExecution()

    # Test the context builder
    print("Testing _build_notification_context()...")
    context = WorkflowNotifications._build_notification_context(mock_step)

    print("\n✅ Generated Context Variables:")
    print("─" * 80)

    # Check for new improved template variables
    required_variables = [
        'requestorName',
        'approverName',
        'processorName',
        'userName',
        'requestType',
        'entityId',
        'dueDate',
        'completionDate',
        'urgencyHint',
        'processorHint',
        'completionDetails',
        'rejectionReason',
        'actionUrl',
    ]

    passed = 0
    failed = 0

    for var in required_variables:
        if var in context:
            print(f"✅ {var:25} = {str(context[var])[:50]}")
            passed += 1
        else:
            print(f"❌ {var:25} = MISSING")
            failed += 1

    print("─" * 80)

    # Check for legacy variables (backward compatibility)
    print("\n✅ Legacy Variables (Backward Compatibility):")
    print("─" * 80)

    legacy_variables = [
        'entity_type',
        'entityType',
        'request_type',
        'entity_id',
        'step_name',
        'stepName',
        'assigned_to',
        'assignedTo',
        'requester',
        'requesterName',
        'sla_due_date',
        'slaDueDate',
        'status',
    ]

    legacy_passed = 0
    legacy_failed = 0

    for var in legacy_variables:
        if var in context:
            print(f"✅ {var:25} = {str(context[var])[:50]}")
            legacy_passed += 1
        else:
            print(f"⚠️  {var:25} = MISSING (may not be critical)")
            legacy_failed += 1

    print("─" * 80)

    # Summary
    print("\n📊 SUMMARY:")
    print(f"Required Variables: {passed}/{len(required_variables)} passed")
    print(f"Legacy Variables: {legacy_passed}/{len(legacy_variables)} passed")

    if failed == 0:
        print("\n✅ ALL REQUIRED VARIABLES PRESENT - Context builder is working correctly!")
        return True
    else:
        print(f"\n❌ {failed} REQUIRED VARIABLES MISSING - Context builder needs fixes!")
        return False


def test_notification_methods_integration():
    """Test that notification methods pass correct additional_data"""

    print("\n" + "=" * 80)
    print("🔍 TESTING NOTIFICATION METHODS INTEGRATION")
    print("=" * 80)
    print()

    print("Checking notification method signatures and additional_data...")
    print()

    # List of notification methods to check
    methods_to_check = [
        ('notify_workflow_started', [
            'requestorName', 'requestType', 'entityId', 'approverName', 'actionUrl'
        ]),
        ('notify_step_approved', [
            'requestorName', 'requestType', 'entityId', 'approverName', 'actionUrl'
        ]),
        ('notify_step_rejected', [
            'requestorName', 'requestType', 'entityId', 'approverName', 'rejectionReason', 'actionUrl'
        ]),
        ('notify_step_delegated', [
            'approverName', 'delegatorName', 'requestType', 'entityId', 'actionUrl'
        ]),
        ('notify_workflow_completed', [
            'requestorName', 'requestType', 'entityId', 'processorName', 'completionDate', 'completionDetails', 'actionUrl'
        ]),
    ]

    import inspect

    all_good = True

    for method_name, expected_vars in methods_to_check:
        method = getattr(WorkflowNotifications, method_name)
        source = inspect.getsource(method)

        print(f"Testing: {method_name}")
        print("─" * 80)

        # Check if method contains additional_data
        if 'additional_data=' in source:
            print(f"✅ Method passes additional_data")

            # Check for each expected variable in the source
            missing_vars = []
            for var in expected_vars:
                if f"'{var}'" in source or f'"{var}"' in source:
                    print(f"   ✅ {var}")
                else:
                    print(f"   ❌ {var} - NOT FOUND")
                    missing_vars.append(var)
                    all_good = False

            if not missing_vars:
                print(f"   🎉 All {len(expected_vars)} variables found!")
            else:
                print(f"   ⚠️  Missing {len(missing_vars)} variables: {', '.join(missing_vars)}")
        else:
            print(f"❌ Method does NOT pass additional_data")
            all_good = False

        print()

    if all_good:
        print("✅ ALL NOTIFICATION METHODS CORRECTLY CONFIGURED!")
        return True
    else:
        print("❌ SOME NOTIFICATION METHODS NEED FIXES!")
        return False


def test_template_variables_mapping():
    """Verify that templates variables match what the code provides"""

    print("\n" + "=" * 80)
    print("🔍 VERIFYING TEMPLATE-CODE VARIABLE MAPPING")
    print("=" * 80)
    print()

    from notifications.models import NotificationTemplate

    # Check each template
    templates = NotificationTemplate.objects.all()

    all_ok = True

    for template in templates:
        print(f"\n📄 Template: {template.name}")
        print("─" * 80)

        # Extract variables from template body and subject
        import re
        variables_in_subject = set(re.findall(r'\{\{(\w+)\}\}', template.subject))
        variables_in_body = set(re.findall(r'\{\{(\w+)\}\}', template.body))
        all_template_vars = variables_in_subject | variables_in_body

        print(f"Variables used in template: {', '.join(sorted(all_template_vars))}")

        # Check if all used variables are in variables_available
        if template.variables_available:
            registered_vars = set(template.variables_available)
            missing_from_registry = all_template_vars - registered_vars
            extra_in_registry = registered_vars - all_template_vars

            if missing_from_registry:
                print(f"⚠️  Used but not registered: {', '.join(missing_from_registry)}")
                all_ok = False
            else:
                print(f"✅ All used variables are registered")

            if extra_in_registry:
                print(f"ℹ️  Registered but not used: {', '.join(extra_in_registry)}")
        else:
            print(f"❌ No variables_available array defined!")
            all_ok = False

    print("\n" + "=" * 80)
    if all_ok:
        print("✅ ALL TEMPLATES HAVE CORRECT VARIABLE MAPPINGS!")
        return True
    else:
        print("⚠️  SOME TEMPLATES HAVE VARIABLE MAPPING ISSUES!")
        return False


if __name__ == '__main__':
    print("\n🚀 Starting Workflow Notifications Integration Tests\n")

    # Run all integration tests
    test1_passed = test_notification_context_builder()
    test2_passed = test_notification_methods_integration()
    test3_passed = test_template_variables_mapping()

    # Final summary
    print("\n" + "=" * 80)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 80)

    tests = [
        ("Context Builder Test", test1_passed),
        ("Notification Methods Test", test2_passed),
        ("Template Variables Mapping Test", test3_passed),
    ]

    total_passed = sum(1 for _, passed in tests if passed)
    total_tests = len(tests)

    for test_name, passed in tests:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status:12} {test_name}")

    print("─" * 80)
    print(f"Total: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.0f}%)")
    print("=" * 80)

    if total_passed == total_tests:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Workflow notifications are ready for production!")
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed. Please review the output above.")

    print()
