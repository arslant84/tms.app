# Authentication Fix Guide - Dashboard HTTP Error

**Error:** `❌ Error fetching dashboard data: HttpErrorResponse`
**HTTP Status:** 401 Unauthorized
**Root Cause:** User is not authenticated or token is invalid/missing

## Problem Summary

The dashboard is trying to fetch data from `/api/insights/dashboard/summary/` but the backend requires authentication. The HTTP interceptor is correctly configured to add the auth token, but the user either:
1. Has not logged in
2. Has an expired/invalid token
3. Token is not being stored properly

## Solution Steps

### Step 1: Check if User is Logged In

**In Browser Console:**
```javascript
// Check if token exists in localStorage
localStorage.getItem('auth_token')

// Should return a token string like: "abc123def456..."
// If it returns null, user is not logged in
```

### Step 2: Login to the Application

**Method A: Use Admin User (Already Created)**
1. Navigate to `http://localhost:4200/auth/login` (or `/login`)
2. Enter credentials:
   - Email: `admin@tms.com`
   - Password: `admin123`
3. Click Login
4. Should redirect to dashboard

**Method B: Create Django Admin Super User**
```bash
cd backend
python manage.py createsuperuser

# Follow prompts:
# Email: your-email@example.com
# Password: your-password
```

**Method C: Use Django Admin to Login**
1. Navigate to `http://localhost:8000/admin/`
2. Login with Django admin credentials
3. Go back to Angular app
4. Should be authenticated

### Step 3: Verify Token is Set

After logging in, check browser console:
```javascript
localStorage.getItem('auth_token')
// Should now show a token
```

### Step 4: Verify Interceptor is Working

After logging in, in Network tab:
1. Go to dashboard
2. Look for request to `/api/insights/dashboard/summary/`
3. Check Request Headers
4. Should see: `Authorization: Token abc123...`

### Step 5: Test Dashboard Endpoint Manually

**With Token:**
```bash
# Replace YOUR_TOKEN with actual token from localStorage
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/insights/dashboard/summary/
```

**Expected Response (200 OK):**
```json
{
  "total_trfs": 0,
  "pending_trfs": 0,
  "approved_trfs": 0,
  "rejected_trfs": 0,
  "total_travel_cost": 0,
  "total_expense_claims": 0,
  "active_bookings": 0,
  "pending_approvals": 0,
  "recent_activities": []
}
```

## Quick Fix: Bypass Authentication for Development (TEMPORARY)

**⚠️ WARNING: Only for development! Remove before production!**

### Option 1: Make Dashboard Summary Public (Django)

Edit `backend/insights/views.py`:

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny  # Add this

@api_view(['GET'])
@permission_classes([AllowAny])  # Add this line
def dashboard_summary(request):
    # ... existing code
```

### Option 2: Use Session Authentication

If you're logged into Django Admin, session auth might work.

Edit `backend/tms_project/settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # Add this
    ],
    # ...
}
```

## Proper Authentication Flow

### How It Should Work:

1. **User visits app** → Redirected to `/login`
2. **User enters credentials** → POST to `/api/accounts/login/`
3. **Backend responds** with:
   ```json
   {
     "token": "abc123...",
     "user": { ... }
   }
   ```
4. **Frontend stores token** in `localStorage`
5. **All subsequent requests** include `Authorization: Token abc123...`
6. **Backend validates token** and returns data

### Verify Auth Service

Check `frontend/src/app/core/services/auth.service.ts`:

```typescript
login(email: string, password: string): Observable<any> {
  return this.http.post(`${environment.apiUrl}/accounts/login/`, {
    email,
    password
  }).pipe(
    tap((response: any) => {
      // Store token
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('user', JSON.stringify(response.user));
    })
  );
}

getToken(): string | null {
  return localStorage.getItem('auth_token');
}
```

## Check Backend Auth Configuration

### 1. Verify Django REST Framework Settings

`backend/tms_project/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'rest_framework.authtoken',  # Must be included
    # ...
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Requires auth by default
    ],
}
```

### 2. Verify Auth Token Model is Migrated

```bash
cd backend
python manage.py migrate

# Should see:
# Running migrations:
#   Applying authtoken.0001_initial... OK
```

### 3. Create Token for Existing User

```bash
python manage.py shell

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
user = User.objects.get(email='admin@tms.com')
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
```

Copy the token and use it manually:

```javascript
// In browser console
localStorage.setItem('auth_token', 'YOUR_TOKEN_HERE');
location.reload();
```

## Common Issues

### Issue 1: CORS Error
**Symptom:** Browser blocks request
**Solution:** Add CORS headers in Django

```bash
pip install django-cors-headers
```

`settings.py`:
```python
INSTALLED_APPS = [
    'corsheaders',
    # ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add at top
    # ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
]

CORS_ALLOW_CREDENTIALS = True
```

### Issue 2: Token Not Being Sent
**Symptom:** Interceptor not adding Authorization header
**Check:** Browser console should show:
```
Adding auth token to request: http://localhost:8000/api/insights/dashboard/summary/
```

If not showing, interceptor may not be running.

### Issue 3: Wrong Token Format
**Django REST Framework expects:**
```
Authorization: Token abc123def456
```

**NOT:**
```
Authorization: Bearer abc123def456  ❌ (This is JWT format)
```

### Issue 4: Backend Not Running
```bash
cd backend
python manage.py runserver

# Should see:
# Starting development server at http://127.0.0.1:8000/
```

## Testing Checklist

- [ ] Backend server is running on port 8000
- [ ] Frontend server is running on port 4200
- [ ] User can access login page
- [ ] Login page successfully authenticates
- [ ] Token is stored in localStorage after login
- [ ] Dashboard loads without errors
- [ ] Network tab shows 200 OK for dashboard summary
- [ ] Authorization header is present in requests

## Debug Commands

**Check if user has auth token:**
```python
# Django shell
python manage.py shell

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
user = User.objects.get(email='admin@tms.com')
token = Token.objects.filter(user=user).first()
print(f"Has token: {token is not None}")
if token:
    print(f"Token: {token.key}")
```

**Test endpoint with curl:**
```bash
# Get token first
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tms.com","password":"admin123"}'

# Use token in subsequent request
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/insights/dashboard/summary/
```

## Resolution Summary

**The dashboard HTTP error is caused by missing authentication.**

**To fix:**
1. Login to the application using credentials
2. Verify token is stored
3. Refresh dashboard
4. Error should be resolved

**If still not working:**
- Check backend auth configuration
- Verify migrations are applied
- Check that authtoken is installed
- Verify user has a token in database

---

**Related Files:**
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/core/services/auth.service.ts`
- `backend/accounts/views.py` (login endpoint)
- `backend/insights/views.py` (dashboard endpoint)
- `backend/tms_project/settings.py` (REST Framework config)

**Last Updated:** 2025-10-15
