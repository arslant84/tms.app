# TMS Backend Setup Guide

## Initial Database Setup

### Secure Admin Account Creation

The `init_db.py` script creates the initial admin user with **secure random passwords**.

**Basic Usage:**
```bash
python init_db.py
```

**Custom Admin Credentials (Optional):**
```bash
# Set custom admin email and password
export ADMIN_EMAIL="your-admin@company.com"
export ADMIN_PASSWORD="YourSecurePassword123!"

python init_db.py
```

**Important Security Notes:**
- ✅ Passwords are generated randomly if not provided
- ✅ Generated passwords are printed ONCE - save them immediately
- ⚠️ Change default password on first login
- ⚠️ Test users only created in development (not production)

### Example Output

```
Initializing database...
Creating superuser...
✅ Superuser created: admin@example.com
⚠️  Generated password: xK9$mP2@hQ7!vN4L
⚠️  SAVE THIS PASSWORD - Change it on first login!

📝 Test Users (Development Only):
  ✅ employee@example.com | Password: aB8#nR5@tY2!wM9K
  ✅ focal@example.com | Password: pQ4$xJ7@dL3!cF6N
  ✅ hod@example.com | Password: vM2#kS9@rT5!bH8P
  ✅ ticketing@example.com | Password: gN6$fQ3@wL7!xR4M
```

## Environment Variables

Add these to your `.env` file for custom setup:

```bash
# Admin Account (Optional)
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=YourSecurePassword123!

# Environment
DJANGO_ENV=development  # or 'production'
```

## Production Deployment

In production:
- Set `DJANGO_ENV=production` to skip test user creation
- Always provide custom `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- Implement forced password change on first login
