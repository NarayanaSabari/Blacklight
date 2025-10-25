# Authentication Setup Guide

## ✅ What's Already Implemented

### Backend (100% Complete)
- ✅ PM Admin user model with bcrypt password hashing
- ✅ JWT-based authentication service with access & refresh tokens
- ✅ Login, logout, and token refresh endpoints
- ✅ Account lockout after 5 failed attempts (30 min lockout)
- ✅ Token blacklisting in Redis
- ✅ Authentication middleware with OPTIONS bypass for CORS
- ✅ Seed script for default admin user
- ✅ All routes accept both ID and slug identifiers

### Frontend (100% Complete)
- ✅ PMAdminAuthContext with login/logout/refresh
- ✅ LoginPage with email/password form
- ✅ API client with Authorization header injection
- ✅ Token storage in localStorage
- ✅ Automatic redirect to login on 401 errors
- ✅ Protected routes structure

## 🚀 Quick Start

### 1. Ensure Backend is Running

```bash
cd server

# If not already done, initialize database and seed data
python manage.py init
python manage.py seed-all

# If database exists but no PM admin, seed just the admin
python manage.py seed-pm-admin

# Start the backend
docker-compose up -d  # OR
flask run
```

**Default Credentials:**
- Email: `admin@blacklight.com`
- Password: `Admin@123`

### 2. Start Frontend

```bash
cd ui/centralD
npm run dev
```

### 3. Login

1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Email: `admin@blacklight.com`
   - Password: `Admin@123`
3. Click "Sign in"

The frontend will:
- Call `POST /api/pm-admin/auth/login`
- Store the access token in `localStorage` as `pm_admin_token`
- Store refresh token in response data
- Navigate to `/tenants`

### 4. Verify Authentication

All subsequent API calls will automatically include:
```
Authorization: Bearer <access_token>
```

## 🔧 Backend Endpoints

### Authentication Endpoints (No Auth Required)

#### Login
```http
POST /api/pm-admin/auth/login
Content-Type: application/json

{
  "email": "admin@blacklight.com",
  "password": "Admin@123"
}

Response 200:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "admin": {
    "id": 1,
    "email": "admin@blacklight.com",
    "first_name": "Super",
    "last_name": "Admin",
    "is_active": true,
    ...
  }
}
```

#### Refresh Token
```http
POST /api/pm-admin/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}

Response 200:
{
  "access_token": "NEW_TOKEN...",
  "refresh_token": "SAME_TOKEN...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "admin": { ... }
}
```

### Protected Endpoints (Require Auth)

#### Get Current Admin
```http
GET /api/pm-admin/current
Authorization: Bearer <access_token>

Response 200:
{
  "id": 1,
  "email": "admin@blacklight.com",
  "first_name": "Super",
  "last_name": "Admin",
  ...
}
```

#### Logout
```http
POST /api/pm-admin/auth/logout
Authorization: Bearer <access_token>

Response 200:
{
  "message": "Logged out successfully"
}
```

## 📋 Frontend Flow

### Login Flow
```typescript
// 1. User submits login form
const credentials = { email, password };

// 2. Call auth context login method
await login(credentials);
// Internally calls: POST /api/pm-admin/auth/login
// Stores token: localStorage.setItem('pm_admin_token', access_token)
// Sets currentAdmin state

// 3. Navigate to protected route
navigate('/tenants');
```

### API Request Flow
```typescript
// All requests through apiClient automatically:
// 1. Add Authorization header from localStorage
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('pm_admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 2. Handle 401 responses
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('pm_admin_token');
      window.location.href = '/login';
    }
  }
);
```

## 🔐 Security Features

### Token Configuration
- **Access Token:** 24 hours validity, stored in localStorage
- **Refresh Token:** 30 days validity, stored in Redis
- **Algorithm:** HS256 (HMAC with SHA-256)
- **Secret:** From `SECRET_KEY` environment variable

### Account Protection
- **Max Failed Attempts:** 5
- **Lockout Duration:** 30 minutes
- **Password Hashing:** bcrypt with auto-generated salt
- **Token Blacklisting:** On logout, tokens blacklisted in Redis

### CORS Configuration
- **Origins:** Configurable via `CORS_ORIGINS` (default: `*`)
- **Methods:** GET, POST, PUT, PATCH, DELETE, OPTIONS
- **Credentials:** Supported
- **OPTIONS Bypass:** Authentication skipped for CORS preflight

## 🐛 Troubleshooting

### "CORS policy" Error
✅ **Fixed!** OPTIONS requests now bypass authentication middleware.

### "Authorization header is required"
- Check that `localStorage.getItem('pm_admin_token')` returns a valid token
- Open browser DevTools → Application → Local Storage → Check `pm_admin_token`
- If missing, login again

### "Invalid email or password"
```bash
# Reset admin password to default
cd server
python -c "
from app import create_app, db
from app.models import PMAdminUser
import bcrypt

app = create_app()
with app.app_context():
    admin = PMAdminUser.query.filter_by(email='admin@blacklight.com').first()
    if admin:
        admin.password_hash = bcrypt.hashpw(b'Admin@123', bcrypt.gensalt()).decode('utf-8')
        admin.failed_login_attempts = 0
        admin.locked_until = None
        db.session.commit()
        print('Password reset to Admin@123')
"
```

### "Account is locked"
```bash
# Unlock account
cd server
python -c "
from app import create_app, db
from app.models import PMAdminUser

app = create_app()
with app.app_context():
    admin = PMAdminUser.query.filter_by(email='admin@blacklight.com').first()
    if admin:
        admin.failed_login_attempts = 0
        admin.locked_until = None
        db.session.commit()
        print('Account unlocked')
"
```

## 🧪 Testing Authentication

### Manual Testing Checklist
- [ ] Login with correct credentials → Success, redirects to /tenants
- [ ] Login with wrong password → Error toast, account not locked (first 4 attempts)
- [ ] Login with wrong password 5 times → Account locked for 30 min
- [ ] Access protected route without token → Redirect to /login
- [ ] Logout → Token cleared, redirect to /login
- [ ] Refresh page after login → User stays authenticated
- [ ] Token expires → Auto-logout on next API call

### cURL Testing

```bash
# 1. Login
curl -X POST http://localhost:5000/api/pm-admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@blacklight.com","password":"Admin@123"}'

# Save the access_token from response

# 2. Get current admin
curl -X GET http://localhost:5000/api/pm-admin/current \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 3. List tenants (protected route)
curl -X GET http://localhost:5000/api/tenants \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🎯 Next Steps

All authentication is fully implemented! You can now:

1. ✅ **Login to Central Dashboard** with `admin@blacklight.com` / `Admin@123`
2. ✅ **Access all tenant management features** (create, view, edit, suspend, delete)
3. ✅ **Use protected API endpoints** with automatic token injection

### Optional Enhancements (Future)
- [ ] Add "Remember Me" functionality
- [ ] Implement password reset via email
- [ ] Add 2FA (Two-Factor Authentication)
- [ ] Password strength requirements
- [ ] Password expiry policy
- [ ] Session management dashboard
- [ ] Login history tracking
