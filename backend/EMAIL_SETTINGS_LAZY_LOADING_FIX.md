# Email Settings Lazy Loading Fix

## Issue
The application was accessing the database during app initialization to load email settings, which caused:
- `RuntimeWarning: Accessing the database during app initialization is discouraged`
- Potential issues in production with multiple worker processes
- Database connection problems during migrations or when database is not ready
- Violation of Django's initialization lifecycle best practices

## Root Cause
Email settings were being loaded in `accounts/apps.py` → `AccountsConfig.ready()` method, which runs during Django app initialization **before** the database is guaranteed to be ready.

```python
# OLD CODE (BAD PRACTICE)
class AccountsConfig(AppConfig):
    def ready(self):
        from tms_project.settings import load_email_settings
        load_email_settings()  # ❌ Database access during initialization!
```

## Solution: Lazy Loading Pattern

Implemented a **lazy loading pattern** where email settings are loaded only when first needed, not at startup.

### 1. Created Lazy Loader (`core/email_settings_loader.py`)

**Key Features**:
- **Singleton pattern**: Ensures only one instance exists
- **Thread-safe**: Uses locks to prevent race conditions
- **Cached loading**: Loads settings only once, subsequent calls use cache
- **Graceful failure**: Falls back to defaults if database is unavailable

**API**:
```python
from core.email_settings_loader import ensure_email_settings_loaded, reload_email_settings

# Load settings lazily (safe to call multiple times)
ensure_email_settings_loaded()

# Force reload settings (e.g., after admin updates)
reload_email_settings()
```

### 2. Updated Notification Service

Modified `notifications/services.py` to load email settings before sending emails:

```python
@staticmethod
def send_email_notification(notification):
    # Lazy load email settings from database (on first use only)
    ensure_email_settings_loaded()

    # Now send email...
```

### 3. Removed App Initialization Loading

Updated `accounts/apps.py`:
```python
# NEW CODE (BEST PRACTICE)
class AccountsConfig(AppConfig):
    def ready(self):
        # NO database access here!
        pass
```

### 4. Cleaned Up Settings File

Removed the old `load_email_settings()` function from `tms_project/settings.py` and added clear documentation.

## How It Works

### Before (❌ Bad):
```
App Startup
  ↓
AccountsConfig.ready()
  ↓
load_email_settings()
  ↓
DATABASE ACCESS ❌ (causes warning)
  ↓
Settings loaded
  ↓
App continues...
```

### After (✅ Good):
```
App Startup
  ↓
AccountsConfig.ready()
  ↓
(nothing - just pass)
  ↓
App ready
  ↓
User triggers action (e.g., transport request created)
  ↓
Notification needs to be sent
  ↓
ensure_email_settings_loaded()
  ↓
DATABASE ACCESS ✅ (only when needed)
  ↓
Settings cached
  ↓
Email sent
  ↓
Future emails use cached settings (no DB access)
```

## Benefits

### For Development:
✅ **No more warnings** during server startup
✅ **Clean console output** for better debugging
✅ **Faster app initialization** (no DB queries at startup)

### For Production:
✅ **Production-ready**: Follows Django best practices
✅ **Multiple workers**: Safe with Gunicorn/uWSGI multi-worker setups
✅ **Migration-safe**: Won't fail during database migrations
✅ **Database resilience**: Gracefully handles DB unavailability
✅ **Thread-safe**: Prevents race conditions in concurrent environments

### For Operations:
✅ **Settings reload**: Can reload settings without restarting server
✅ **Graceful degradation**: Falls back to environment variable settings if DB unavailable
✅ **Clear logging**: Informative messages about what's happening

## Testing

### Test 1: Server Startup (No Warning)
```bash
cd backend
python manage.py runserver
```

**Expected**: No `RuntimeWarning` about database access during initialization.

### Test 2: Email Sending (Lazy Load)
```python
from notifications.services import NotificationService
from accounts.models import User

user = User.objects.first()
NotificationService.create_notification(
    user=user,
    title="Test",
    message="Testing lazy loading",
    send_email=True
)
```

**Expected**:
- Settings loaded on first email send
- Console output: `[OK] Loaded X email settings from database`
- Subsequent emails use cached settings (no reload)

### Test 3: Settings Reload
```python
from core.email_settings_loader import reload_email_settings

# Update settings in admin panel
# ...

# Force reload
reload_email_settings()

# Next email uses new settings
```

## Migration Guide

No migration needed! This change is backward-compatible:
- ✅ Existing code continues to work
- ✅ No database schema changes
- ✅ No API changes
- ✅ Settings still loaded automatically before email sending

## Files Modified

### Created:
- ✅ `core/email_settings_loader.py` - Lazy loader implementation

### Modified:
- ✅ `accounts/apps.py` - Removed database access from `ready()`
- ✅ `notifications/services.py` - Added lazy loading before email send
- ✅ `tms_project/settings.py` - Removed old `load_email_settings()` function

## Code Quality Improvements

### Before:
- ❌ Database access during app initialization
- ❌ Settings loaded even when not needed
- ❌ No control over reload timing
- ❌ Not thread-safe
- ❌ Failed silently in many scenarios

### After:
- ✅ Database access only when needed
- ✅ Settings loaded on-demand
- ✅ Explicit reload API
- ✅ Thread-safe singleton pattern
- ✅ Graceful error handling with fallbacks

## Summary

**Problem**: RuntimeWarning about database access during app initialization
**Root Cause**: Email settings loaded in `AppConfig.ready()`
**Solution**: Lazy loading pattern with singleton caching
**Result**: Production-ready, best-practice implementation
**Impact**: Zero breaking changes, improved performance and reliability

---

**Date**: December 23, 2025
**Status**: ✅ FIXED - Production Ready
**Breaking Changes**: None
**Backward Compatible**: Yes
