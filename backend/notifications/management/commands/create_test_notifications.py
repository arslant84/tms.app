"""
Management command to create test notifications for users
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import UserNotification, NotificationEventType
from accounts.models import User


class Command(BaseCommand):
    help = 'Create test notifications for users to demonstrate the notification system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Email of the user to create notifications for (default: all users)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of notifications to create per user (default: 5)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing notifications before creating new ones',
        )

    def handle(self, *args, **options):
        user_email = options.get('user')
        count = options.get('count')
        clear = options.get('clear')

        # Get users
        if user_email:
            users = User.objects.filter(email=user_email)
            if not users.exists():
                self.stdout.write(self.style.ERROR(f'User with email {user_email} not found'))
                return
        else:
            users = User.objects.filter(is_active=True)

        if not users.exists():
            self.stdout.write(self.style.ERROR('No users found'))
            return

        # Get or create event type
        event_type, _ = NotificationEventType.objects.get_or_create(
            name='WORKFLOW_STARTED',
            defaults={
                'description': 'Workflow started',
                'category': 'approval',
                'module': 'workflows',
                'is_active': True
            }
        )

        # Clear existing notifications if requested
        if clear:
            deleted_count = UserNotification.objects.filter(user__in=users).delete()[0]
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing notifications'))

        # Get some real IDs from the database to avoid 404 errors
        from trf.models import TravelRequest
        from visa.models import VisaApplication
        from transport.models import TransportRequest
        from expenses.models import ExpenseClaim

        # Get first available ID or use placeholder
        trf_id = TravelRequest.objects.values_list('id', flat=True).first() or 'demo'
        visa_id = VisaApplication.objects.values_list('id', flat=True).first() or 'demo'
        transport_id = TransportRequest.objects.values_list('id', flat=True).first() or 'demo'
        expense_id = ExpenseClaim.objects.values_list('id', flat=True).first() or 'demo'

        # Notification templates
        notification_templates = [
            {
                'title': '📝 Travel Request Submitted',
                'message': 'Your travel request #TSR-2025004 has been submitted successfully and is pending approval.',
                'priority': 'normal',
                'action_url': f'/trf/{trf_id}',
                'action_text': 'View Request'
            },
            {
                'title': '⏰ Approval Required',
                'message': 'You have a new travel request awaiting your approval from {name}.',
                'priority': 'high',
                'action_url': '/approvals',
                'action_text': 'Review Now'
            },
            {
                'title': '✅ Request Approved',
                'message': 'Your expense claim #EXP-2025009 has been approved successfully.',
                'priority': 'normal',
                'action_url': f'/expenses/{expense_id}',
                'action_text': 'View Details'
            },
            {
                'title': '🚨 Urgent: SLA Breach Warning',
                'message': 'Transport request #TR-2025018 is approaching SLA deadline (2 hours remaining).',
                'priority': 'urgent',
                'action_url': f'/transport/{transport_id}',
                'action_text': 'Take Action'
            },
            {
                'title': '✈️ Visa Application Update',
                'message': 'Your visa application has been processed and is ready for collection.',
                'priority': 'normal',
                'action_url': f'/visa/{visa_id}',
                'action_text': 'View Status'
            },
            {
                'title': '🏨 Accommodation Confirmed',
                'message': 'Your accommodation booking #ACC-2025042 has been confirmed.',
                'priority': 'normal',
                'action_url': '/dashboard',  # Safe fallback
                'action_text': 'View Booking'
            },
            {
                'title': '❌ Request Rejected',
                'message': 'Your request has been rejected. Please review the feedback and resubmit.',
                'priority': 'high',
                'action_url': f'/trf/{trf_id}',
                'action_text': 'View Feedback'
            },
            {
                'title': '💬 New Comment Added',
                'message': 'A new comment has been added to your request by {name}.',
                'priority': 'low',
                'action_url': f'/trf/{trf_id}',
                'action_text': 'View Comment'
            },
        ]

        total_created = 0

        for user in users:
            user_created = 0

            for i in range(min(count, len(notification_templates))):
                template = notification_templates[i % len(notification_templates)]

                # Replace placeholders (only {name}, URLs are already set)
                title = template['title']
                message = template['message'].replace('{name}', user.name or 'Admin')
                action_url = template['action_url']

                # Create notification
                notification = UserNotification.objects.create(
                    user=user,
                    event_type=event_type,
                    title=title,
                    message=message,
                    priority=template['priority'],
                    action_url=action_url,
                    action_text=template['action_text'],
                    is_read=(i >= 2),  # First 2 are unread
                    sent_via_email=False,
                    created_at=timezone.now() - timedelta(hours=i)
                )
                user_created += 1

            total_created += user_created
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created {user_created} notifications for {user.email}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Total: Created {total_created} test notifications for {users.count()} user(s)')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Database stats: {UserNotification.objects.count()} total, {UserNotification.objects.filter(is_read=False).count()} unread')
        )
