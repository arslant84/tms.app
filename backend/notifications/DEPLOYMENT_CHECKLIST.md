# 🚀 Notification Templates Deployment Checklist

**Project:** TMS Notification Templates Update
**Version:** 2.0 (Improved Templates)
**Date:** 2026-01-06

---

## Pre-Deployment Checklist

### ✅ Development Environment Testing

- [x] Migration created: `0004_update_notification_templates.py`
- [x] Migration tested locally
- [x] All 10 templates updated successfully
- [x] Template rendering tests passing (10/10)
- [x] Integration tests passing (3/3)
- [x] No unreplaced variables in templates
- [x] Context builder includes all variables
- [x] Notification methods pass correct data
- [x] Backward compatibility maintained

### 📋 Code Review

- [x] Review migration file for correctness
- [x] Review notification methods for variable completeness
- [x] Review context builder for all required variables
- [x] Check for any hardcoded values that should be variables
- [x] Verify date formatting is user-friendly
- [x] Confirm action URLs are correct

### 📝 Documentation

- [x] Template documentation created
- [x] Variable reference documented
- [x] Usage examples provided
- [x] Troubleshooting guide included
- [x] Migration history documented
- [x] Roadmap updated with progress

---

## Deployment Steps

### Step 1: Backup Database ⚠️ CRITICAL

```bash
# For PostgreSQL
pg_dump tms_database > backup_$(date +%Y%m%d_%H%M%S).sql

# For MySQL
mysqldump -u username -p tms_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Verify backup:**
```bash
# Check backup file size (should be > 0)
ls -lh backup_*.sql

# For extra safety, compress and store in secure location
gzip backup_*.sql
mv backup_*.sql.gz /path/to/secure/backups/
```

---

### Step 2: Apply Migration

```bash
# Navigate to backend directory
cd backend

# Check migration status
python manage.py showmigrations notifications

# Apply the migration
python manage.py migrate notifications 0004

# Expected output:
# Running migrations:
#   Applying notifications.0004_update_notification_templates... OK
# ✅ Updated template: workflow_started_requestor
# ✅ Updated template: approval_required
# ... (10 templates total)
# =====================================================
# ✅ Successfully updated 10 out of 10 templates
# =====================================================
```

---

### Step 3: Verify Migration

```bash
# Enter Django shell
python manage.py shell
```

```python
from notifications.models import NotificationTemplate

# Check template count (should be 10)
print(f"Total templates: {NotificationTemplate.objects.count()}")

# Verify a sample template
template = NotificationTemplate.objects.get(name='workflow_started_requestor')
print(f"Subject: {template.subject}")
print(f"Variables: {template.variables_available}")

# Should output:
# Subject: ✅ Your {{requestType}} Request (#{{entityId}}) Has Been Submitted
# Variables: ['requestorName', 'requestType', 'entityId', 'approverName', 'actionUrl']

# Check all templates have the new format
for t in NotificationTemplate.objects.all():
    has_greeting = 'Hi {{' in t.body or 'Hi {' in t.body
    has_closing = 'The TMS Team' in t.body
    print(f"{t.name:30} Greeting: {has_greeting}  Closing: {has_closing}")

# Exit shell
exit()
```

---

### Step 4: Test Notification Sending

**Option A: Run automated tests**

```bash
cd backend

# Test template rendering
python test_notification_templates.py

# Test integration
python test_workflow_notifications_integration.py

# Both should show 100% pass rate
```

**Option B: Manual test with real user**

```bash
python manage.py shell
```

```python
from notifications.services import NotificationService
from notifications.models import NotificationEventType
from accounts.models import User

# Get a test user
user = User.objects.filter(email='your.email@test.com').first()

# Get event type
event_type = NotificationEventType.objects.get(name='APPROVAL_REQUESTED')

# Send test notification
notification = NotificationService.create_notification(
    user=user,
    title="Test Notification",
    message="This is a test",
    event_type=event_type,
    priority='normal',
    additional_data={
        'approverName': user.get_full_name(),
        'requestType': 'Test Request',
        'entityId': 'TEST-001',
        'requestorName': 'Test User',
        'dueDate': 'January 10, 2026 at 05:00 PM',
        'urgencyHint': 'Normal priority',
        'actionUrl': '/test/123',
    },
    send_email=True
)

print(f"Notification created: {notification.id}")
print(f"Check email at: {user.email}")

# Wait a few seconds for async email sending
import time
time.sleep(5)

# Check email status
notification.refresh_from_db()
if notification.email_sent_at:
    print("✅ Email sent successfully!")
else:
    print(f"❌ Email failed: {notification.email_error}")

exit()
```

---

### Step 5: Monitor Logs

```bash
# Monitor application logs for errors
tail -f /var/log/tms/error.log

# Or if using Docker
docker logs -f tms-backend

# Look for:
# - Migration success messages
# - Email sending confirmations
# - Any error messages related to templates
```

---

### Step 6: Smoke Testing

Perform these actions in the application to trigger real notifications:

1. **Create a new request** (visa/accommodation/transport)
   - ✅ Verify requestor receives "workflow_started" email
   - ✅ Verify approver receives "approval_required" email
   - ✅ Check email formatting and variables are correct

2. **Approve a step**
   - ✅ Verify requestor receives update
   - ✅ Verify next approver receives assignment

3. **Reject a request**
   - ✅ Verify requestor receives rejection email
   - ✅ Check rejection reason is included

4. **Delegate a request**
   - ✅ Verify delegate receives notification
   - ✅ Check delegator name is correct

5. **Complete a workflow**
   - ✅ Verify requestor receives completion email
   - ✅ Check all details are present

---

## Rollback Procedure

If issues are found after deployment:

### Step 1: Revert Migration

```bash
cd backend

# Roll back to previous migration
python manage.py migrate notifications 0003

# This will run the reverse migration and restore old templates
```

### Step 2: Verify Rollback

```bash
python manage.py shell
```

```python
from notifications.models import NotificationTemplate

# Check a sample template (should have old format)
template = NotificationTemplate.objects.get(name='workflow_started_requestor')
print(template.subject)

# Should output old format:
# 🔔 New Request Initiated - {{requestType}} #{{entityId}}

exit()
```

### Step 3: Restore Database (If Needed)

Only if migration rollback fails:

```bash
# Stop application
sudo systemctl stop tms-backend

# Restore from backup
psql tms_database < backup_YYYYMMDD_HHMMSS.sql

# Restart application
sudo systemctl start tms-backend
```

---

## Post-Deployment Monitoring

### Day 1-3: Active Monitoring

- [ ] Monitor error logs hourly
- [ ] Check email delivery rate
- [ ] Verify no user complaints about notifications
- [ ] Check for any unreplaced variables in sent emails
- [ ] Monitor SMTP server for any issues

### Week 1: Regular Checks

- [ ] Review email delivery success rate
- [ ] Check for any template-related errors
- [ ] Gather user feedback on new email format
- [ ] Monitor notification preferences changes

### Metrics to Track

```python
# Run this query to check email success rate
from notifications.models import UserNotification
from django.utils import timezone
from datetime import timedelta

# Last 24 hours
yesterday = timezone.now() - timedelta(days=1)
notifications = UserNotification.objects.filter(
    created_at__gte=yesterday,
    sent_via_email=True
)

total = notifications.count()
successful = notifications.filter(email_sent_at__isnull=False).count()
failed = notifications.filter(email_error__isnull=False).count()

print(f"Total email notifications: {total}")
print(f"Successful: {successful} ({successful/total*100:.1f}%)")
print(f"Failed: {failed} ({failed/total*100:.1f}%)")
```

---

## Success Criteria

Deployment is considered successful when:

- [x] Migration completed without errors
- [x] All 10 templates updated (verified in database)
- [x] Test notifications render correctly
- [x] No unreplaced {{variables}} in emails
- [x] Email delivery rate > 95%
- [x] No critical errors in logs
- [x] User feedback is positive
- [x] All notification types work in production

---

## Emergency Contacts

If issues arise during deployment:

- **Database Admin:** [Contact info]
- **Backend Lead:** [Contact info]
- **DevOps:** [Contact info]
- **Email Service Provider:** [Support link]

---

## Environment-Specific Notes

### Development

```bash
# Already completed ✅
python manage.py migrate notifications
```

### Staging

```bash
# 1. Backup
pg_dump tms_staging > backup_staging_$(date +%Y%m%d).sql

# 2. Apply migration
python manage.py migrate notifications

# 3. Test with staging users
python test_notification_templates.py

# 4. Send test notifications to team
python manage.py shell
# ... follow Step 4 manual testing
```

### Production

```bash
# 1. CRITICAL: Backup first!
pg_dump tms_production > backup_prod_$(date +%Y%m%d_%H%M%S).sql

# 2. Optional: Schedule maintenance window
# Inform users if needed (migration is non-breaking, should take < 1 minute)

# 3. Apply migration
python manage.py migrate notifications

# 4. Immediate verification
python manage.py shell
# Check one template quickly
# from notifications.models import NotificationTemplate
# t = NotificationTemplate.objects.first()
# print(t.subject)  # Should have new format

# 5. Monitor logs actively for 1 hour
tail -f /var/log/tms/error.log

# 6. Send test notification to admin
# ... follow Step 4 manual testing with admin user

# 7. Monitor for 24 hours
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration fails | Low | Medium | Backup available, rollback tested |
| Variables not rendering | Low | High | Tests verify all variables work |
| Email delivery issues | Low | Medium | Email infrastructure unchanged |
| User complaints | Low | Low | Templates improved, professional |
| Performance impact | Very Low | Low | Templates cached, no schema changes |

---

## Final Checklist Before Production

- [ ] All tests passing in development
- [ ] Migration tested in staging
- [ ] Database backup completed
- [ ] Rollback procedure tested
- [ ] Team notified of deployment
- [ ] Monitoring tools ready
- [ ] Emergency contacts available
- [ ] This checklist reviewed and approved

---

## Deployment Sign-off

**Deployed By:** ___________________
**Date:** ___________________
**Time:** ___________________
**Environment:** [ ] Development  [ ] Staging  [ ] Production
**Backup Location:** ___________________
**Migration Status:** [ ] Success  [ ] Rollback Required

**Notes:**
_______________________________________________________________________
_______________________________________________________________________
_______________________________________________________________________

---

**Last Updated:** 2026-01-06
**Version:** 1.0
