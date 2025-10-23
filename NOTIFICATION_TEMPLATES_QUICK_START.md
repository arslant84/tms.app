# Quick Start: Notification Templates

## ✅ What's Ready

Your notification templates system is **fully functional** with all 46 default templates from the source project!

## 🚀 Access

1. **Backend API:** http://localhost:8000/api/notifications/
2. **Frontend UI:** http://localhost:4200/admin/settings/notifications
3. **Login:** tekayev@outlook.com / admin123

## 📋 What You Have

### 46 Default Templates Ready to Use

**Accommodation (5 templates)**
- Request submitted, approved at each level, completed

**Claims (10 templates)**
- Submitted, focal/manager/HOD approval, finance processing, completed

**Transport (8 templates)**
- Request submitted, approved at each level, scheduled, rejected

**TRF - Travel Requests (10 templates)**
- Submitted, focal/manager/HOD approval, booking, completed

**Visa (7 templates)**
- Application submitted, approved at each level, processing, ready

### 30 Event Types

**By Module:**
- Accommodation: 4 events
- Claims: 6 events
- General: 4 events (account created, password reset, etc.)
- Transport: 4 events
- TRF: 7 events
- Visa: 5 events

## 🎯 Common Actions

### View All Templates

**URL:** http://localhost:4200/admin/settings/notifications

You'll see:
- List of 46 templates
- Template name, subject, type, recipient
- Active/inactive status
- Edit and Delete buttons

### Create Custom Template

1. Click **"Add New Template"**
2. Fill in:
   - **Name:** `my_custom_approval` (unique)
   - **Description:** "Custom approval email"
   - **Subject:** `Approval Required: {entityId}`
   - **Body:** HTML email content
   - **Event Type:** Select from dropdown
   - **Notification Type:** email / system / both
   - **Recipient Type:** approver / requestor / both
   - **Variables:** `["entityId", "requestorName", "approverName"]`
   - **Active:** ✓ Checked
3. Click **"Create Template"**
4. ✅ Done! Template created

### Edit Existing Template

1. Find template in list
2. Click **"Edit"**
3. Modify:
   - Subject line
   - Body content
   - Variables
   - Active status
4. Click **"Update Template"**
5. ✅ Done! Changes saved

### Use Variables in Templates

**Available Variables:**
- `{entityId}` - ID of request/claim/visa
- `{requestorName}` - Person who submitted
- `{approverName}` - Person approving
- `{department}` - Department name
- `{currentStatus}` - Current status
- `{comments}` - Approval comments
- `{viewUrl}` - Link to view request
- `{approvalUrl}` - Link to approve
- `{dashboardUrl}` - Link to dashboard

**Example Subject:**
```
Action Required: {requestorName} submitted {entityId}
```

**Example Body:**
```html
<html>
<body>
  <p>Dear {approverName},</p>
  <p><strong>{requestorName}</strong> from {department} has submitted a request.</p>
  <p><strong>Request ID:</strong> {entityId}</p>
  <p><strong>Status:</strong> {currentStatus}</p>
  <a href="{approvalUrl}">Review & Approve</a>
</body>
</html>
```

## 📊 API Endpoints

### Get All Templates
```bash
GET http://localhost:8000/api/notifications/templates/
```

**Response:** Array of 46 templates (without body)

### Get Single Template
```bash
GET http://localhost:8000/api/notifications/templates/{id}/
```

**Response:** Full template with body and variables

### Get Event Types
```bash
GET http://localhost:8000/api/notifications/event-types/
```

**Response:** Array of 30 event types

### Create Template
```bash
POST http://localhost:8000/api/notifications/templates/
Content-Type: application/json

{
  "name": "custom_template",
  "subject": "Subject with {variable}",
  "body": "<html>...</html>",
  "event_type": "uuid-of-event-type",
  "notification_type": "email",
  "recipient_type": "approver",
  "variables_available": ["variable", "another"],
  "is_active": true
}
```

### Update Template
```bash
PUT http://localhost:8000/api/notifications/templates/{id}/
Content-Type: application/json

{
  "name": "custom_template",
  "subject": "Updated subject",
  ...
}
```

### Delete Template
```bash
DELETE http://localhost:8000/api/notifications/templates/{id}/
```

## 🔍 Filter Templates

**By Module:**
```
GET /api/notifications/templates/?module=trf
```

**By Notification Type:**
```
GET /api/notifications/templates/?notification_type=email
```

**By Recipient:**
```
GET /api/notifications/templates/?recipient_type=approver
```

**Active Only:**
```
GET /api/notifications/templates/?is_active=true
```

## 💡 Common Use Cases

### Use Case 1: Create Reminder Email

**Goal:** Send weekly reminder to approvers

**Steps:**
1. Create template: `weekly_approval_reminder`
2. Subject: `Weekly Reminder: {pendingCount} Pending Approvals`
3. Body: List of pending approvals with links
4. Event Type: `deadline_reminder`
5. Recipient: `approver`
6. Variables: `["pendingCount", "approvalsList", "dashboardUrl"]`

### Use Case 2: Custom Rejection Email

**Goal:** More detailed rejection notification

**Steps:**
1. Create template: `custom_rejection_detailed`
2. Subject: `Request Rejected: {entityId}`
3. Body: Include rejection reason, next steps, contact info
4. Event Type: Select appropriate (trf_rejected, claim_rejected, etc.)
5. Recipient: `requestor`
6. Variables: `["entityId", "rejectionReason", "nextSteps", "contactEmail"]`

### Use Case 3: Multi-Language Template

**Goal:** Support multiple languages

**Steps:**
1. Create templates for each language:
   - `trf_approval_en` (English)
   - `trf_approval_ru` (Russian)
   - `trf_approval_tm` (Turkmen)
2. System chooses template based on user's language preference

## 🐛 Troubleshooting

### Problem: Templates not showing
**Solution:** Check backend API: http://localhost:8000/api/notifications/templates/
- Should return array of 46 templates
- If empty, run migration: `python migrate_notification_templates.py`

### Problem: Can't create template
**Solution:** Check:
- Template name is unique
- Subject and body are not empty
- Event type exists
- User has admin permissions

### Problem: Variables not working
**Solution:**
- Use curly braces: `{variableName}` not `{{variableName}}`
- Ensure variable is in `variables_available` array
- Check spelling exactly matches

## ✅ System Status

- ✅ **Backend:** Django REST API running on port 8000
- ✅ **Frontend:** Angular app running on port 4200
- ✅ **Database:** PostgreSQL with 46 templates, 30 event types
- ✅ **Default Templates:** All 46 templates migrated from source
- ✅ **API Endpoints:** All working and tested
- ✅ **CRUD Operations:** Create, read, update, delete functional

## 🎉 You're Ready!

All notification templates from your source project are now in the TMS application and ready to use when deployed!

**Next Steps:**
1. Test template creation in UI
2. Customize templates for your needs
3. Add new event types if needed
4. Configure email sending for production

---

**Need Help?** Check `NOTIFICATION_TEMPLATES_COMPLETE.md` for detailed documentation.
