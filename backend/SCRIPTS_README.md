# Utility Scripts

This directory contains utility scripts for development, testing, and system checks.

## Usage

All scripts should be run from the backend directory:

```bash
cd backend
python script_name.py
```

## Available Scripts

### System Checks

1. **check_notifications.py**
   - Purpose: Check notification status and email sending
   - Usage: `python check_notifications.py`
   - Shows recent notifications from the last 7 days and email delivery status

2. **check_transport_admin_permissions.py**
   - Purpose: Verify transport admin permissions are correctly configured
   - Usage: `python check_transport_admin_permissions.py`

3. **check_trfs.py**
   - Purpose: Check travel request forms (TRFs) status and data integrity
   - Usage: `python check_trfs.py`

4. **check_view_permissions.py**
   - Purpose: Audit view permissions across the system
   - Usage: `python check_view_permissions.py`

### Data Management

5. **delete_notifications.py**
   - Purpose: Bulk delete notifications (use with caution!)
   - Usage: `python delete_notifications.py`
   - **WARNING**: This will delete data. Review code before running.

6. **create_test_flights.py**
   - Purpose: Create test flight bookings for development/testing
   - Usage: `python create_test_flights.py`
   - Only use in development environment

7. **init_db.py**
   - Purpose: Initialize database with seed data
   - Usage: `python init_db.py`
   - Only use in development environment

## Future Improvements

These scripts should be converted to Django management commands:

```bash
# Example structure
backend/core/management/commands/
├── __init__.py
├── check_notifications.py      # python manage.py check_notifications
├── check_permissions.py         # python manage.py check_permissions
└── create_test_data.py          # python manage.py create_test_data
```

Django management commands provide:
- Better argument parsing
- Integration with Django's command system
- Consistent help text and documentation
- Proper transaction handling

## Archived Scripts

One-time migration scripts have been moved to `_archived_scripts/` directory.
