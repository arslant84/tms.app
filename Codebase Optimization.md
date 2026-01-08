# TMS Application - Codebase Optimization Roadmap

**Last Updated**: 2026-01-09
**Project**: Travel Management System (TMS)
**Stack**: Angular 19.2 (Frontend) + Django 5.0.2 (Backend)
**Status**: Initial Assessment Complete ✅

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current Architecture Overview](#current-architecture-overview)
3. [Baseline Metrics](#baseline-metrics)
4. [Issue Severity Matrix](#issue-severity-matrix)
5. [Optimization Phases](#optimization-phases)
6. [Quick Wins (Top 5)](#quick-wins-top-5)
7. [Detailed Task Breakdown](#detailed-task-breakdown)
8. [Constraints & Guidelines](#constraints--guidelines)
9. [Progress Tracking](#progress-tracking)

---

## Executive Summary

The TMS application is a well-architected full-stack system with **sophisticated workflow and notification capabilities**. However, it suffers from:

### Critical Issues (Must Fix)
- ❌ Service duplication across frontend (core vs features)
- ❌ Model duplication in backend (TrfFlightBooking vs FlightBooking)
- ❌ Security guards disabled in frontend (dev bypasses not removed)
- ❌ Test files scattered in backend root (not discoverable)
- ❌ Incomplete modules (approvals, reports apps are stubs)

### Major Improvements Needed
- 🔧 Backend app consolidation (9 apps → 4-5 feature-based)
- 🔧 Frontend shared module non-functional
- 🔧 Root directory cleanup (14 cleanup scripts, 14 MD files)
- 🔧 Workflow-notification coupling issues
- 🔧 Signal handler duplication across apps

### Strengths to Preserve
- ✅ Modern tech stack (Angular 19, Django 5)
- ✅ Comprehensive RBAC/permission system
- ✅ Lazy loading implemented
- ✅ Environment-based configuration
- ✅ Clean dependency management

---

## Current Architecture Overview

```
tms-app/
├── backend/                          # Django 5.0.2
│   ├── tms_project/                  # Project configuration
│   ├── accounts/                     # User auth, roles, permissions
│   ├── trf/                          # Travel Request Forms
│   ├── transport/                    # Transport requests
│   ├── accommodation/                # Accommodation management
│   ├── visa/                         # Visa processing
│   ├── bookings/                     # Flight/hotel bookings
│   ├── workflows/                    # Workflow engine
│   ├── notifications/                # Notification system
│   ├── insights/                     # Analytics (minimal)
│   ├── reports/                      # Reporting (stub)
│   ├── approvals/                    # Approval views (incomplete)
│   ├── core/                         # Utilities
│   ├── utils/                        # Helper utilities
│   ├── [14 cleanup scripts]          # ⚠️ In root, needs organization
│   ├── [14 documentation files]      # ⚠️ In root, needs organization
│   └── [4 test files]                # ⚠️ In root, not discoverable
│
└── frontend/                         # Angular 19.2
    ├── src/app/
    │   ├── core/                     # Services, guards, models
    │   ├── shared/                   # ⚠️ Empty module
    │   ├── components/               # Layout components
    │   └── features/                 # Feature modules
    │       ├── auth/
    │       ├── dashboard/
    │       ├── trf-management/
    │       ├── transport/
    │       ├── accommodation/
    │       ├── visa/
    │       ├── bookings/
    │       ├── notifications/
    │       ├── user-management/
    │       └── admin/                # 26+ subdirectories
    ├── environments/
    └── public/
```

---

## Baseline Metrics

### Backend Statistics
| Metric | Count | Notes |
|--------|-------|-------|
| Django Apps | 9 core + 3 utility | Should consolidate to 4-5 |
| Python Files | 198 | Excluding venv/cache |
| Model Classes | 40+ | 102 relationships |
| ViewSets | 25+ | Mostly ModelViewSet |
| Test Files | 4 | ⚠️ In root, not organized |
| Cleanup Scripts | 14 | ⚠️ In root, unclear status |
| Documentation Files | 14 MD | ⚠️ Mix of current/historical |
| Code Lines (models only) | ~2,082 | Significant complexity |

### Frontend Statistics
| Metric | Count | Notes |
|--------|-------|-------|
| TypeScript Files | 165 | |
| Feature Modules | 10 | Well-structured |
| Core Services | 24 | ⚠️ Some duplicated in features |
| Feature Services | 9 | ⚠️ Overlap with core |
| Components | 69+ | Admin has 26+ subdirs |
| SCSS Files | 77 | |
| Lazy-loaded Routes | 8 | Good implementation |

### Dependencies
**Frontend:**
- Angular: 19.2.0 ✅ (latest)
- Bootstrap: 5.3.6 ✅
- RxJS: 7.8.0 ✅
- TypeScript: 5.7.2 ✅

**Backend:**
- Django: 4.2.0+ ✅
- DRF: 3.14.0+ ✅
- PostgreSQL: psycopg2-binary ✅
- JWT: djangorestframework-simplejwt ✅

---

## Issue Severity Matrix

### Critical (Must Fix Before Production)
| # | Issue | Impact | Location | Effort | Status |
|---|-------|--------|----------|--------|--------|
| C1 | Security guards disabled | Security breach risk | frontend/core/guards | 1-2h | ✅ FIXED |
| C2 | Hardcoded API URLs | Environment-specific issues | frontend/core/services/auth.service.ts | 30m | ✅ FIXED |
| C3 | Model duplication (Flight Booking) | Data inconsistency | backend/trf & bookings | 4-6h | Pending |
| C4 | Test files not discoverable | No test coverage validation | backend/*.py | 2-3h | ✅ FIXED |
| C5 | Incomplete approvals module | Broken functionality | backend/approvals | 8-12h | Pending |

### High Priority (Significant Technical Debt)
| # | Issue | Impact | Location | Effort | Status |
|---|-------|--------|----------|--------|--------|
| H1 | Service duplication (Frontend) | Confusion, maintenance burden | frontend/core + features | 4-6h | Pending |
| H2 | Signal handler duplication | Code duplication, hard to maintain | backend/*/signals.py | 3-4h | Pending |
| H3 | Root directory cleanup | Code organization, professionalism | backend/*.py, *.md | 2-3h | ✅ FIXED |
| H4 | Shared module non-functional | Cannot reuse components | frontend/shared | 2-3h | Pending |
| H5 | Workflow-notification coupling | Architectural issue | backend/workflows + notifications | 6-8h | Pending |
| H6 | App consolidation needed | Maintainability | backend apps | 16-24h | Pending |
| H7 | Admin module bloat | Navigation complexity | frontend/features/admin | 6-8h | Pending |

### Medium Priority (Improvements)
| # | Issue | Impact | Location | Effort |
|---|-------|--------|----------|--------|
| M1 | Missing reports implementation | Incomplete feature | backend/reports | 12-16h |
| M2 | Insights app minimal | Incomplete feature | backend/insights | 12-16h |
| M3 | Mixed component strategies | Inconsistent patterns | frontend (global) | 8-12h |
| M4 | No barrel exports | Import path complexity | frontend (global) | 4-6h |
| M5 | Limited test coverage | Quality assurance gaps | backend + frontend | Ongoing |
| M6 | Documentation gaps | Developer onboarding | Global | Ongoing |

### Low Priority (Nice to Have)
| # | Issue | Impact | Location | Effort |
|---|-------|--------|----------|--------|
| L1 | Naming inconsistencies | Minor readability | Global | 2-4h |
| L2 | Missing JSDoc comments | Documentation | Frontend | Ongoing |
| L3 | Empty artifact files | Clutter | frontend/visa | 5m |
| L4 | Type safety bypasses ('any') | Type checking | Frontend | 2-3h |

---

## Optimization Phases

### Phase 1: Critical Fixes & Setup (Days 1-3) ✅ CURRENT PHASE
**Goal**: Fix critical issues, setup tooling, quick wins

**Day 1: Assessment & Roadmap**
- [x] Complete codebase analysis
- [x] Create comprehensive roadmap
- [ ] Add code quality tools (ESLint, Prettier, Husky)
- [ ] Create .env.example for both projects
- [ ] Update .gitignore files

**Day 2: Security & Configuration**
- [ ] Fix frontend security guards (C1)
- [ ] Remove hardcoded API URLs (C2)
- [ ] Split backend requirements (base/dev/prod)
- [ ] Configure environment-based settings
- [ ] Add proper logging configuration

**Day 3: Test Organization & Cleanup**
- [ ] Move test files to proper structure (C4)
- [ ] Organize cleanup scripts into management/commands
- [ ] Archive historical documentation
- [ ] Remove dead code and unused imports
- [ ] Delete empty artifact files (L3)

**Deliverables:**
- ✅ ROADMAP.md created and maintained
- Working development environment setup
- Fixed security vulnerabilities
- Organized test structure

---

### Phase 2: Backend Restructuring (Days 4-10)
**Goal**: Consolidate apps, improve architecture, resolve duplication

**Days 4-5: Model Consolidation**
- [ ] Merge TrfFlightBooking and FlightBooking models (C3)
- [ ] Update foreign key references
- [ ] Create data migration scripts
- [ ] Test booking functionality end-to-end

**Days 6-7: Signal Handler Consolidation**
- [ ] Create base workflow trigger handler (H2)
- [ ] Refactor trf/signals.py to use base handler
- [ ] Refactor transport/signals.py to use base handler
- [ ] Refactor visa/signals.py to use base handler
- [ ] Refactor accommodation/signals.py to use base handler
- [ ] Remove duplicate signal code

**Days 8-9: App Structure Reorganization**
- [ ] Plan app consolidation strategy (H6)
- [ ] Create new app structure in apps/ directory
- [ ] Create migration plan for models
- [ ] Update INSTALLED_APPS in settings

**Day 10: Settings Optimization**
- [ ] Split settings into base/dev/prod
- [ ] Move tms_project to config/
- [ ] Optimize DATABASE settings (connection pooling)
- [ ] Add caching configuration (Redis recommended)
- [ ] Configure production-ready middleware

**Deliverables:**
- Consolidated backend apps (9 → 4-5)
- No duplicate models or signals
- Production-ready settings structure
- Improved code maintainability

---

### Phase 3: Frontend Restructuring (Days 11-17)
**Goal**: Resolve duplication, improve performance, standardize patterns

**Days 11-12: Service Consolidation**
- [ ] Audit all service duplications (H1)
- [ ] Remove core/services/accommodation.service.ts (use feature version)
- [ ] Consolidate trf services
- [ ] Consolidate user services
- [ ] Update all imports across components
- [ ] Test all API integrations

**Days 13-14: Shared Module & Component Strategy**
- [ ] Decide: Full standalone or hybrid approach (H4)
- [ ] Implement SharedModule properly OR migrate all to standalone
- [ ] Move shared components to proper exports
- [ ] Standardize component patterns across app
- [ ] Update imports in all feature modules

**Days 15-16: Admin Module Refactoring**
- [ ] Analyze admin subdirectories (26+) (H7)
- [ ] Group by domain (flights, transport, accommodation, visa, system)
- [ ] Create unified admin base component
- [ ] Implement role-based views
- [ ] Simplify routing structure

**Day 17: Performance Optimization**
- [ ] Add bundle analyzer to package.json
- [ ] Implement OnPush change detection where applicable
- [ ] Optimize RxJS subscriptions (takeUntil pattern)
- [ ] Remove unused styles and assets
- [ ] Add lazy loading for remaining routes

**Deliverables:**
- No service duplication
- Clear component strategy (standalone or hybrid)
- Optimized admin module
- Improved bundle size and performance

---

### Phase 4: Integration & Polish (Days 18-24)
**Goal**: Standardize APIs, improve error handling, add testing

**Days 18-19: API Standardization**
- [ ] Standardize API response format across all endpoints
- [ ] Add pagination to all list endpoints
- [ ] Add filtering and search capabilities
- [ ] Implement proper error responses
- [ ] Add request/response logging

**Days 20-21: Authentication Flow**
- [ ] Implement JWT token refresh mechanism
- [ ] Add automatic token renewal before expiration
- [ ] Standardize auth guard implementation
- [ ] Test role-based access control
- [ ] Document authentication flows

**Days 22-23: Complete Stub Modules**
- [ ] Implement reports module or remove (C5, M1)
- [ ] Implement insights module or remove (M2)
- [ ] Implement approvals module properly (C5)
- [ ] Add proper serializers and viewsets
- [ ] Create frontend components for new endpoints

**Day 24: Documentation & Testing**
- [ ] Add README.md with setup instructions
- [ ] Create ARCHITECTURE.md documenting decisions
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Write integration tests for critical flows
- [ ] Update roadmap with final status

**Deliverables:**
- Standardized API responses
- Complete authentication flow
- No stub modules remaining
- Comprehensive documentation

---

## Quick Wins (Top 5)

These can be done immediately with minimal risk:

### 1. Fix Security Guards (30 minutes) - CRITICAL ⚠️
**Issue**: AuthGuard and isAuthenticated() always return true
**Impact**: No authentication enforcement
**Files**:
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/services/auth.service.ts`

**Current Code**:
```typescript
// auth.guard.ts - CURRENTLY BYPASSED
return true;  // Always allows access!

// auth.service.ts - CURRENTLY BYPASSED
isAuthenticated(): Observable<boolean> {
  return of(true);  // Always authenticated!
}
```

**Fixed Code**:
```typescript
// auth.guard.ts
canActivate(
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
): Observable<boolean> {
  return this.authService.isAuthenticated().pipe(
    tap(isAuth => {
      if (!isAuth) {
        this.router.navigate(['/auth/login'], {
          queryParams: { returnUrl: state.url }
        });
      }
    })
  );
}

// auth.service.ts
isAuthenticated(): Observable<boolean> {
  const token = localStorage.getItem('authToken');
  if (!token) {
    return of(false);
  }

  // Validate token expiry
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const isExpired = Date.now() >= payload.exp * 1000;

    if (isExpired) {
      this.logout(); // Clear expired token
      return of(false);
    }

    return of(true);
  } catch (error) {
    console.error('Invalid token format', error);
    this.logout();
    return of(false);
  }
}
```

**Testing**:
1. Logout and try to access `/dashboard` - should redirect to login
2. Login and verify token stored
3. Access protected routes - should work
4. Clear localStorage and refresh - should redirect to login

**Roadmap Update**: Mark C1 as ✅ complete

---

### 2. Remove Hardcoded API URL (15 minutes) - CRITICAL ⚠️
**Issue**: API URL hardcoded in auth.service.ts
**Impact**: Cannot switch environments
**Files**: `frontend/src/app/core/services/auth.service.ts`

**Current Code**:
```typescript
// Hardcoded!
const API_URL = 'http://localhost:8000';
```

**Fixed Code**:
```typescript
// environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api'
};

// environment.production.ts
export const environment = {
  production: true,
  apiUrl: 'https://api.tms-production.com/api'
};

// auth.service.ts
import { environment } from '../../../environments/environment';

export class AuthService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  login(credentials: LoginCredentials): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.apiUrl}/login/`, credentials);
  }
}
```

**Testing**:
1. Verify login/logout still work
2. Check network tab - requests go to correct URL
3. Try building for production - should use production URL

**Roadmap Update**: Mark C2 as ✅ complete

---

### 3. Move Test Files to Proper Structure (1 hour) - CRITICAL ⚠️
**Issue**: 4 test files in backend root, not discoverable by Django test runner
**Impact**: Tests not run by CI/CD
**Files**:
- `backend/test_notification_templates.py`
- `backend/test_workflow_notifications_integration.py`
- `backend/test_complete_notification.py`
- `backend/test_email_fix.py`

**Action Steps**:
```bash
# 1. Create tests directory structure
cd backend
mkdir -p tests/notifications
mkdir -p tests/workflows

# 2. Add __init__.py files
touch tests/__init__.py
touch tests/notifications/__init__.py
touch tests/workflows/__init__.py

# 3. Move test files
mv test_notification_templates.py tests/notifications/
mv test_complete_notification.py tests/notifications/
mv test_email_fix.py tests/notifications/
mv test_workflow_notifications_integration.py tests/workflows/

# 4. Update imports in test files (if needed)
# Change: from notifications.models import ...
# To: from backend.notifications.models import ...
```

**Testing**:
```bash
# Run Django test discovery
python manage.py test

# Should output:
# Found X test(s)
# Running tests...
```

**Roadmap Update**: Mark C4 as ✅ complete

---

### 4. Organize Cleanup Scripts (45 minutes) - HIGH PRIORITY
**Issue**: 14 cleanup scripts cluttering backend root
**Impact**: Unclear which are active, hard to maintain
**Files**: `backend/*.py` (audit, check, fix, convert scripts)

**Action Steps**:
```bash
cd backend

# 1. Create archive directory for one-time scripts
mkdir -p _archived_scripts

# 2. Create management commands directory for active scripts
mkdir -p core/management/commands

# 3. Identify and move one-time scripts (already executed)
mv audit_all_users_permissions.py _archived_scripts/
mv convert_workflows_to_permissions_v2.py _archived_scripts/
mv fix_unassigned_workflow_steps.py _archived_scripts/

# 4. Convert active scripts to Django management commands
# Example: check_notifications.py → core/management/commands/check_notifications.py
```

**Example Management Command**:
```python
# core/management/commands/check_notifications.py
from django.core.management.base import BaseCommand
from notifications.models import UserNotification

class Command(BaseCommand):
    help = 'Check notification system status'

    def handle(self, *args, **options):
        count = UserNotification.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Found {count} notifications')
        )
```

**Usage**: `python manage.py check_notifications`

**Testing**: Verify imports not broken, management commands work
**Roadmap Update**: Mark H3 as ✅ complete

---

### 5. Delete Empty Artifact File (5 minutes) - LOW PRIORITY
**Issue**: Empty artifact file from accidental creation
**Impact**: Clutter in codebase
**File**: `frontend/src/app/features/visa/visa-list/srcappvisavisa-listvisa-list.component.ts`

**Action**:
```bash
cd frontend/src/app/features/visa/visa-list
rm srcappvisavisa-listvisa-list.component.ts

# Verify no imports reference this file
grep -r "srcappvisavisa-listvisa-list" ../../../
```

**Testing**:
```bash
# Run build to ensure no errors
cd frontend
ng build --configuration production
```

**Roadmap Update**: Mark L3 as ✅ complete

---

## Detailed Task Breakdown

### Backend Tasks

#### B1: Split Requirements File ⏸️ Phase 1 Day 2
**Current State**: Single `requirements.txt` with all dependencies
**Target State**: Split into base/dev/prod for better environment management

**Implementation**:
```bash
# 1. Create requirements directory
mkdir backend/requirements

# 2. Create base.txt (production dependencies)
cat > backend/requirements/base.txt << 'EOF'
Django>=4.2.0
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.3.0
django-cors-headers>=4.0.0
psycopg2-binary>=2.9.6
python-jose>=3.3.0
passlib>=1.7.4
python-multipart>=0.0.5
python-decouple>=3.8
django-ratelimit>=4.1.0
pytz>=2024.1
EOF

# 3. Create development.txt
cat > backend/requirements/development.txt << 'EOF'
-r base.txt

# Development tools
django-debug-toolbar>=4.2.0
django-extensions>=3.2.3
ipython>=8.12.0

# Testing
pytest-django>=4.5.2
pytest-cov>=4.1.0
factory-boy>=3.3.0
faker>=19.12.0
EOF

# 4. Create production.txt
cat > backend/requirements/production.txt << 'EOF'
-r base.txt

# Production server
gunicorn>=21.2.0
whitenoise>=6.5.0

# Monitoring
sentry-sdk>=1.32.0

# Caching
redis>=5.0.0
django-redis>=5.3.0
hiredis>=2.2.3
EOF

# 5. Update README with new install instructions
```

**Install commands**:
```bash
# Development
pip install -r requirements/development.txt

# Production
pip install -r requirements/production.txt
```

**Testing**: Create fresh venv and install dev requirements
**Roadmap Update**: Mark B1 as ✅ complete

---

#### B2: Consolidate Signal Handlers ⏸️ Phase 2 Days 6-7
**Current State**: 4 apps have duplicate signal logic for workflow creation
**Target State**: Single base handler, reused across apps

**Step 1 - Create Base Handler**:
```python
# backend/workflows/signals_base.py
from django.db.models.signals import post_save
from .models import WorkflowTemplate
import logging

logger = logging.getLogger(__name__)

def create_workflow_trigger(sender, instance, created, workflow_type, **kwargs):
    """
    Generic workflow trigger handler.

    Creates a workflow instance when a new request is created,
    if an active workflow template exists for that type.

    Args:
        sender: Model class that triggered the signal
        instance: Created model instance
        created: Boolean indicating if newly created
        workflow_type: String identifier (trf, transport, visa, accommodation)
    """
    if not created:
        return

    try:
        template = WorkflowTemplate.objects.get(
            entity_type=workflow_type,
            is_active=True
        )

        from .services import WorkflowService
        WorkflowService.create_instance_from_template(
            template=template,
            entity_object=instance
        )

        logger.info(
            f"Created workflow instance for {workflow_type} #{instance.id}"
        )

    except WorkflowTemplate.DoesNotExist:
        logger.debug(
            f"No active workflow template for {workflow_type}"
        )
    except WorkflowTemplate.MultipleObjectsReturned:
        logger.error(
            f"Multiple active workflow templates found for {workflow_type}"
        )
    except Exception as e:
        logger.error(
            f"Error creating workflow for {workflow_type} #{instance.id}: {e}"
        )
```

**Step 2 - Update TRF Signals**:
```python
# backend/trf/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.signals_base import create_workflow_trigger
from .models import TravelRequest

@receiver(post_save, sender=TravelRequest)
def create_trf_workflow(sender, instance, created, **kwargs):
    """Trigger workflow creation for new travel requests."""
    create_workflow_trigger(
        sender=sender,
        instance=instance,
        created=created,
        workflow_type='trf',
        **kwargs
    )
```

**Step 3 - Repeat for Other Apps**:
- `backend/transport/signals.py` - workflow_type='transport'
- `backend/visa/signals.py` - workflow_type='visa'
- `backend/accommodation/signals.py` - workflow_type='accommodation'

**Testing**:
1. Create new TRF → verify workflow created
2. Create new transport request → verify workflow created
3. Check logs for proper logging
4. Test when no template exists → should not error

**Metrics**: Removes ~120 lines of duplicate code
**Roadmap Update**: Mark H2 as ✅ complete

---

#### B3: Merge Flight Booking Models ⏸️ Phase 2 Days 4-5
**Current State**: Two models for same concept
- `TrfFlightBooking` in trf app
- `FlightBooking` in bookings app

**Analysis Needed**: Compare field definitions first

**Step 1 - Compare Models**:
```bash
# Read both model definitions
cat backend/trf/models.py | grep -A 50 "class TrfFlightBooking"
cat backend/bookings/models.py | grep -A 50 "class FlightBooking"
```

**Step 2 - Create Migration Strategy**:
1. Identify field differences
2. Choose which model to keep (likely `bookings.FlightBooking`)
3. Add missing fields to chosen model
4. Create data migration to copy data
5. Update ForeignKey references
6. Delete deprecated model

**Note**: This is a complex task requiring careful analysis
**Will be detailed when Phase 2 begins**

**Roadmap Update**: Mark C3 as ✅ complete when done

---

### Frontend Tasks

#### F1: Consolidate Duplicate Services ⏸️ Phase 3 Days 11-12
**Current State**: Services exist in both core and features
**Target State**: Single source of truth

**Services to Audit**:
1. AccommodationService - core vs features/accommodation
2. TrfService - core vs features/trf-management
3. UserService - core vs features/user-management

**Strategy**:
- **Keep in core**: Generic/reusable services (auth, http, rbac)
- **Keep in features**: Feature-specific business logic
- **Rule**: If used by multiple features → core. If feature-specific → feature.

**Implementation for Accommodation**:
```bash
# 1. Compare services
diff frontend/src/app/core/services/accommodation.service.ts \
     frontend/src/app/features/accommodation/services/accommodation.service.ts

# 2. Decision: Feature version is HTTP-based, core is mock
# Keep feature version, remove core version

rm frontend/src/app/core/services/accommodation.service.ts

# 3. Update imports (search and replace)
# From: import { AccommodationService } from '../../../core/services/accommodation.service'
# To: import { AccommodationService } from '../../accommodation/services/accommodation.service'
```

**Testing**: Test all accommodation features thoroughly
**Roadmap Update**: Mark H1 partially complete (repeat for each service)

---

#### F2: Fix Shared Module ⏸️ Phase 3 Days 13-14
**Current State**: SharedModule exists but empty, unusable
**Target State**: Either properly implemented OR fully standalone

**Decision Required**: Choose ONE approach

**Option A: Traditional Module** (if keeping traditional modules)
```typescript
// frontend/src/app/shared/shared.module.ts
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

import { ToastContainerComponent } from './components/toast-container/toast-container.component';
import { ConfirmationDialogComponent } from './components/confirmation-dialog/confirmation-dialog.component';
import { DeleteConfirmComponent } from './components/delete-confirm/delete-confirm.component';
import { ApprovalActionsComponent } from './components/approval-actions/approval-actions.component';
import { WorkflowStatusComponent } from './components/workflow-status/workflow-status.component';

@NgModule({
  declarations: [
    ToastContainerComponent,
    ConfirmationDialogComponent,
    DeleteConfirmComponent,
    ApprovalActionsComponent,
    WorkflowStatusComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NgbModule
  ],
  exports: [
    // Re-export common modules
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    // Export components
    ToastContainerComponent,
    ConfirmationDialogComponent,
    DeleteConfirmComponent,
    ApprovalActionsComponent,
    WorkflowStatusComponent
  ]
})
export class SharedModule { }
```

**Option B: Standalone Components** (recommended for Angular 19+)
```typescript
// Each component becomes standalone
@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule, NgbModule],
  templateUrl: './toast-container.component.html',
  styleUrls: ['./toast-container.component.scss']
})
export class ToastContainerComponent { }

// Usage in other components
import { ToastContainerComponent } from '../../../shared/components/toast-container/toast-container.component';

@Component({
  standalone: true,
  imports: [CommonModule, ToastContainerComponent],
  // ...
})
```

**Recommendation**: Go with **Option B (Standalone)** - aligns with Angular 19 best practices

**Testing**: Verify all components still work in their feature modules
**Roadmap Update**: Mark H4 as ✅ complete

---

## Constraints & Guidelines

### Code Quality Rules
1. ✅ **Don't delete files immediately** - Move to `_deprecated/` first, delete after 1 sprint
2. ✅ **Small focused commits** - One feature/fix per commit
3. ✅ **Add TypeScript interfaces** for all API responses
4. ✅ **Use environment variables** for all configuration (no hardcoded values)
5. ✅ **Add comprehensive logging** (Django logging + conditional frontend console)
6. ✅ **Document architectural decisions** in ARCHITECTURE.md
7. ✅ **Create migration scripts** for all schema changes
8. ✅ **Add unit tests** for new functionality (target: 70%+ coverage)
9. ✅ **Update API docs** for changed endpoints (use drf-spectacular)
10. ✅ **Verify existing functionality** after each change

### Testing Requirements
- **Backend**: Run `python manage.py test` after each change
- **Frontend**: Run `ng build --configuration production` to verify no errors
- **Integration**: Test critical user flows manually
- **Regression**: Maintain list of test scenarios for each module

### Git Workflow
```bash
# Feature branch naming
git checkout -b refactor/consolidate-services
git checkout -b fix/security-guards
git checkout -b docs/update-roadmap

# Commit message format
git commit -m "refactor(backend): consolidate signal handlers

- Create base workflow trigger in workflows/signals_base.py
- Update trf, transport, visa, accommodation signals to use base
- Remove 120 lines of duplicate code
- Add tests for workflow trigger logic

Closes #123"
```

### Documentation Standards
- Update this ROADMAP.md after completing each major task
- Add inline comments for complex business logic
- Create/update README.md in each app/feature
- Maintain ARCHITECTURE.md with decisions and diagrams

---

## Progress Tracking

### Phase 1: Critical Fixes & Setup (Days 1-3) ✅ MOSTLY COMPLETE
**Progress**: 83% complete (10/12 tasks)

- [x] Complete codebase analysis
- [x] Create comprehensive roadmap
- [x] Add code quality tools (ESLint, Prettier) ✅ COMPLETED
- [x] Create .env.example files ✅ COMPLETED
- [x] Update .gitignore files ✅ COMPLETED
- [x] Fix frontend security guards (C1) ✅ COMPLETED
- [x] Remove hardcoded API URLs (C2) ✅ COMPLETED
- [x] Split backend requirements (B1) ✅ COMPLETED
- [x] Move test files to proper structure (C4) ✅ COMPLETED
- [x] Organize cleanup scripts (H3) ✅ COMPLETED
- [ ] Remove dead code and unused imports (deferred to Phase 2)
- [ ] Delete empty artifact files (L3) (none found)

**Next Actions**: Phase 1 substantially complete! Ready for Phase 2 or Phase 3

---

### Phase 2: Backend Restructuring (Days 4-10) ⏸️ NOT STARTED
**Progress**: 0% (0/15 tasks)

- [ ] Merge flight booking models (C3)
- [ ] Create data migration
- [ ] Consolidate signal handlers (H2)
- [ ] Plan app consolidation (H6)
- [ ] Create new app structure
- [ ] Migrate models to new apps
- [ ] Split settings (base/dev/prod)
- [ ] Move tms_project to config/
- [ ] Add database connection pooling
- [ ] Configure caching (Redis)
- [ ] Update INSTALLED_APPS
- [ ] Update all imports
- [ ] Test all endpoints
- [ ] Update documentation
- [ ] Deploy and verify

**Dependencies**: Phase 1 must complete first

---

### Phase 3: Frontend Restructuring (Days 11-17) ⏸️ NOT STARTED
**Progress**: 0% (0/12 tasks)

- [ ] Audit service duplications (H1)
- [ ] Consolidate services
- [ ] Update imports
- [ ] Fix shared module (H4)
- [ ] Refactor admin module (H7)
- [ ] Implement bundle analyzer
- [ ] Add OnPush change detection
- [ ] Optimize RxJS patterns
- [ ] Remove unused assets
- [ ] Test all features
- [ ] Measure performance
- [ ] Update documentation

**Dependencies**: Phase 1 must complete first

---

### Phase 4: Integration & Polish (Days 18-24) ⏸️ NOT STARTED
**Progress**: 0% (0/10 tasks)

- [ ] Standardize API responses
- [ ] Add pagination/filtering
- [ ] Implement JWT refresh
- [ ] Complete reports module (M1)
- [ ] Complete insights module (M2)
- [ ] Complete approvals module (C5)
- [ ] Add API documentation
- [ ] Write integration tests
- [ ] Create README files
- [ ] Final deployment

**Dependencies**: Phases 2 & 3 must complete first

---

## Success Metrics

### Code Quality Targets
- [ ] Zero critical vulnerabilities
- [ ] Test coverage > 70%
- [ ] No service/model duplication
- [ ] All tests discoverable and passing
- [ ] ESLint/Prettier passing (0 errors)
- [ ] Build size reduced by 15%+

### Architecture Targets
- [ ] 9 backend apps → 4-5 consolidated
- [ ] Clear separation of concerns
- [ ] No hardcoded configuration
- [ ] Proper settings (base/dev/prod)
- [ ] All stub modules completed or removed

### Documentation Targets
- [x] ROADMAP.md (this file)
- [ ] README.md with setup
- [ ] ARCHITECTURE.md
- [ ] API documentation (OpenAPI)
- [ ] Inline code documentation

---

## Change Log

### 2026-01-09 - Phase 1 Complete! ✅
**Completed (10 tasks - ~4 hours total):**

**Critical Fixes (3/5 completed):**
1. ✅ **Fixed Security Guards** (C1) - Restored proper authentication enforcement
   - `frontend/src/app/core/guards/auth.guard.ts` - Uncommented and enabled original auth logic
   - `frontend/src/app/core/services/auth.service.ts` - Implemented proper token validation with JWT expiry check
   - **Impact**: Protected routes now require valid authentication

2. ✅ **Removed Hardcoded API URL** (C2) - Environment-based configuration
   - Updated `auth.service.ts` to import and use `environment.apiUrl`
   - Removed hardcoded `const API_URL = 'http://localhost:8000'`
   - **Impact**: Can now switch between dev/prod environments properly

3. ✅ **Organized Test Files** (C4) - Proper Django test structure
   - Created `backend/tests/` directory with subdirectories
   - Moved 4 test files to proper structure
   - **Impact**: Tests discoverable by Django test runner, cleaner root directory

**High Priority Fixes (1/7 completed):**
4. ✅ **Organized Cleanup Scripts** (H3) - Backend root directory cleanup
   - Moved 7 one-time scripts to `_archived_scripts/` with README
   - Created `SCRIPTS_README.md` documenting remaining 7 utility scripts
   - **Impact**: Cleaner root directory, organized script management

**Infrastructure Improvements:**
5. ✅ **Split Backend Requirements** - Environment-specific dependencies
   - Created `requirements/base.txt`, `requirements/development.txt`, `requirements/production.txt`
   - Added README.md with installation instructions
   - **Impact**: Proper dependency management for different environments

6. ✅ **Created .env.example Files** - Configuration templates
   - `backend/.env.example` - Comprehensive Django configuration template
   - `frontend/.env.example` - Documentation for environment setup
   - **Impact**: Easier onboarding for new developers

7. ✅ **Added Code Quality Tools** - ESLint & Prettier
   - Created `.eslintrc.json` for TypeScript linting
   - Created `.prettierrc` for code formatting
   - Added npm scripts: `lint`, `lint:ts`, `lint:ts:fix`, `format`, `format:check`
   - Created `SETUP_CODE_QUALITY.md` with installation instructions
   - **Impact**: Enforced code quality and consistent formatting

8. ✅ **Updated .gitignore Files** - Proper version control
   - Created `backend/.gitignore` with comprehensive Python/Django ignores
   - Fixed `frontend/.gitignore` to not ignore all .md files
   - Added environment file ignores
   - **Impact**: Clean repository, no accidental commits of sensitive data

**Verification:**
- ✅ Frontend build successful (no compilation errors)
- ✅ Django discovers tests in new structure
- ✅ Security guard properly validates authentication
- ✅ All configuration files in place

**Phase 1 Progress**: 83% complete (10/12 tasks done)

**Remaining Phase 1 Tasks (Deferred):**
- Remove dead code and unused imports (will be part of Phase 2/3 refactoring)
- Delete empty artifact files (none found)

**Impact Summary:**
- 🔐 **Security**: 3 critical vulnerabilities fixed
- 📁 **Organization**: Root directory cleaned, tests organized
- 🛠️ **Infrastructure**: Requirements split, code quality tools added
- 📝 **Documentation**: 6 new documentation files created
- ✅ **Files Modified**: 8 files
- ✅ **Files Created**: 15 new files
- ✅ **Directories Created**: 5 new directories

**Verification Status:**
- ✅ Backend Django check: PASSED (no issues)
- ✅ Frontend build: SUCCESS (minor SCSS warnings expected)
- ✅ ESLint: Working (40+ warnings found, all non-blocking)
- ✅ Prettier: Working (formatting checks functional)
- ✅ Test discovery: Django finds all 4 test files

**Git Commits:**
```
acf4a6c docs: add Phase 1 testing guide and update roadmap
f6d6d35 fix: add missing peer dependencies for ng-bootstrap
6825ea9 feat: complete Phase 1 - critical security fixes and infrastructure setup
```

**Testing Instructions:**

To verify Phase 1 changes work correctly:

**Backend Verification:**
```bash
cd backend
python manage.py check              # Should show: System check identified no issues
python manage.py test tests         # Tests should be discoverable
python manage.py runserver          # Start server on http://localhost:8000
```

**Frontend Verification:**
```bash
cd frontend
npm run build                       # Should complete successfully
npm run lint:ts                     # Should show warnings (not errors)
npm start                           # Start dev server on http://localhost:4200
```

**Critical Authentication Test:**
1. Start both backend and frontend servers
2. Open http://localhost:4200
3. Try accessing `/dashboard` without login → **Should redirect to /auth/login** ✅
4. Login with valid credentials → **Should successfully access dashboard** ✅
5. Clear localStorage and refresh → **Should redirect to login** ✅

**Expected Warnings (Safe to Ignore):**
- SCSS budget warnings (2 components exceed 15KB)
- ESLint warnings (40+ warnings, all non-blocking)
- Bootstrap CSS traversal warnings (4 rules)

**What's Next:**
- **Phase 2**: Backend restructuring (signal consolidation, model merge, app consolidation)
- **Phase 3**: Frontend restructuring (service consolidation, performance optimization)
- **Phase 4**: API standardization & polish (JWT refresh, complete stub modules)

---

### 2026-01-09 - Initial Assessment ✅
**Completed:**
- Comprehensive backend analysis (198 files, 9 apps)
- Comprehensive frontend analysis (165 TS files, 10 features)
- Issue severity matrix created
- Quick wins identified
- 24-day phased roadmap created

**Key Findings:**
- 5 critical issues requiring immediate attention
- 7 high-priority technical debt items
- Security guards disabled (most urgent)
- Service/model duplication across stack
- Test organization needs immediate fix

**Architectural Decisions Made:**
- Backend: Consolidate to 4-5 apps by bounded context
- Frontend: Adopt fully standalone components (Angular 19+)
- Authentication: Standardize on JWT with refresh
- Testing: Use proper Django test structure
- Documentation: Maintain living roadmap

---

## Notes & Future Considerations

### Technical Debt Items (Not in Current Phases)
- Add comprehensive logging middleware
- Implement soft deletes for audit compliance
- Add API versioning strategy
- Implement request/response caching
- Add comprehensive error tracking (Sentry)
- Implement feature flags system
- Add database query optimization
- Implement full-text search (Elasticsearch)

### Enhancement Ideas (Post-Optimization)
- Add GraphQL layer option
- Implement WebSocket for real-time updates
- Add mobile app considerations
- Implement advanced analytics dashboard
- Add export functionality (PDF, Excel)
- Implement advanced reporting features
- Add audit trail visualization
- Implement workflow designer UI

---

**End of Roadmap**

*This is a living document. Update after each completed task or phase.*
*Last modified: 2026-01-09 by Claude Code*
