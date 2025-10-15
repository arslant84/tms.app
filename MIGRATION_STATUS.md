# TMS Project Migration Status

**Migration From:** Next.js/React (pctsb.syntra) → Angular/Django (tms-app)
**Last Updated:** 2025-10-14
**Status:** In Progress

## Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Backend Migration Status](#backend-migration-status)
4. [Frontend Migration Status](#frontend-migration-status)
5. [Database Schema](#database-schema)
6. [Next Steps](#next-steps)

## Overview

This document tracks the progress of migrating the Travel Management System (TMS) from a Next.js/React + PostgreSQL stack to an Angular + Django REST Framework stack.

**Source Project:** `C:\Users\Arslan\Documents\Projects\tms-app\pctsb.syntra`
**Target Backend:** `C:\Users\Arslan\Documents\Projects\tms-app\backend`
**Target Frontend:** `C:\Users\Arslan\Documents\Projects\tms-app\frontend`

## Project Structure

### Source Project Structure (pctsb.syntra)
```
pctsb.syntra/
├── src/
│   ├── app/
│   │   ├── accommodation/        # Accommodation request pages
│   │   ├── admin/                # Admin panel (users, settings, processing)
│   │   ├── api/                  # Next.js API routes
│   │   ├── claims/               # Expense claims
│   │   ├── notifications/        # Notifications UI
│   │   ├── profile/              # User profile
│   │   ├── reports/              # Reporting module
│   │   ├── transport/            # Transport requests
│   │   ├── trf/                  # Travel Request Forms
│   │   └── visa/                 # Visa applications
│   ├── components/               # Reusable UI components
│   ├── contexts/                 # React contexts
│   ├── hooks/                    # Custom React hooks
│   ├── lib/                      # Utility libraries
│   └── types/                    # TypeScript type definitions
└── scripts/
    ├── database/                 # Database schema and migrations
    └── sql/                      # SQL scripts

### Target Project Structure
```
tms-app/
├── backend/                      # Django REST Framework backend
│   ├── accounts/                 # ✓ User management, roles, permissions
│   ├── accommodation/            # ⚠ Models created, needs views/serializers
│   ├── bookings/                 # ⚠ Flight bookings (needs expansion)
│   ├── expenses/                 # ⚠ Basic models, needs claims logic
│   ├── insights/                 # ⚠ Dashboard/analytics (skeleton)
│   ├── tms_project/              # ✓ Django settings
│   ├── trf/                      # ⚠ Basic models, needs full migration
│   └── visa/                     # ✓ Models, views, serializers completed
└── frontend/                     # Angular frontend
    └── src/app/
        ├── features/
        │   ├── admin/            # ⚠ Clerk panel (partial)
        │   ├── expense-claims/   # ⚠ Basic UI created
        │   ├── requests/         # ⚠ Accommodation, travel, visa (partial)
        │   └── trf-management/   # ⚠ TRF forms (in progress)
        └── shared/               # ✓ Header, sidebar, common components
```

## Backend Migration Status

### Modules Overview

| Module | Status | Models | Serializers | Views | URLs | Notes |
|--------|--------|--------|-------------|-------|------|-------|
| **accounts** | ✅ Complete | ✅ | ✅ | ✅ | ✅ | User, Role, Permission models migrated |
| **visa** | ✅ Complete | ✅ | ✅ | ✅ | ✅ | Full visa application workflow |
| **accommodation** | ⚠ Partial | ✅ | ❌ | ❌ | ❌ | Models exist, needs views/serializers/URLs |
| **trf** | ⚠ Partial | ⚠ | ❌ | ❌ | ❌ | Basic models, needs itinerary, passport, bank details |
| **expenses** | ⚠ Partial | ⚠ | ❌ | ❌ | ❌ | Basic models, needs items, FX rates, approval workflow |
| **bookings** | ⚠ Partial | ⚠ | ❌ | ❌ | ❌ | Flight bookings skeleton, needs expansion |
| **transport** | ❌ Missing | ❌ | ❌ | ❌ | ❌ | Not yet created |
| **workflows** | ❌ Missing | ❌ | ❌ | ❌ | ❌ | Approval workflow system not migrated |
| **notifications** | ❌ Missing | ❌ | ❌ | ❌ | ❌ | Notification system not migrated |
| **insights** | ⚠ Skeleton | ⚠ | ❌ | ❌ | ❌ | Dashboard/analytics module exists but empty |

### Detailed Backend Status

#### 1. Accounts Module ✅ COMPLETE
**Location:** `backend/accounts/`

**Completed:**
- ✅ User model with role-based access control
- ✅ Role and Permission models
- ✅ User serializers and viewsets
- ✅ Authentication endpoints
- ✅ Database migrations applied

**Source Tables Migrated:**
- `users` → User model
- `roles` → Role model
- `permissions` → Permission model
- `role_permissions` → ManyToMany relationship

---

#### 2. Visa Module ✅ COMPLETE
**Location:** `backend/visa/`

**Completed:**
- ✅ VisaApplication model
- ✅ VisaApprovalStep model
- ✅ VisaDocument model
- ✅ Full CRUD API endpoints
- ✅ Document upload handling
- ✅ Approval workflow

**Source Tables Migrated:**
- `visa_applications` → VisaApplication
- `visa_approval_steps` → VisaApprovalStep
- `visa_documents` → VisaDocument

---

#### 3. Accommodation Module ⚠ PARTIAL
**Location:** `backend/accommodation/`

**Completed:**
- ✅ AccommodationStaffHouse model
- ✅ AccommodationRoom model
- ✅ AccommodationRequest model
- ✅ AccommodationBooking model

**Missing:**
- ❌ Serializers for all models
- ❌ ViewSets for CRUD operations
- ❌ URL routing
- ❌ Approval workflow integration
- ❌ Room availability logic
- ❌ Calendar/booking conflict checks

**Source Tables to Migrate:**
- `accommodation_staff_houses` → AccommodationStaffHouse ✅
- `accommodation_rooms` → AccommodationRoom ✅
- `accommodation_bookings` → AccommodationBooking ✅
- `accommodation_requests` → AccommodationRequest (needs review)

---

#### 4. TRF (Travel Request Form) Module ⚠ PARTIAL
**Location:** `backend/trf/`

**Completed:**
- ✅ Basic TravelRequest model structure

**Missing:**
- ❌ TrfItinerarySegment model
- ❌ TrfAccommodationDetail model
- ❌ TrfAdvanceBankDetail model
- ❌ TrfPassportDetail model
- ❌ TrfApprovalStep model
- ❌ Serializers for all models
- ❌ ViewSets and endpoints
- ❌ URL routing
- ❌ Different TRF types (Domestic, Overseas, Home Leave, External Parties)
- ❌ Auto-generation of TSRs (Transport/Accommodation sub-requests)

**Source Tables to Migrate:**
- `travel_requests` → TravelRequest ⚠
- `trf_itinerary_segments` → TrfItinerarySegment ❌
- `trf_accommodation_details` → TrfAccommodationDetail ❌
- `trf_advance_bank_details` → TrfAdvanceBankDetail ❌
- `trf_passport_details` → TrfPassportDetail ❌
- `trf_approval_steps` → TrfApprovalStep ❌

---

#### 5. Expenses/Claims Module ⚠ PARTIAL
**Location:** `backend/expenses/`

**Completed:**
- ✅ Basic ExpenseClaim model structure

**Missing:**
- ❌ ExpenseClaimItem model
- ❌ ExpenseClaimFxRate model
- ❌ ClaimsApprovalStep model
- ❌ Serializers for all models
- ❌ ViewSets and endpoints
- ❌ URL routing
- ❌ Claims calculation logic
- ❌ Approval workflow
- ❌ Medical claims handling
- ❌ Integration with TRF

**Source Tables to Migrate:**
- `expense_claims` → ExpenseClaim ⚠
- `expense_claim_items` → ExpenseClaimItem ❌
- `expense_claim_fx_rates` → ExpenseClaimFxRate ❌
- `claims_approval_steps` → ClaimsApprovalStep ❌

---

#### 6. Transport Module ❌ NOT STARTED
**Location:** `backend/` (needs creation)

**Required:**
- ❌ Create `transport` Django app
- ❌ TransportRequest model
- ❌ TransportDetail model
- ❌ TransportApprovalStep model
- ❌ Serializers
- ❌ ViewSets
- ❌ URL routing
- ❌ Integration with TRF auto-generation

**Source Tables to Migrate:**
- `transport_requests` → TransportRequest ❌
- `transport_details` → TransportDetail ❌
- `transport_approval_steps` → TransportApprovalStep ❌

---

#### 7. Workflows Module ❌ NOT STARTED
**Location:** `backend/` (needs creation)

**Required:**
- ❌ Create `workflows` Django app
- ❌ WorkflowTemplate model
- ❌ WorkflowStep model
- ❌ WorkflowInstance model
- ❌ WorkflowStepExecution model
- ❌ WorkflowCondition model
- ❌ WorkflowDelegation model
- ❌ WorkflowAuditLog model
- ❌ Generic workflow engine
- ❌ Integration with all approval modules

**Source Tables to Migrate:**
- `workflow_templates` → WorkflowTemplate ❌
- `workflow_steps` → WorkflowStep ❌
- `workflow_instances` → WorkflowInstance ❌
- `workflow_step_executions` → WorkflowStepExecution ❌
- `workflow_conditions` → WorkflowCondition ❌
- `workflow_delegations` → WorkflowDelegation ❌
- `workflow_audit_log` → WorkflowAuditLog ❌

---

#### 8. Notifications Module ❌ NOT STARTED
**Location:** `backend/` (needs creation)

**Required:**
- ❌ Create `notifications` Django app
- ❌ NotificationEventType model
- ❌ NotificationTemplate model
- ❌ UserNotificationSubscription model
- ❌ UserNotificationPreference model
- ❌ UserNotification model
- ❌ Email notification service
- ❌ In-app notification service
- ❌ WebSocket/real-time notifications
- ❌ Notification triggers for all modules

**Source Tables to Migrate:**
- `notification_event_types` → NotificationEventType ❌
- `notification_templates` → NotificationTemplate ❌
- `notification_user_subscriptions` → UserNotificationSubscription ❌
- `user_notification_preferences` → UserNotificationPreference ❌
- `user_notifications` → UserNotification ❌

---

#### 9. Bookings Module ⚠ PARTIAL
**Location:** `backend/bookings/`

**Completed:**
- ✅ Basic module structure

**Missing:**
- ❌ FlightBooking model
- ❌ Flight search/booking logic
- ❌ Integration with TRF
- ❌ Ticketing admin features
- ❌ Serializers, views, URLs

**Source Tables to Migrate:**
- `flight_bookings` → FlightBooking ❌
- `flight_details` → FlightDetail ❌

---

#### 10. Insights/Reports Module ⚠ SKELETON
**Location:** `backend/insights/`

**Required:**
- ❌ Dashboard summary endpoints
- ❌ Travel analytics
- ❌ Expense reports
- ❌ User activity tracking
- ❌ Department-wise statistics
- ❌ Export functionality (PDF, Excel)

---

## Frontend Migration Status

### Modules Overview

| Module | Status | Components | Services | Routing | Forms | Notes |
|--------|--------|------------|----------|---------|-------|-------|
| **Admin Panel** | ⚠ Partial | ⚠ | ⚠ | ⚠ | ❌ | Clerk panel exists, needs expansion |
| **TRF Management** | ⚠ Partial | ⚠ | ⚠ | ⚠ | ⚠ | Form wizard in progress |
| **Visa** | ⚠ Partial | ⚠ | ✅ | ⚠ | ⚠ | Initial implementation |
| **Accommodation** | ⚠ Partial | ⚠ | ⚠ | ⚠ | ⚠ | Request form exists |
| **Expense Claims** | ⚠ Partial | ⚠ | ❌ | ⚠ | ⚠ | Create form exists |
| **Transport** | ❌ Missing | ❌ | ❌ | ❌ | ❌ | Not yet created |
| **Notifications** | ❌ Missing | ❌ | ❌ | ❌ | ❌ | Not yet created |
| **Reports** | ❌ Missing | ❌ | ❌ | ❌ | ❌ | Not yet created |
| **Dashboard** | ⚠ Skeleton | ⚠ | ❌ | ⚠ | ❌ | Basic structure exists |

### Detailed Frontend Status

#### 1. Admin Panel ⚠ PARTIAL
**Location:** `frontend/src/app/features/admin/`

**Completed:**
- ✅ Clerk panel component structure
- ⚠ Basic user management UI

**Missing:**
- ❌ Accommodation admin panel
- ❌ Transport admin panel
- ❌ Visa processing panel
- ❌ Claims processing panel
- ❌ Flight bookings panel
- ❌ User management (full CRUD)
- ❌ Role & permission management
- ❌ Workflow configuration UI
- ❌ Notification template management
- ❌ System settings

**Source Pages to Migrate:**
- `admin/users` → User management ❌
- `admin/accommodation` → Accommodation admin ❌
- `admin/accommodation/processing` → Room booking interface ❌
- `admin/visa` → Visa list ❌
- `admin/visa/processing` → Visa processing ❌
- `admin/claims` → Claims list ❌
- `admin/claims/processing` → Claims processing ❌
- `admin/transport` → Transport list ❌
- `admin/transport/processing` → Transport processing ❌
- `admin/flights` → Flight bookings ❌
- `admin/flights/processing` → Flight booking interface ❌
- `admin/approvals` → Approval queue ❌
- `admin/settings` → System settings ❌
- `admin/settings/workflows` → Workflow config ❌
- `admin/settings/notifications` → Notification config ❌

---

#### 2. TRF Management ⚠ PARTIAL
**Location:** `frontend/src/app/features/trf-management/`

**Completed:**
- ✅ TRF list component
- ⚠ TRF create component (wizard pattern started)
- ⚠ Domestic travel details component
- ⚠ Requestor information component

**Missing:**
- ❌ TRF view/detail component
- ❌ TRF edit component
- ❌ Overseas travel form
- ❌ Home leave passage form
- ❌ External parties form
- ❌ Itinerary builder
- ❌ Passport details form
- ❌ Bank details form
- ❌ Accommodation preferences
- ❌ Approval tracking UI
- ❌ Document attachments
- ❌ TRF history/audit trail

**Source Pages to Migrate:**
- `trf/` → TRF list ⚠
- `trf/new` → TRF type selection ⚠
- `trf/new/domestic` → Domestic TRF form ⚠
- `trf/new/overseas` → Overseas TRF form ❌
- `trf/new/home-leave` → Home Leave form ❌
- `trf/new/external-parties` → External Parties form ❌
- `trf/view/[trfId]` → TRF detail view ❌

---

#### 3. Visa Module ⚠ PARTIAL
**Location:** `frontend/src/app/visa/`

**Completed:**
- ⚠ Basic service for API calls

**Missing:**
- ❌ Visa list component
- ❌ Visa application form
- ❌ Visa detail view
- ❌ Visa edit component
- ❌ Document upload UI
- ❌ Approval status tracking
- ❌ Visa routing module

**Source Pages to Migrate:**
- `visa/` → Visa list ❌
- `visa/new` → Visa application form ❌
- `visa/view/[visaId]` → Visa detail ❌
- `visa/edit/[visaId]` → Visa edit ❌

---

#### 4. Accommodation Requests ⚠ PARTIAL
**Location:** `frontend/src/app/features/requests/accommodation/`

**Completed:**
- ⚠ Basic request form structure

**Missing:**
- ❌ Accommodation list/history
- ❌ Room availability calendar
- ❌ Staff house selection
- ❌ Room type preferences
- ❌ Date range picker
- ❌ Request detail view
- ❌ Request edit
- ❌ Booking confirmation
- ❌ Check-in/check-out flow

**Source Pages to Migrate:**
- `accommodation/` → Accommodation list ❌
- `accommodation/request` → New request form ⚠
- `accommodation/view/[requestId]` → Request detail ❌
- `accommodation/edit/[requestId]` → Edit request ❌

---

#### 5. Expense Claims ⚠ PARTIAL
**Location:** `frontend/src/app/features/expense-claims/`

**Completed:**
- ⚠ Basic expense create form

**Missing:**
- ❌ Claims list component
- ❌ Claim detail view
- ❌ Claim edit component
- ❌ Expense items table
- ❌ FX rates calculator
- ❌ Receipt upload
- ❌ Medical claim form
- ❌ Claim summary calculations
- ❌ Approval tracking
- ❌ Link to TRF

**Source Pages to Migrate:**
- `claims/` → Claims list ❌
- `claims/new` → New claim form ⚠
- `claims/view/[claimId]` → Claim detail ❌
- `claims/edit/[claimId]` → Edit claim ❌

---

#### 6. Transport Requests ❌ NOT STARTED
**Location:** `frontend/src/app/` (needs creation)

**Required:**
- ❌ Transport list component
- ❌ Transport request form
- ❌ Transport detail view
- ❌ Transport edit component
- ❌ Route/itinerary builder
- ❌ Vehicle type selection
- ❌ Date/time scheduling
- ❌ Passenger management
- ❌ Cost estimation
- ❌ Approval tracking

**Source Pages to Migrate:**
- `transport/` → Transport list ❌
- `transport/new` → New request form ❌
- `transport/view/[transportId]` → Request detail ❌
- `transport/edit/[transportId]` → Edit request ❌

---

#### 7. Notifications ❌ NOT STARTED
**Location:** `frontend/src/app/` (needs creation)

**Required:**
- ❌ Notifications list component
- ❌ Notification bell/badge in header
- ❌ Notification preferences page
- ❌ Real-time notification updates
- ❌ Mark as read/unread
- ❌ Notification filters
- ❌ Email notification settings

**Source Pages to Migrate:**
- `notifications/` → Notifications page ❌
- Header notification bell integration ❌

---

#### 8. Reports/Analytics ❌ NOT STARTED
**Location:** `frontend/src/app/` (needs creation)

**Required:**
- ❌ Reports dashboard
- ❌ Travel statistics
- ❌ Expense analytics
- ❌ Department-wise reports
- ❌ User activity reports
- ❌ Export to PDF/Excel
- ❌ Chart visualizations
- ❌ Date range filters

**Source Pages to Migrate:**
- `reports/` → Reports dashboard ❌

---

#### 9. Profile ❌ NOT STARTED
**Location:** `frontend/src/app/` (needs creation)

**Required:**
- ❌ User profile page
- ❌ Profile edit form
- ❌ Password change
- ❌ Notification preferences
- ❌ Avatar upload
- ❌ Activity history

**Source Pages to Migrate:**
- `profile/` → User profile ❌

---

#### 10. Shared Components ✅ MOSTLY COMPLETE
**Location:** `frontend/src/app/shared/components/`

**Completed:**
- ✅ Header component
- ✅ Sidebar component
- ✅ Main layout

**Missing:**
- ❌ Notification bell component
- ❌ User avatar component
- ❌ Breadcrumbs
- ❌ Loading indicators
- ❌ Error pages
- ❌ Confirmation dialogs
- ❌ Data tables
- ❌ Date pickers
- ❌ File upload component

---

## Database Schema

### Fully Migrated Tables ✅
- `users`
- `roles`
- `permissions`
- `role_permissions`
- `visa_applications`
- `visa_approval_steps`
- `visa_documents`
- `accommodation_staff_houses`
- `accommodation_rooms`
- `accommodation_bookings`

### Partially Migrated Tables ⚠
- `travel_requests` (basic structure only)
- `expense_claims` (basic structure only)

### Not Yet Migrated Tables ❌
- `trf_itinerary_segments`
- `trf_accommodation_details`
- `trf_advance_bank_details`
- `trf_passport_details`
- `trf_approval_steps`
- `transport_requests`
- `transport_details`
- `transport_approval_steps`
- `expense_claim_items`
- `expense_claim_fx_rates`
- `claims_approval_steps`
- `flight_bookings`
- `workflow_templates`
- `workflow_steps`
- `workflow_instances`
- `workflow_step_executions`
- `workflow_conditions`
- `workflow_delegations`
- `workflow_audit_log`
- `notification_event_types`
- `notification_templates`
- `notification_user_subscriptions`
- `user_notification_preferences`
- `user_notifications`

---

## Next Steps

### High Priority (Week 1-2)
1. **Transport Module** - Complete backend (models, serializers, views, URLs)
2. **Complete TRF Module** - Add all related models (itinerary, passport, bank details)
3. **Complete Accommodation Module** - Add serializers, views, and URLs
4. **Complete Expenses Module** - Add items, FX rates, and approval workflow

### Medium Priority (Week 3-4)
5. **Workflows Module** - Implement generic approval workflow system
6. **Notifications Module** - Implement notification system
7. **Frontend: Transport UI** - Build transport request forms and lists
8. **Frontend: TRF Forms** - Complete all TRF form types

### Lower Priority (Week 5-6)
9. **Frontend: Admin Panels** - Build all admin processing interfaces
10. **Frontend: Reports** - Build analytics and reporting UI
11. **Frontend: Notifications** - Build notification UI and real-time updates
12. **Testing & Integration** - End-to-end testing of all modules

### Migration Priority Order
1. ✅ Accounts/Authentication (DONE)
2. ✅ Visa Module (DONE)
3. 🔄 Transport Module (IN PROGRESS - NEXT)
4. 🔄 Accommodation Module (IN PROGRESS)
5. 🔄 TRF Module (IN PROGRESS)
6. 🔄 Expenses/Claims Module (IN PROGRESS)
7. ⏳ Workflows Module
8. ⏳ Notifications Module
9. ⏳ Bookings/Flights Module
10. ⏳ Reports/Insights Module

---

## Key Features Not Yet Migrated

### Backend
- [ ] Complete TRF approval workflow with auto-TSR generation
- [ ] Transport request system
- [ ] Generic workflow engine
- [ ] Notification system (email + in-app)
- [ ] Flight booking integration
- [ ] Reports and analytics endpoints
- [ ] Document management system
- [ ] Audit logging
- [ ] Delegation system

### Frontend
- [ ] All admin processing panels
- [ ] Transport request UI
- [ ] Complete TRF form wizard (all types)
- [ ] Notification center with real-time updates
- [ ] Reports dashboard
- [ ] User profile management
- [ ] Advanced search and filters
- [ ] Export functionality
- [ ] Calendar views for bookings
- [ ] Document preview/download

---

## Migration Notes

### Architecture Changes
- **Authentication:** Migrated from NextAuth to Django Rest Framework JWT
- **API:** REST endpoints instead of Next.js API routes
- **State Management:** Angular services instead of React Context
- **Forms:** Angular Reactive Forms instead of React Hook Form
- **UI Components:** Angular Material instead of Radix UI
- **Styling:** Maintained but adapted for Angular

### Data Model Changes
- UUIDs remain consistent (PostgreSQL gen_random_uuid())
- Foreign key relationships maintained
- Timestamps use Django's auto_now/auto_now_add
- JSON fields for flexible data storage

### API Endpoint Structure
```
Source (Next.js):          Target (Django):
/api/trf                   /api/trf/
/api/visa/[id]             /api/visa/{id}/
/api/admin/users           /api/accounts/users/
```

---

**Migration Progress: ~25% Complete**

**Estimated Completion:** 4-6 weeks with focused development
