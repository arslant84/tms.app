# TMS Backend Deployment Guide

## Environment Configuration

The TMS backend automatically adapts URLs based on environment configuration using the `FRONTEND_URL` environment variable.

### Development Environment

In `.env` (development):
```env
DEBUG=True
FRONTEND_URL=http://localhost:4200
```

Password reset emails will contain links like:
```
http://localhost:4200/auth/reset-password?token=...
```

### Production Environment

When deploying to production:

1. **Copy production template:**
   ```bash
   cp .env.production .env
   ```

2. **Update FRONTEND_URL:**
   ```env
   DEBUG=False
   FRONTEND_URL=https://yourdomain.com
   ```

3. **Password reset emails will automatically use:**
   ```
   https://yourdomain.com/auth/reset-password?token=...
   ```

## How It Works

The password reset view (`accounts/views.py:356`) uses `settings.FRONTEND_URL`:

```python
reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
```

Django's `python-decouple` loads `FRONTEND_URL` from the `.env` file:

```python
# settings.py
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:4200')
```

**No code changes needed** - URLs automatically adapt based on environment!

## Email Configuration

### Custom Email Backend

The TMS uses a custom email backend (`utils.email_backend.CustomEmailBackend`) that provides:
- Better SSL/TLS handling for Windows environments
- Improved error reporting
- Fallback mechanisms for certificate issues

### Testing Email in Production

```bash
python manage.py test_email your-email@example.com --show-config
```

### Environment Variables

Required email settings in `.env`:
```env
EMAIL_BACKEND=utils.email_backend.CustomEmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=SynTra TMS <noreply@yourdomain.com>
```

## Production Checklist

- [ ] Copy `.env.production` to `.env`
- [ ] Update `SECRET_KEY` (generate new one)
- [ ] Set `DEBUG=False`
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Update `FRONTEND_URL` with production domain (https://yourdomain.com)
- [ ] Update `CORS_ALLOWED_ORIGINS` with production domain
- [ ] Update `CSRF_TRUSTED_ORIGINS` with production domain
- [ ] Configure production database credentials
- [ ] Set up SMTP email credentials
- [ ] Enable security settings (SSL_REDIRECT, SECURE_COOKIES, HSTS)
- [ ] Test email sending: `python manage.py test_email your-email@example.com`

## Security Notes

### Email Error Handling

The password reset endpoint includes error handling to prevent SMTP failures from exposing system information:

```python
try:
    send_mail(...)
except Exception as e:
    # Log error but don't expose to user
    logger.error(f"Failed to send password reset email: {str(e)}")
    # Continue - user sees generic success message
```

This prevents:
- Email enumeration attacks
- System information disclosure
- 500 errors from SMTP issues

### SSL/TLS Configuration

The custom email backend handles certificate verification appropriately:
- **Development:** More permissive SSL handling for local testing
- **Production:** Full certificate verification enabled

## Troubleshooting

### SMTP Connection Issues

1. Run diagnostic script:
   ```bash
   python test_smtp.py
   ```

2. Test through Django:
   ```bash
   python manage.py test_email test@example.com --show-config
   ```

3. Check firewall/antivirus allows port 587

### Email Not Sending in Production

1. Verify SMTP credentials are correct
2. Check `EMAIL_HOST` and `EMAIL_PORT` settings
3. Ensure `EMAIL_USE_TLS=True` for port 587
4. Review logs: `tail -f /var/log/tms/django.log`
5. Test with: `python manage.py test_email`

### Wrong URLs in Emails

1. Check `.env` file has correct `FRONTEND_URL`
2. Restart Django application after changing `.env`
3. Verify with: `python manage.py shell`
   ```python
   from django.conf import settings
   print(settings.FRONTEND_URL)
   ```

## Related Files

- `.env` - Development environment configuration
- `.env.production` - Production environment template
- `.env.example` - Example configuration for new developers
- `accounts/views.py` - Password reset implementation
- `utils/email_backend.py` - Custom email backend
- `test_smtp.py` - SMTP diagnostic tool
