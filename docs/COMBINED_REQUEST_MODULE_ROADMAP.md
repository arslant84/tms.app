# Combined Request Module - Feasibility Study & Implementation Roadmap

## Executive Summary

This document outlines the feasibility and implementation roadmap for a new **Combined Request Module** that allows users to apply for TSR (Travel Request), Transport, Accommodation, and Visa in a single unified request. This addresses the end-user requirement of streamlining the application process when all services are needed for a trip.

---

## 1. FEASIBILITY ASSESSMENT

### 1.1 Technical Feasibility: ✅ HIGH

The current TMS architecture is well-suited for this enhancement:

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Modular Architecture** | ✅ Excellent | Clean separation of modules with consistent patterns |
| **Workflow Engine** | ✅ Ready | Generic workflow engine can handle new entity types |
| **Database Design** | ✅ Flexible | JSONField pattern allows extensible data storage |
| **API Structure** | ✅ Consistent | RESTful patterns make new endpoints straightforward |
| **Frontend Components** | ✅ Reusable | Form components can be composed into wizard |
| **Permission System** | ✅ Extensible | New permissions can be added easily |

### 1.2 Business Feasibility: ✅ HIGH

- **User Demand**: End-user requirement confirms need
- **Efficiency Gains**: Single form reduces data entry duplication
- **Process Improvement**: Coordinated approvals ensure consistency
- **Admin Benefits**: Unified view of complete travel package

### 1.3 Key Challenges & Mitigations

| Challenge | Mitigation Strategy |
|-----------|---------------------|
| Complex approval workflow | Create unified workflow with module-specific steps |
| Partial approvals (some modules approved, others rejected) | Support partial completion with status tracking per module |
| Large form size | Multi-step wizard with progress tracking |
| Data redundancy | Share common fields (requestor info, travel dates) |
| Backward compatibility | New module operates alongside existing standalone modules |

---

## 2. ARCHITECTURE OPTIONS

### Option A: Unified Combined Request Model (⭐ RECOMMENDED)

Create a single `CombinedRequest` model that contains all fields from all modules, with its own unified workflow.

**Pros:**
- Single source of truth
- Simplified approval workflow
- Better user experience
- Easier reporting and tracking

**Cons:**
- Large model with many fields
- Requires new workflow template configuration

### Option B: Request Bundle (Orchestrator Pattern)

Create a `RequestBundle` that coordinates multiple individual requests (TRF, Transport, Accommodation, Visa) behind the scenes.

**Pros:**
- Reuses existing models and logic
- Modular approval per component
- Less code duplication

**Cons:**
- Complex synchronization
- Multiple workflows to manage
- Harder to track overall status
- Approval coordination is complex

### Option C: Hybrid Approach

Master `CombinedRequest` with optional child requests spawned when approved.

**Pros:**
- Unified form entry
- Individual processing after approval

**Cons:**
- Most complex to implement
- Two-phase processing

### **Recommendation: Option A (Unified Model)**

Given the existing patterns and user requirement for simplicity, a unified model provides the cleanest solution.

---

## 3. DATA MODEL DESIGN

### 3.1 New Models

```python
# backend/combined_request/models.py

class CombinedRequest(models.Model):
    """
    Unified request combining TSR, Transport, Accommodation, and Visa.
    """
    # ===== REQUEST IDENTIFICATION =====
    request_number = models.CharField(max_length=50, unique=True, blank=True)

    # ===== REQUESTOR INFORMATION (Shared) =====
    requestor = models.ForeignKey(User, on_delete=models.CASCADE)
    requestor_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)

    # ===== MODULE INCLUSION FLAGS =====
    include_travel = models.BooleanField(default=True)
    include_transport = models.BooleanField(default=False)
    include_accommodation = models.BooleanField(default=False)
    include_visa = models.BooleanField(default=False)

    # ===== TRAVEL/TSR SECTION =====
    travel_type = models.CharField(max_length=50, blank=True)  # domestic, international, home_leave, external
    travel_purpose = models.TextField(blank=True)
    departure_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    destination_country = models.CharField(max_length=100, blank=True)
    destination_city = models.CharField(max_length=100, blank=True)
    cost_center = models.CharField(max_length=100, blank=True)
    travel_data = models.JSONField(default=dict, blank=True)  # Additional travel-specific data

    # ===== TRANSPORT SECTION =====
    transport_required_from = models.DateTimeField(null=True, blank=True)
    transport_required_to = models.DateTimeField(null=True, blank=True)
    transport_pickup_location = models.CharField(max_length=500, blank=True)
    transport_dropoff_location = models.CharField(max_length=500, blank=True)
    transport_data = models.JSONField(default=dict, blank=True)  # Transport segments, etc.

    # ===== ACCOMMODATION SECTION =====
    accommodation_checkin = models.DateField(null=True, blank=True)
    accommodation_checkout = models.DateField(null=True, blank=True)
    accommodation_location = models.CharField(max_length=500, blank=True)
    accommodation_guests = models.IntegerField(default=1)
    accommodation_preferences = models.TextField(blank=True)
    accommodation_data = models.JSONField(default=dict, blank=True)  # Room preferences, etc.

    # ===== VISA SECTION =====
    visa_destination_country = models.CharField(max_length=100, blank=True)
    visa_type = models.CharField(max_length=50, blank=True)
    passport_number = models.CharField(max_length=50, blank=True)
    passport_expiry = models.DateField(null=True, blank=True)
    visa_data = models.JSONField(default=dict, blank=True)  # Additional visa fields

    # ===== STATUS & WORKFLOW =====
    status = models.CharField(max_length=50, default='draft')

    # Module-specific statuses for partial approval tracking
    travel_status = models.CharField(max_length=50, default='pending')
    transport_status = models.CharField(max_length=50, default='pending')
    accommodation_status = models.CharField(max_length=50, default='pending')
    visa_status = models.CharField(max_length=50, default='pending')

    # ===== COMMENTS & TRACKING =====
    additional_comments = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)

    # ===== TIMESTAMPS =====
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Combined Request'
        verbose_name_plural = 'Combined Requests'


class CombinedRequestPassport(models.Model):
    """Passport details for combined request."""
    combined_request = models.ForeignKey(CombinedRequest, on_delete=models.CASCADE, related_name='passports')
    passport_name = models.CharField(max_length=255)
    passport_number = models.CharField(max_length=50)
    nationality = models.CharField(max_length=100)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    passport_file = models.FileField(upload_to='combined_passports/', null=True, blank=True)


class CombinedRequestItinerary(models.Model):
    """Itinerary segments for combined request."""
    combined_request = models.ForeignKey(CombinedRequest, on_delete=models.CASCADE, related_name='itinerary_segments')
    segment_order = models.PositiveIntegerField(default=1)
    from_location = models.CharField(max_length=255)
    to_location = models.CharField(max_length=255)
    departure_date = models.DateField()
    departure_time = models.TimeField(null=True, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)
    mode_of_travel = models.CharField(max_length=50)  # flight, train, bus, etc.
    notes = models.TextField(blank=True)


class CombinedRequestTransportSegment(models.Model):
    """Transport segments for combined request."""
    combined_request = models.ForeignKey(CombinedRequest, on_delete=models.CASCADE, related_name='transport_segments')
    segment_order = models.PositiveIntegerField(default=1)
    pickup_location = models.CharField(max_length=500)
    dropoff_location = models.CharField(max_length=500)
    pickup_datetime = models.DateTimeField()
    passengers = models.IntegerField(default=1)
    vehicle_type_preference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)


class CombinedRequestDocument(models.Model):
    """Supporting documents for combined request."""
    combined_request = models.ForeignKey(CombinedRequest, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50)  # passport, visa_photo, invitation_letter, etc.
    module = models.CharField(max_length=20)  # travel, transport, accommodation, visa
    file = models.FileField(upload_to='combined_documents/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class CombinedRequestApprovalStep(models.Model):
    """Approval tracking for combined request."""
    combined_request = models.ForeignKey(CombinedRequest, on_delete=models.CASCADE, related_name='approval_steps')
    step_order = models.PositiveIntegerField()
    step_name = models.CharField(max_length=100)
    module = models.CharField(max_length=20, blank=True)  # Which module this step is for
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    comments = models.TextField(blank=True)
    actioned_at = models.DateTimeField(null=True, blank=True)
```

### 3.2 Database Relationships Diagram

```
CombinedRequest
├── CombinedRequestPassport (1:N)
├── CombinedRequestItinerary (1:N)
├── CombinedRequestTransportSegment (1:N)
├── CombinedRequestDocument (1:N)
├── CombinedRequestApprovalStep (1:N)
└── WorkflowInstance (1:1 via generic FK)
```

---

## 4. WORKFLOW DESIGN (Option A: Single Unified Workflow)

### 4.1 Design Decision

**Chosen Approach:** Single Unified Workflow with Conditional Steps

This approach uses ONE workflow for the entire Combined Request, with steps that are conditionally executed based on which modules are included. The workflow engine's existing `WorkflowCondition` model handles step skipping automatically.

**Benefits:**
- Single approval flow - easier to track overall status
- One workflow instance per request
- Clear progression through approval stages
- Leverages existing workflow engine without modifications

### 4.2 Workflow Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMBINED REQUEST WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Step 1: Line Manager Approval │ ← ALWAYS
                    │  (Reviews travel justification)│
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Step 2: HOD Approval          │ ← ALWAYS
                    │  (Department head sign-off)    │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ Step 3:         │ │ Step 4:         │ │ Step 5:         │
    │ Transport Review│ │ Accommodation   │ │ Visa Review     │
    │                 │ │ Review          │ │                 │
    │ IF include_     │ │ IF include_     │ │ IF include_     │
    │ transport=true  │ │ accommodation   │ │ visa=true       │
    │                 │ │ =true           │ │                 │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │ (skip if false)   │ (skip if false)   │ (skip if false)
             └───────────────────┼───────────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────────┐
                    │  Step 5: Final Admin Processing│ ← ALWAYS
                    │  (Clerk processes all modules) │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │   COMPLETED   │
                            └───────────────┘
```

### 4.3 Conditional Step Execution

The workflow engine's `WorkflowCondition` model evaluates conditions before activating each step:

| Step | Condition | Skipped When |
|------|-----------|--------------|
| Step 1: Department Focal | None | Can be skipped if no focal available |
| Step 2: Line Manager | None | Can be skipped if no LM available |
| Step 3: HOD | None | Can be skipped if no HOD available |
| Step 4: Travel Desk | None | Never (main processing step) |

### 4.4 Module-Specific Status Tracking

While using a single workflow, we track individual module statuses for visibility:

```python
class CombinedRequest(models.Model):
    # Overall workflow status (driven by workflow engine)
    status = models.CharField(max_length=50, default='draft')

    # Module-specific statuses (for tracking/display)
    travel_status = models.CharField(max_length=50, default='pending')
    transport_status = models.CharField(max_length=50, default='not_requested')
    accommodation_status = models.CharField(max_length=50, default='not_requested')
    visa_status = models.CharField(max_length=50, default='not_requested')
```

**Status Values:**
- `not_requested` - Module not included in this request
- `pending` - Awaiting approval
- `approved` - Module-specific approval received
- `processing` - Being processed by admin
- `completed` - Fully processed

### 4.5 Workflow Configuration (Database Seed)

```json
{
  "entity_type": "combined_request",
  "name": "Combined Request Approval Workflow",
  "description": "Unified workflow for combined TSR/Transport/Accommodation/Visa requests",
  "is_active": true,
  "allow_parallel_steps": false,
  "steps": [
    {
      "step_order": 1,
      "step_name": "Line Manager Approval",
      "approver_permission": "approve_trf",
      "is_required": true,
      "sla_hours": 48,
      "conditions": []
    },
    {
      "step_order": 2,
      "step_name": "Department Head Approval",
      "approver_permission": "approve_trf",
      "is_required": true,
      "sla_hours": 48,
      "conditions": []
    },
    {
      "step_order": 3,
      "step_name": "Transport Coordinator Review",
      "approver_permission": "approve_transport",
      "is_required": false,
      "can_skip": true,
      "sla_hours": 24,
      "conditions": [
        {"field": "include_transport", "operator": "equals", "value": true}
      ]
    },
    {
      "step_order": 4,
      "step_name": "Accommodation Coordinator Review",
      "approver_permission": "approve_accommodation",
      "is_required": false,
      "can_skip": true,
      "sla_hours": 24,
      "conditions": [
        {"field": "include_accommodation", "operator": "equals", "value": true}
      ]
    },
    {
      "step_order": 5,
      "step_name": "Visa Processing Review",
      "approver_permission": "approve_visa",
      "is_required": false,
      "can_skip": true,
      "sla_hours": 72,
      "conditions": [
        {"field": "include_visa", "operator": "equals", "value": true}
      ]
    },
    {
      "step_order": 6,
      "step_name": "Final Admin Processing",
      "approver_permission": "process_combined_requests",
      "is_required": true,
      "sla_hours": 24,
      "conditions": []
    }
  ]
}
```

### 4.6 Workflow Engine Integration

The existing `WorkflowRouter` needs to be updated to recognize `combined_request` entity type:

```python
# backend/workflows/router.py

ENTITY_TYPE_MAPPING = {
    'trf': 'travelrequest',
    'transport': 'transportrequest',
    'visa': 'visaapplication',
    'accommodation': 'accommodationrequest',
    'combined_request': 'combinedrequest',  # NEW
}
```

---

## 5. API DESIGN

### 5.1 Endpoints

```
/api/combined-request/
├── GET    /                           # List all combined requests
├── POST   /                           # Create new combined request
├── GET    /{id}/                      # Get combined request details
├── PUT    /{id}/                      # Update combined request
├── PATCH  /{id}/                      # Partial update
├── DELETE /{id}/                      # Delete/cancel request
├── POST   /{id}/submit/               # Submit for approval
├── POST   /{id}/approve/              # Approve request
├── POST   /{id}/reject/               # Reject request
├── GET    /{id}/approval-history/     # Get approval history
│
├── GET    /passports/                 # Passport details CRUD
├── GET    /itinerary-segments/        # Itinerary CRUD
├── GET    /transport-segments/        # Transport segments CRUD
├── GET    /documents/                 # Documents CRUD
```

### 5.2 Serializers Structure

```python
# Serializers
- CombinedRequestListSerializer      # For list views
- CombinedRequestDetailSerializer    # For detail views with nested data
- CombinedRequestCreateSerializer    # For creating new requests
- CombinedRequestUpdateSerializer    # For updating requests
- CombinedRequestPassportSerializer
- CombinedRequestItinerarySerializer
- CombinedRequestTransportSegmentSerializer
- CombinedRequestDocumentSerializer
```

---

## 6. NAVIGATION INTEGRATION (SEAMLESS)

The Combined Request will be added as a **5th request type** in the header navigation, following the existing pattern exactly.

### 6.1 Header Navigation Update

**Current Header Nav** (`header.component.html` lines 21-50):
```
TSR → Transport → Visa → Accommodation
```

**Updated Header Nav** (add Combined after Accommodation):
```
TSR → Transport → Visa → Accommodation → Combined
```

**Code Change** in `frontend/src/app/shared/components/header/header.component.html`:
```html
<!-- Add after Accommodation nav-link (line 49) -->
<a
  routerLink="/combined"
  routerLinkActive="active"
  class="nav-link">
  <i class="bi bi-collection"></i>
  <span>Combined</span>
</a>
```

### 6.2 Routes Integration

**Add to `app.routes.ts`** (follows existing pattern):

```typescript
// In requests children (after visa route, line 66):
{ path: 'combined', component: CombinedRequestWizardComponent },

// Add new management module (after visa module, line 241):
// Combined Request Management
{
  path: 'combined',
  loadChildren: () => import('./features/combined/combined.module').then(m => m.CombinedModule)
},
```

### 6.3 Admin Sidebar Integration

**Current Sidebar Order** (from `sidebar.component.html`):
```
1. Reports (if hasReportPermissions)
2. Flights Admin (if hasFlightsAdminPermission)
3. Accommodation Admin (if hasAccommodationAdminPermission)
4. Visa Admin (if hasVisaAdminPermission)
5. Transport Admin (if hasTransportAdminPermission)
6. Approvals (if hasApprovalPermissions) ← with badge count
7. User Management (if hasAdminPermissions)
───────────────────────────────────────────
8. System Settings (if hasAdminPermissions)
```

**Updated Sidebar Order** (add Combined Admin after Transport Admin):
```
1. Reports
2. Flights Admin
3. Accommodation Admin
4. Visa Admin
5. Transport Admin
6. Combined Admin ← NEW
7. Approvals ← with badge count (includes combined requests)
8. User Management
───────────────────────────────────────────
9. System Settings
```

**Code Changes Required:**

**1. Add to `sidebar.component.html`** (after Transport Admin, before Approvals):
```html
<!-- Combined Admin -->
<a
  *ngIf="hasCombinedAdminPermission"
  routerLink="/admin/combined"
  routerLinkActive="active"
  [routerLinkActiveOptions]="{ exact: false }"
  class="nav-item"
  [attr.title]="'Combined Admin'">
  <i class="bi bi-collection"></i>
  <span class="nav-label">Combined Admin</span>
</a>
```

**2. Add to `sidebar.component.ts`**:
```typescript
// Add permission check method
get hasCombinedAdminPermission(): boolean {
  return this.rbacService.canAccessAdminMenu('combined');
}
```

**3. Update `rbac.service.ts`** to recognize 'combined' admin module:
```typescript
canAccessAdminMenu(module: string): boolean {
  const modulePermissions: Record<string, Permission[]> = {
    'flights': [Permission.VIEW_ADMIN_FLIGHTS, Permission.SYSTEM_ADMIN],
    'transport': [Permission.VIEW_ADMIN_TRANSPORT, Permission.SYSTEM_ADMIN],
    'accommodation': [Permission.VIEW_ADMIN_ACCOMMODATION, Permission.SYSTEM_ADMIN],
    'visa': [Permission.VIEW_ADMIN_VISA, Permission.SYSTEM_ADMIN],
    'combined': [Permission.VIEW_ADMIN_COMBINED, Permission.SYSTEM_ADMIN],  // NEW
  };
  return this.hasAnyPermission(modulePermissions[module] || []);
}
```

**4. Update `permission.models.ts`**:
```typescript
export enum Permission {
  // ... existing permissions ...

  // Combined Request permissions
  VIEW_ADMIN_COMBINED = 'view_admin_combined',
  CREATE_COMBINED_REQUEST = 'create_combined_request',
  APPROVE_COMBINED_REQUEST = 'approve_combined_request',
  PROCESS_COMBINED_REQUESTS = 'process_combined_requests',
  MANAGE_COMBINED_REQUESTS = 'manage_combined_requests',
}
```

### 6.4 URL Structure (Matches Existing Pattern)

| Module | Create Request | My Requests | Admin Panel |
|--------|---------------|-------------|-------------|
| TSR | `/requests/travel/*` | `/trf` | `/admin/flights` |
| Transport | `/requests/transport` | `/transport` | `/admin/transport` |
| Visa | `/requests/visa` | `/visa` | `/admin/visa` |
| Accommodation | `/requests/accommodation` | `/accommodation` | `/admin/accommodation` |
| **Combined** | `/requests/combined` | `/combined` | `/admin/combined` |

### 6.5 Navigation Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HEADER NAV BAR                              │
├─────────┬───────────┬─────────┬───────────────┬────────────────────┤
│   TSR   │ Transport │  Visa   │ Accommodation │     Combined       │
│  /trf   │/transport │  /visa  │/accommodation │     /combined      │
└────┬────┴─────┬─────┴────┬────┴───────┬───────┴─────────┬──────────┘
     │          │          │            │                 │
     ▼          ▼          ▼            ▼                 ▼
  My TSRs   My Transport  My Visa   My Accomm.      My Combined
  Requests   Requests    Requests   Requests         Requests
     │          │          │            │                 │
     │          │          │            │                 │
     └──────────┴──────────┴────────────┴─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  "Create New" CTA │
                    └─────────┬─────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    Request Type Selection     │
              │   (or direct from header)     │
              └───────────────────────────────┘
```

---

## 7. FRONTEND FORM DESIGN

### 7.1 Multi-Step Wizard Form

The Combined Request form will be a **multi-step wizard** (similar to TravelRequestWizardComponent) with the following steps:

```
STEP 1: Request Type Selection
├── Which modules do you need?
│   ☑ Travel Request (TSR)
│   ☑ Transport
│   ☑ Accommodation
│   ☑ Visa
└── [Next]

STEP 2: Basic Information (Shared)
├── Requestor Details (auto-filled from profile)
├── Travel Dates
├── Destination
└── Purpose

STEP 3: Travel Details (if selected)
├── Travel Type (Domestic/International/Home Leave/External)
├── Itinerary Builder
├── Cost Estimation
└── Passport Details

STEP 4: Transport Details (if selected)
├── Transport Segments
├── Pickup/Dropoff Locations
├── Date/Time Selection
└── Vehicle Preferences

STEP 5: Accommodation Details (if selected)
├── Check-in/Check-out Dates
├── Location Preference
├── Number of Guests
└── Room Type Preferences

STEP 6: Visa Details (if selected)
├── Destination Country
├── Visa Type
├── Passport Information
├── Supporting Documents Upload

STEP 7: Review & Submit
├── Summary of all sections
├── Document checklist
├── Terms & Conditions
└── [Submit Request]
```

### 7.2 Component Structure

```
frontend/src/app/features/requests/combined/
├── combined-request.routes.ts
├── services/
│   └── combined-request.service.ts
├── models/
│   └── combined-request.model.ts
├── components/
│   ├── combined-request-wizard/
│   │   ├── combined-request-wizard.component.ts
│   │   ├── combined-request-wizard.component.html
│   │   └── combined-request-wizard.component.scss
│   ├── step-module-selection/
│   ├── step-basic-info/
│   ├── step-travel-details/
│   ├── step-transport-details/
│   ├── step-accommodation-details/
│   ├── step-visa-details/
│   ├── step-review-submit/
│   └── combined-request-summary/
└── pages/
    ├── combined-request-list/
    ├── combined-request-detail/
    └── combined-request-edit/
```

---

## 8. ADMIN PANEL INTEGRATION

### 8.1 Combined Request Admin Module

```
/admin/combined-requests/
├── Dashboard (overview stats)
├── Pending Requests (queue)
├── All Requests (searchable list)
├── Processing (handle approved requests)
└── Reports
```

### 8.2 Unified Approvals Integration

Combined Requests will appear in the **same unified approvals queue** (`/api/admin/approvals/`) alongside all other request types.

#### Backend Changes (`approvals/views.py`):

```python
def get_all_pending_approvals(self):
    """
    Aggregates pending approvals from all modules including Combined Requests.
    """
    # Existing modules
    trf_pending = TravelRequest.objects.filter(...)
    transport_pending = TransportRequest.objects.filter(...)
    visa_pending = VisaApplication.objects.filter(...)
    accommodation_pending = AccommodationRequest.objects.filter(...)

    # NEW: Add combined requests
    combined_pending = CombinedRequest.objects.filter(
        status__in=['pending_lm_approval', 'pending_hod_approval',
                    'pending_transport_review', 'pending_accommodation_review',
                    'pending_visa_review']
    )

    # Merge and return with type identifier
    all_pending = []
    for item in combined_pending:
        all_pending.append({
            'id': item.id,
            'type': 'combined',  # Type identifier
            'request_number': item.request_number,
            'requestor_name': item.requestor_name,
            'department': item.department,
            'status': item.status,
            'submitted_at': item.submitted_at,
            'includes': {  # Show which modules are included
                'travel': item.include_travel,
                'transport': item.include_transport,
                'accommodation': item.include_accommodation,
                'visa': item.include_visa,
            },
            'current_step': self.get_current_workflow_step(item),
        })

    return all_pending
```

#### Frontend Approvals List Display:

Combined requests in the approvals list will show:
- Type badge: "Combined" with distinct color
- Included modules as mini-badges: [TSR] [Transport] [Accommodation] [Visa]
- Current approval step name
- Requestor info and submission date

```typescript
// In pending-approvals.component.ts
getTypeBadgeClass(type: string): string {
  const classes: Record<string, string> = {
    'trf': 'badge-primary',
    'transport': 'badge-info',
    'visa': 'badge-warning',
    'accommodation': 'badge-success',
    'combined': 'badge-purple',  // Distinct color for combined
  };
  return classes[type] || 'badge-secondary';
}

// Display included modules
getIncludedModules(item: any): string[] {
  if (item.type !== 'combined') return [];
  const modules = [];
  if (item.includes?.travel) modules.push('TSR');
  if (item.includes?.transport) modules.push('Transport');
  if (item.includes?.accommodation) modules.push('Accommodation');
  if (item.includes?.visa) modules.push('Visa');
  return modules;
}
```

#### Approval Detail View:

When an approver clicks on a Combined Request, they see:
1. **Summary Section** - Requestor info, dates, overall status
2. **Travel Section** (if included) - Itinerary, purpose, cost
3. **Transport Section** (if included) - Pickup/dropoff details
4. **Accommodation Section** (if included) - Check-in/out, location
5. **Visa Section** (if included) - Passport, visa type, documents
6. **Approval Actions** - Approve/Reject with comments

```
┌─────────────────────────────────────────────────────────────────┐
│ Combined Request: CMB-20250415-0930-DXB-A7K2                    │
│ Status: Pending HOD Approval                                     │
├─────────────────────────────────────────────────────────────────┤
│ Requestor: John Smith | Dept: Engineering | Submitted: Apr 15   │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│ │ ✓ TSR      │ │ ✓ Transport │ │ ✓ Accomm.  │ │ ✓ Visa      ││
│ │ Included   │ │ Included    │ │ Included   │ │ Included    ││
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ ▼ Travel Details                                                │
│   Purpose: Client Meeting                                        │
│   Destination: Dubai, UAE                                        │
│   Dates: Apr 20 - Apr 25, 2025                                  │
│   Estimated Cost: $3,500                                         │
├─────────────────────────────────────────────────────────────────┤
│ ▼ Transport Details                                              │
│   Pickup: Office → Airport (Apr 20, 6:00 AM)                    │
│   Return: Airport → Office (Apr 25, 8:00 PM)                    │
├─────────────────────────────────────────────────────────────────┤
│ ▼ Accommodation Details                                          │
│   Location: Dubai Marina                                         │
│   Check-in: Apr 20 | Check-out: Apr 25                          │
│   Guests: 1 | Room Type: Standard                                │
├─────────────────────────────────────────────────────────────────┤
│ ▼ Visa Details                                                   │
│   Country: UAE | Type: Business Visa                             │
│   Passport: AB1234567 | Expiry: Dec 2027                        │
├─────────────────────────────────────────────────────────────────┤
│ Comments: ________________________________________________       │
│                                                                  │
│ [Approve]  [Reject]  [Request More Info]                        │
└─────────────────────────────────────────────────────────────────┘
```

#### Approval Badge Count:

The sidebar approval badge already counts all pending items. Combined Requests will be automatically included in this count since the unified approvals endpoint aggregates all types.

---

## 9. PERMISSIONS

### 9.1 New Permissions Required

```python
# Add to permission.models.ts and accounts
COMBINED_REQUEST_PERMISSIONS = {
    'create_combined_request': 'Can create combined requests',
    'view_combined_request': 'Can view combined requests',
    'approve_combined_request': 'Can approve combined requests',
    'process_combined_requests': 'Can process approved combined requests',
    'view_admin_combined': 'Can access combined requests admin panel',
    'manage_combined_requests': 'Can manage all combined requests',
}
```

### 9.2 Permission Groups Update

```python
BASIC_USER_PERMISSIONS += ['create_combined_request', 'view_combined_request']
APPROVER_PERMISSIONS += ['approve_combined_request']
ADMIN_PERMISSIONS += ['process_combined_requests', 'view_admin_combined', 'manage_combined_requests']
```

---

## 10. IMPLEMENTATION PHASES

### Phase 1: Foundation ✅ COMPLETED (2025-04-13)
- [x] Create Django app: `combined_request`
- [x] Implement database models (6 models created)
- [x] Create migrations (0001_initial.py)
- [x] Set up model admin for testing (with inlines)
- [x] Add new permissions to system (7 new permissions)
- [x] Update request ID generator for CMB type
- [x] Create serializers (skeleton for Phase 2)
- [x] Create views (skeleton for Phase 2)

**Files Created:**
```
backend/combined_request/
├── __init__.py
├── apps.py
├── models.py                    # CombinedRequest + 5 related models
├── admin.py                     # Django admin with inlines
├── serializers.py               # 8 serializers (ready for Phase 2)
├── views.py                     # ViewSet skeleton
├── urls.py                      # URL routing placeholder
└── migrations/
    ├── __init__.py
    ├── 0001_initial.py          # Initial schema
    ├── 0002_add_transport_purpose_tsr_ref_accommodation_gender.py
    └── 0003_add_all_missing_fields_fix_transport_segment.py
```

**Files Modified:**
- `backend/tms_project/settings.py` - Added app to INSTALLED_APPS
- `backend/utils/request_id_generator.py` - Added CMB type
- `backend/accounts/migrations/0029_add_combined_request_permissions.py` - New permissions
- `frontend/src/app/core/models/permission.models.ts` - Added 7 permissions

**To Apply:**
```bash
cd backend && python manage.py migrate
```

---

### Phase 2: Backend API ✅ COMPLETED (2025-04-13)
- [x] Complete ViewSets with full CRUD implementation
- [x] Add proper permission checks to views
- [x] Add submit/approve/reject actions with workflow
- [x] Integrate with workflow engine (WorkflowRouter)
- [x] Create workflow template in management command
- [x] Add combined requests to unified approvals endpoint
- [x] Register URLs in main urls.py
- [ ] Unit tests for API endpoints (deferred to Phase 6)

**Files Modified:**
- `backend/combined_request/views.py` - Full ViewSet with submit/approve/reject actions
- `backend/combined_request/urls.py` - Router configuration
- `backend/workflows/router.py` - Added combinedrequest to admin_role_map
- `backend/workflows/management/commands/create_default_workflows.py` - Added combined workflow
- `backend/approvals/views.py` - Added combined requests to unified approvals
- `backend/tms_project/urls.py` - Registered combined_request URLs

**API Endpoints Available:**
```
GET    /api/combined/combined-requests/          # List combined requests
POST   /api/combined/combined-requests/          # Create new request
GET    /api/combined/combined-requests/{id}/     # Get request details
PUT    /api/combined/combined-requests/{id}/     # Update request
DELETE /api/combined/combined-requests/{id}/     # Delete request (draft only)
POST   /api/combined/combined-requests/{id}/submit/   # Submit for approval
POST   /api/combined/combined-requests/{id}/approve/  # Approve current step
POST   /api/combined/combined-requests/{id}/reject/   # Reject request
POST   /api/combined/combined-requests/{id}/cancel/   # Cancel request
```

**To Create Workflow Template:**
```bash
cd backend && python manage.py create_default_workflows
```

---

### Phase 3: Frontend Wizard ✅ COMPLETED (2025-04-13)
- [x] Create combined request module structure
- [x] Implement multi-step wizard component
- [x] Build module selection step
- [x] Build basic info step
- [x] Build travel details step with itinerary segments
- [x] Build transport details step with transport segments
- [x] Build accommodation details step
- [x] Build visa details step with passport information
- [x] Build review & submit step
- [x] Implement form validation across steps
- [x] Add progress indicator and step navigation
- [x] Implement draft auto-save to localStorage
- [x] Create CombinedRequestService with full API integration

**Files Created:**
```
frontend/src/app/features/requests/combined/
├── models/
│   └── combined-request.model.ts           # Interfaces, types, and format converters
├── services/
│   └── combined-request.service.ts         # API service with CRUD + workflow actions
├── combined-request-wizard.component.ts    # Multi-step wizard (create / edit)
├── combined-request-wizard.component.html
├── combined-request-wizard.component.scss
├── combined-list.component.ts              # My Requests list view (/combined)
├── combined-list.component.html
├── combined-list.component.scss
├── combined-detail.component.ts            # Request detail / status view (/combined/:id)
├── combined-detail.component.html
└── combined-detail.component.scss
```

**Files Modified:**
- `frontend/src/app/app.routes.ts` - Added combined request routes
- `frontend/src/app/features/requests/components/request-type-selection/` - Added featured Combined Request option

**Frontend Routes:**
```
/combined           # My combined requests list (CombinedListComponent)
/combined/new       # New combined request wizard
/combined/edit/:id  # Edit existing request
/combined/:id       # Request detail view (also used by admin "View" action)
```

---

### Phase 4: Navigation & Integration ✅ COMPLETED (2025-04-13)
- [x] Update routing configuration (app.routes.ts)
- [x] Add Combined Request to request type selection page
- [x] Backend unified approvals already includes combined requests (Phase 2)
- [x] Update sidebar navigation (Combined Admin) - Done in Phase 5
- [x] Add permission guards for combined routes (AdminMenuGuard with 'combined' module)
- [ ] Add "Combined" to header navigation bar (optional - accessible from request selection)

### Phase 5: Admin Panel ✅ COMPLETED (2025-04-13)
- [x] Create admin module for combined requests
- [x] Build dashboard with stats (CombinedAdminComponent)
- [x] Build request list with filters
- [x] Build detail/processing view (CombinedProcessingComponent — initial version; fully rewritten in Phase 7)
- [x] Integrate with existing admin navigation (sidebar, routes)

**Files Created:**
```
frontend/src/app/features/admin/combined/
├── components/
│   ├── combined-admin.component.ts        # Dashboard with stats, filterable list
│   ├── combined-admin.component.html
│   ├── combined-admin.component.scss
│   ├── combined-processing.component.ts   # Tabbed workflow processing view
│   ├── combined-processing.component.html
│   └── combined-processing.component.scss
```

**Files Modified:**
- `frontend/src/app/app.routes.ts` - Added combined admin routes with AdminMenuGuard
- `frontend/src/app/shared/components/sidebar/sidebar.component.ts` - Added hasCombinedAdminPermission
- `frontend/src/app/shared/components/sidebar/sidebar.component.html` - Added Combined Admin nav item
- `frontend/src/app/core/services/rbac.service.ts` - Added 'combined' to canAccessAdminMenu

**Admin Routes:**
```
/admin/combined            # Dashboard with stats and request list
/admin/combined/processing # Tabbed workflow processing view
```
Note: Clicking a request number navigates to `/combined/:id` (user-facing detail page), same pattern as visa admin.

### Phase 6: Testing & Refinement (Week 7-8)
**Status**: 🔄 IN PROGRESS

**Prerequisites (MUST DO FIRST):**
```bash
cd backend
python manage.py migrate
python manage.py create_default_workflows  # Creates Combined Request workflow template
```

**Tasks:**
- [x] Run database migrations (creates combined_request tables)
- [x] Create workflow template for Combined Requests
- [ ] End-to-end testing of wizard flow
- [ ] Test approval workflow integration
- [ ] Test admin panel functionality
- [ ] User acceptance testing
- [ ] Performance optimization
- [ ] Documentation

**Bug Fixes Applied (2025-04-13):**
- Fixed model loading error by adding explicit `app_label` to all models
- Fixed circular import in approvals/views.py with lazy imports
- Fixed frontend TypeScript error (added `position` to User model)
- Fixed SCSS deprecation warning (replaced `darken()` with design system variable)
- Fixed optional chaining warning in combined-request-wizard template

**Bug Fixes Applied (2025-04-18):**
- Fixed `combined-processing.component.ts` TypeScript error: `property 'processing' from index signature must use bracket notation` — changed `?.processing` → `?.['processing']` in `preFillForms()`, `isModuleCompleted()`, `getModuleProcessingData()`
- Fixed `combined-processing.component.ts` same-route navigation bug: `ngOnInit` used `route.snapshot.queryParamMap` which doesn't re-run on same-route navigation. Changed to subscribe to `route.queryParamMap` observable with `OnDestroy` cleanup — "Start Processing" button now reliably switches to detail mode.
- Fixed `combined-detail.component.html` HTML nesting: visa processing result box was inside `.sub-section` div instead of card-body — restructured closing divs
- Fixed `combined-admin.component.ts` stats accuracy: stats were calculated only from the current page (20 items). Now `loadStats()` fetches all items (`pageSize: 1000`) separately on init, matching the visa admin pattern. `buildDynamicOptions()` now also draws from the full dataset for accurate status/type filter options.
- Removed `estimated_cost` field entirely: dropped from `CombinedRequest` model, migration `0004_remove_combinedrequest_estimated_cost.py` created, removed from frontend model interfaces (`combined-request.model.ts`), wizard form group, PDF export row in `views.py`, and detail view display.
- Removed finance approval step: `'Pending Finance'` status removed from cancellable-statuses list in `views.py`. Finance step was never in the actual workflow command (4-step workflow: Dept Focal → LM → HOD → Travel Desk).

**Approval Workflow Audit (2025-04-18):**

Confirmed all five modules (TRF, Visa, Transport, Accommodation, Combined Request) are **fully workflow-driven** — no hardcoded approvers in primary paths:
- **Submit path**: all modules call `WorkflowRouter.start_workflow_for_request()`, which reads the active workflow template from the database.
- **Approve path**: all modules call `WorkflowEngine.process_action()`, advancing through whatever steps the template defines.
- **Frontend approver selection**: `ApproverSelectionComponent` takes `entityType` input and loads steps dynamically from the backend template. Changing the workflow in Admin → Settings updates approver slots for all future requests automatically.
- **Fallback logic** (appears hardcoded): only triggers if no workflow template is configured for the entity type — a safe guard, not the normal path.

**Wizard Refinements Applied (2025-04-15):**

*Travel-type-aware itinerary columns:*
- Added dynamic 8-col / 6-col itinerary grid: `[class.itinerary-grid-6col]` applied for `home_leave` travel type (no ETD/ETA columns)
- ETD and ETA columns hidden for `home_leave` and `external` travel types via `*ngIf`
- Departure Time and Arrival Time (time inputs) shown only for `external` travel type
- Flight Number label changes to "Flight / Transport Number" for `home_leave`
- Mode of Transport dropdown shown only for `external` (uses `modeOfTravel` formControlName)
- "Add Itinerary Segment" button shown only for Round Trip or when no segments exist (prevents one-way trip from having multiple legs)

*International travel — Advance Bank Details & Amount table:*
- Added `advanceBankAccountName`, `advanceBankName`, `advanceBankAccountNumber`, `advanceBankCurrency` (default TMT), `advanceBankBranchRemarks` form fields (shown only when `travelType === 'international'`)
- Added `advanceAmountItems` FormArray with per-row: `dateFrom*`, `dateTo*`, `lh`, `ma`, `oa`, `tr`, `oe`, `usd` (readonly computed), `remarks`; add/remove row controls
- USD column is disabled (readonly) and retrieved via `getRawValue()` in `prepareRequestData()`
- 10-column grid table with header row; all styled via new `.advance-amount-table`, `.advance-amount-header`, `.advance-amount-row` CSS classes

*Home Leave — Bank Details section:*
- Added optional bank details sub-section (same fields as International, no required markers) shown when `travelType === 'home_leave'`

*External Party — Information section:*
- Added `externalFullName*`, `externalOrganization*`, `externalRefToAuthorityLetter`, `externalCostCenter*` form fields shown when `travelType === 'external'`
- All fields mapped in `toBackendFormat()` / `toFrontendFormat()` and `patchFormFromRequest()`

*Design system compliance (unified):*
- All 7 section headers converted from plain `.section-header` to full-width gradient `.section-title` bar matching `transport-create` pattern: `linear-gradient(135deg, $primary-color, $primary-hover)`
- Replaced all hardcoded hex/rgba color values with design system variables: `vars.$primary-color`, `vars.$error-color`, `vars.$success-color`, `vars.$primary-lightest`, `vars.$primary-light`
- Fixed SCSS build error: replaced invalid `#{-vars.$variable}` interpolation with `calc(-1 * vars.$variable)` for negative margins
- Added `overflow: hidden` to `.wizard-container` to clip gradient to card border-radius
- Added `.wizard-header` gradient matching the same pattern
- Added mobile responsive recalculation of negative margins for reduced container padding

*Font & typography alignment:*
- `.form-label` color changed from `vars.$text-primary` to `vars.$gray-700` (matches accommodation/transport)
- `.form-control, .form-select` font-size changed from `vars.$font-size-base` (16px) to `vars.$font-size-sm` (14px)
- Added `font-weight: vars.$font-weight-normal` and `color: vars.$gray-900` to form controls
- Added `&::placeholder { color: vars.$gray-400 }` to form controls
- Added `textarea.form-control { font-family: inherit; resize: vertical }`
- `.btn` font-weight upgraded from `vars.$font-weight-medium` to `vars.$font-weight-semibold`
- Added explicit `font-family: vars.$font-primary` to `.wizard-container`

**Bug Fixes Applied (2025-04-16):**

*Departure date / return date / destination city showing N/A in detail view:*
- **Root cause**: `CombinedRequestItinerary.from_location` and `to_location` model fields have no `blank=True`. DRF auto-generated `allow_blank=False`, so any PATCH request that included an itinerary segment with empty locations was rejected with HTTP 400, silently blocking ALL flat fields (dates, city) from saving.
- **Fix** (`backend/combined_request/serializers.py`): Added explicit `from_location = serializers.CharField(max_length=255, allow_blank=True, default='')` and same for `to_location` in `CombinedRequestItinerarySerializer`.
- **Fix** (`backend/combined_request/views.py`): Added custom `update()` override to `CombinedRequestViewSet` with structured logging of incoming date/city fields and consistent `success_response` wrapper. `perform_update()` resets status to `Draft` and clears `submitted_at` when a request is edited.

*Combined admin list — request number not navigating on click:*
- **Root cause**: Route `{ path: 'detail/:id', component: CombinedAdminComponent }` loaded the admin list component again instead of a detail view. `viewRequest()` was navigating to `/admin/combined/detail/:id` which hit that broken route.
- **Fix** (`frontend/src/app/app.routes.ts`): Removed the broken `detail/:id` child route from `/admin/combined`.
- **Fix** (`combined-admin.component.ts`): Changed `viewRequest()` to navigate to `/combined/:id` (user-facing detail page), matching the visa admin pattern.

*Combined admin list — action buttons not matching visa admin pattern:*
- **Fix** (`combined-admin.component.ts`): Added `canReject()`, `canStartProcessing()`, and `startProcessing()` methods. View icon always shown; approve/reject shown for pending/submitted; start-processing shown for approved-only.
- **Fix** (`combined-admin.component.html`): Rewrote table section to match visa admin structure exactly — uppercase headers, module badges, proper action button conditionals with loading spinner on approve, pagination inside card-body.
- **Fix** (`combined-admin.component.scss`): Updated `.btn-icon` to circular `28×28px` with `border-radius: vars.$radius-full` (matching visa admin). Added `.badge-gray` class and `.pagination-container` block.

### Phase 7: Combined Processing Redesign ✅ COMPLETED (2025-04-18)
**Status**: Complete — pragmatic inline approach chosen over sub-component extraction.

**Decision**: Rewrite `combined-processing.component` as a self-contained module-aware processing hub with inline per-module forms. Sub-component extraction from the four standalone processing pages was deferred — the inline forms are simpler to maintain and the standalone pages remain untouched.

**Why pragmatic inline (not sub-component extraction):**
- Standalone processing pages (flights, transport, accommodation, visa) are untouched; no risk of regression.
- Combined processing uses simplified inline forms — appropriate since combined requests use direct entry by the clerk, not the full calendar availability UI. Accommodation room selection was later upgraded to real dropdowns in Phase 8.
- Results are stored in `additional_data.processing.{module}` JSONField — no new migrations needed.

**Implemented UI at `/admin/combined/processing?id=X`:**
```
List mode (no ?id):
  Tabs: Approved | Processing | Completed
  Request cards with module badges and Start/Continue/View buttons

Detail mode (?id=X):
  Header: request number, requestor, status badge, Back to list
  Progress bar: X / N modules completed (%)
  Per-module accordion cards:
    [Travel ✈]  Pending / Completed ✓   [▼]
      PNR, airline, flight no., airports, dates/times, notes → [Save & Complete]
    [Transport 🚗]  Pending / Completed ✓  [▼]
      Vehicle type/no., driver, contact, pickup/dropoff, route, booking ref → [Save & Complete]
    [Accommodation 🏨]  Pending / Completed ✓  [▼]
      Staff house, room, check-in/out, notes → [Save & Complete]
    [Visa 🛂]  Pending / Completed ✓  [▼]
      Visa number, issue/expiry dates, notes → [Save & Complete]
  Completed banner when all modules done.
```

**Backend `process-module` action** (no new migrations):
- `POST /api/combined/combined-requests/{id}/process-module/`
- Saves `processing_data` under `additional_data.processing.{module}` with `status: 'completed'`, `completed_at`, `completed_by`
- Sets `{module}_status = 'completed'` on the model
- Auto-transitions: `Approved → Processing` on first save; `Processing → Completed` when all included modules done

**Implementation steps:**
- [x] Backend: add `process_module` action to `CombinedRequestViewSet`
- [x] Frontend service: add `processModule()` method to `CombinedRequestService`
- [x] Rewrite `combined-processing.component.ts` — two-mode architecture (list / detail), per-module forms, progress tracking
- [x] Write `combined-processing.component.html` — list tabs + accordion detail forms
- [x] Write `combined-processing.component.scss` — design system tokens, module cards, progress bar
- [x] Update `combined-detail.component.html` — per-module "Processing Results" sections (flight booking, vehicle, room, visa number) shown when `additional_data.processing.{module}.status === 'completed'`
- [x] Update `combined-detail.component.scss` — `.processing-result-box` green success card

**Files modified:**
```
backend/combined_request/views.py                                                      ✅ Added process_module action
frontend/src/app/features/requests/combined/services/combined-request.service.ts      ✅ Added processModule()
frontend/src/app/features/admin/combined/components/combined-processing.component.ts  ✅ Full rewrite as module hub
frontend/src/app/features/admin/combined/components/combined-processing.component.html ✅ Written
frontend/src/app/features/admin/combined/components/combined-processing.component.scss ✅ Written
frontend/src/app/features/requests/combined/combined-detail.component.html            ✅ Added processing results sections
frontend/src/app/features/requests/combined/combined-detail.component.scss            ✅ Added .processing-result-box styles
```

---

### Phase 8: Post-Launch Fixes & Enhancements ✅ COMPLETED (2025-04-19)

**Visa Supporting Documents — full upload flow:**
- Fixed `uploadedDocuments: any[]` → `CombinedRequestDocument[]` (cleared TypeScript warning from previous session)
- Added handler methods to wizard: `onVisaDocumentSelected()`, `removeQueuedDocument()`, `deleteUploadedDocument(doc)`, `uploadQueuedDocuments(requestId)`
- Wired `uploadQueuedDocuments()` into both `saveAsDraft()` and `submitRequest()` — queued files are uploaded immediately after the request is created/updated
- Load existing visa documents into `uploadedDocuments` from `request.documents` when entering edit mode (`patchFormFromRequest`)
- Added **Supporting Documents** table to `combined-detail.component.html` — shows file link, document type, and uploader name
- Added `uploaded_by_name` `SerializerMethodField` to `CombinedRequestDocumentSerializer` (backend) — returns user's display name instead of raw ID
- Added `uploadedByName` field to `CombinedRequestDocument` frontend model interface and `toFrontendFormat()` mapping
- Fixed HTML template calling `deleteUploadedDocument(doc.id!)` → `deleteUploadedDocument(doc)` to match method signature

**Build error fixes (visa document upload UI):**
- Fixed `ngModel`/`ngModelOptions` on `<select>` — `FormsModule` is not imported in the wizard (reactive forms only). Replaced with `[value]="newDocumentType" (change)="newDocumentType = $any($event.target).value"`
- Properties (`visaDocumentQueue`, `uploadedDocuments`, etc.) were correctly defined but not yet referenced by any called method — resolved by wiring up handler calls

**Accommodation processing — real room selection from availability system:**
- Replaced hardcoded text inputs for "Staff House Name" and "Room Name" in `combined-processing.component.html` with dynamic dropdowns backed by `AccommodationService`
- Injected `AccommodationService` into `CombinedProcessingComponent`
- Added state: `staffHouses: AccommodationStaffHouse[]`, `availableRooms: AccommodationRoom[]`, `loadingRooms: boolean`
- `ngOnInit` now calls `getAllStaffHouses()` to populate the staff house dropdown on load
- Added `onStaffHouseChange()`: clears room selection, fetches rooms for selected house via `getAllRooms(staffHouseId)`, filters to `status === 'Available'` only, auto-populates `staffHouseName`
- Added `onRoomChange()`: auto-populates `roomName` from the selected room object (includes room type if set)
- Room dropdown disabled and shows contextual placeholder while loading or before a house is selected
- Warning shown inline if selected staff house has zero available rooms
- On re-edit: `preFillForms()` restores saved `staffHouseId`/`roomId` and reloads the room list so dropdowns reflect the saved selection
- Updated `AccommodationForm` interface: added `staffHouseId: number | null` and `roomId: number | null` alongside existing name fields
- Module summary (collapsed state) now also shows the check-in → check-out date range

**Files modified:**
```
backend/combined_request/serializers.py                                                ✅ Added uploaded_by_name field
frontend/src/app/features/requests/combined/models/combined-request.model.ts          ✅ Added uploadedByName to interface + mapping
frontend/src/app/features/requests/combined/combined-request-wizard.component.ts      ✅ Document handlers + upload-after-save wiring
frontend/src/app/features/requests/combined/combined-request-wizard.component.html    ✅ Fixed ngModel → [value]/(change), fixed delete call
frontend/src/app/features/requests/combined/combined-detail.component.html            ✅ Added Supporting Documents table
frontend/src/app/features/admin/combined/components/combined-processing.component.ts  ✅ AccommodationService, room selection state + methods
frontend/src/app/features/admin/combined/components/combined-processing.component.html ✅ Staff house + room dropdowns replacing text inputs
```

---

### Phase 9: Code Quality & Standards Compliance (2025-04-19)
**Status**: ✅ COMPLETE — all 11 items implemented; item 12 deferred (colour constants in shared file)

A full review of the combined request module was conducted against `CODE_STANDARDS_AND_REFACTORING_GUIDE.md`.

#### Overall Compliance Rating

| Layer | Rating | Score |
|-------|--------|-------|
| Backend | Medium | ~70% |
| Frontend | High | ~82% |

---

#### Backend Issues

**High priority:**

- **`views.py` — `export_pdf()` is 230+ lines** (lines ~800–1030). Extract PDF generation logic to `backend/utils/pdf_generator.py` as a dedicated `CombinedRequestPDFGenerator` class.
- **Hardcoded hex colours in PDF** (`colors.HexColor('#0d9488')` etc.). Create `backend/utils/pdf_style_constants.py` referencing design system tokens; import from there.
- **Duplicate permission-check logic in `get_queryset()`** — 30+ lines of manual role inspection that should use the project's `has_permission()` utility per standards section 5.2.

**Medium priority:**

- **Raw `Response()` calls** in error paths (e.g. `create()`) — replace with `validation_error_response()` / `error_response()` helpers for consistency.

**Low priority:**

- **`import traceback` inside method body** (~line 505) — move to top of file with other standard-library imports.

---

#### Frontend Issues

**High priority:**

- **`combined-processing.component.ts`** — uses manual `routeSub?.unsubscribe()` instead of `destroy$ + takeUntil`. Fix:
  ```typescript
  private destroy$ = new Subject<void>();
  this.route.queryParamMap.pipe(takeUntil(this.destroy$)).subscribe(…);
  ```
- **`combined-list.component.ts`** — does not extend `BaseListComponent<T>` like all other list components. Duplicates pagination/search/loading boilerplate.

**Medium priority:**

- **`combined-processing.component.ts`** — inline `getStatusClass()` method duplicates `StatusUtilsService`. Inject and delegate instead.
- **`combined-list.component.ts` line ~83** — `any` cast on filters parameter. Use `CombinedRequestFilters` interface.
- **`combined-detail.component.ts` line ~195** — `Record<string, any>` cast on `travelData`. Define typed `TravelDataStructure` interface.
- **`combined-processing.component.ts`** — `additional_data?.['processing']` typed as `Record<string, any>`. Define typed `ProcessingData` interface.
- **Inline styles in wizard HTML** — `style="font-size:0.75rem"` and `style="white-space: pre-line"` appear multiple times. Move to SCSS classes using `vars.$font-size-xs` per standards.

**Low priority:**

- **`visaDocError` state** — set inconsistently; replace with `toastService.error()` to match the rest of the app, then remove the string state variable.
- **`combined-request-wizard.component.ts`** — department-normalisation logic duplicated between `loadRequest` and `patchFormFromRequest`. Extract to a single private helper.

---

#### What Is Already Compliant ✅

- All components use `standalone: true` with correct imports
- `takeUntil(destroy$)` used correctly in wizard and detail components
- `get_serializer_class()` override in ViewSet
- Workflow integration via `WorkflowRouter.start_workflow_for_request()`
- `AdminActionLog` used in backend
- `ListStateService` used in list component
- `ToastService` / `ConfirmationService` used throughout
- Reactive forms with `FormBuilder` and `FormArray`
- Design-system SCSS variables used in wizard SCSS

---

#### Fix Priority Tracker

| # | Priority | Item | File | Status |
|---|----------|------|------|--------|
| 1 | 🔴 High | Extract `export_pdf()` to utility class | `backend/combined_request/views.py` | ✅ Done |
| 2 | 🔴 High | Replace `routeSub` with `destroy$+takeUntil` | `combined-processing.component.ts` | ✅ Done |
| 3 | 🔴 High | Extend `BaseListComponent<T>` | `combined-list.component.ts` | ✅ Done |
| 4 | 🟡 Medium | Remove `any` types → proper interfaces | `combined-list.ts`, `combined-detail.ts`, `combined-processing.ts` | ✅ Done |
| 5 | 🟡 Medium | Remove inline styles → SCSS classes | `combined-request-wizard.component.html` | ✅ Done |
| 6 | 🟡 Medium | Replace inline `getStatusClass()` with `StatusUtilsService` | `combined-processing.component.ts` | ✅ Done |
| 7 | 🟡 Medium | Replace raw `Response()` with error helpers | `views.py` | ✅ Done |
| 8 | 🟡 Medium | Use `has_permission()` utility in `get_queryset()` | `views.py` | ✅ Done |
| 9 | 🟢 Low | Move `import traceback` to top of file | `views.py` | ✅ Done |
| 10 | 🟢 Low | Consolidate `visaDocError` → `toastService` | `combined-request-wizard.component.ts` | ✅ Done |
| 11 | 🟢 Low | Extract department-normalisation helper | `combined-request-wizard.component.ts` | ✅ Done |
| 12 | 🟢 Low | Extract PDF colour constants to shared file | `views.py` + new `pdf_style_constants.py` | ⏸ Deferred |

---

### Phase 10: Second Code Review Pass (2026-04-19)

A second compliance review was run against `CODE_STANDARDS_AND_REFACTORING_GUIDE.md` after Phase 9 fixes were applied.

**Verified as already done (review agent incorrectly flagged these):**
- ✅ `export_pdf()` extracted to `pdf_generator.py` — views.py delegates in 3 lines
- ✅ `get_queryset()` uses `has_permission()` / `can_view_all()` utilities (imported line 20, used lines 158–177)
- ✅ All Phase 9 items 1–11 confirmed complete in source

**Remaining findings:**

| # | Priority | Item | File | Status |
|---|----------|------|------|--------|
| 1 | 🟡 Medium | Replace raw `Response(serializer.errors, …)` with `validation_error_response()` | `backend/combined_request/views.py` line 253 | ✅ Done |
| 2 | 🟡 Medium | Remove 5× `style="white-space: pre-line"` → `.pre-line` SCSS class | `combined-detail.component.html` lines 653, 710, 714, 740, 744 | ✅ Done |
| 3 | 🟢 Low | Replace hardcoded `#6ee7b7` with `vars.$success-light` | `combined-detail.component.scss` line 235 | ✅ Done |
| 4 | 🟢 Low | Extract PDF colour constant to shared constants file | `pdf_generator.py` line 12 | ⏸ Deferred |

---

### Phase 11: Deployment
- [ ] Production deployment
- [ ] User training/documentation
- [ ] Monitoring and support

---

## 11. FILE CHANGES SUMMARY

### Backend Files - Created ✅

```
backend/combined_request/
├── __init__.py                  ✅ Created (Phase 1)
├── admin.py                     ✅ Created (Phase 1, with inlines)
├── apps.py                      ✅ Created (Phase 1)
├── models.py                    ✅ Created (Phase 1, 6 models)
├── serializers.py               ✅ Created (Phase 1, 8 serializers)
├── views.py                     ✅ Complete (Phase 2, full ViewSet)
├── urls.py                      ✅ Complete (Phase 2, router config)
├── filters.py                   ⏳ Phase 3+ (if needed)
└── migrations/
    ├── __init__.py              ✅ Created
    └── 0001_initial.py          ✅ Created

backend/accounts/migrations/
└── 0029_add_combined_request_permissions.py  ✅ Created (Phase 1)
```

### Backend Files - Modified ✅

```
backend/tms_project/settings.py              ✅ Added to INSTALLED_APPS (Phase 1)
backend/tms_project/urls.py                  ✅ Registered combined URLs (Phase 2)
backend/utils/request_id_generator.py        ✅ Added CMB type (Phase 1)
backend/workflows/router.py                  ✅ Added combinedrequest mapping (Phase 2)
backend/workflows/management/commands/create_default_workflows.py  ✅ Added combined workflow (Phase 2)
backend/approvals/views.py                   ✅ Added combined requests support (Phase 2)
```

### Frontend Files - Modified ✅

```
frontend/src/app/core/models/permission.models.ts  ✅ Added 7 permissions (Phase 1)
```

### Files Still To Create (Phase 6+)

```
Backend:
├── backend/combined_request/
│   ├── filters.py               ⏳ Phase 6 (if needed)
│   └── tests/
│       ├── __init__.py          ⏳ Phase 6
│       ├── test_models.py
│       ├── test_views.py
│       └── test_workflow.py
```

### Frontend Files - Created ✅

```
frontend/src/app/features/requests/combined/
├── models/
│   └── combined-request.model.ts       ✅ Created (Phase 3)
├── services/
│   └── combined-request.service.ts     ✅ Created (Phase 3)
├── combined-request-wizard.component.ts   ✅ Created (Phase 3)
├── combined-request-wizard.component.html ✅ Created (Phase 3)
└── combined-request-wizard.component.scss ✅ Created (Phase 3)

frontend/src/app/features/admin/combined/
├── components/
│   ├── combined-admin.component.ts        ✅ Created (Phase 5)
│   ├── combined-admin.component.html      ✅ Created (Phase 5)
│   ├── combined-admin.component.scss      ✅ Created (Phase 5)
│   ├── combined-processing.component.ts   ✅ Created (Phase 5)
│   ├── combined-processing.component.html ✅ Created (Phase 5)
│   └── combined-processing.component.scss ✅ Created (Phase 5)
```

### Files Modified ✅

```
Backend:
├── backend/tms_project/settings.py          ✅ Added 'combined_request' to INSTALLED_APPS (Phase 1)
├── backend/tms_project/urls.py              ✅ Added combined_request URLs (Phase 2)
├── backend/workflows/router.py              ✅ Added combined_request entity type (Phase 2)
├── backend/approvals/views.py               ✅ Included combined requests in unified approvals (Phase 2)
├── backend/workflows/management/commands/create_default_workflows.py ✅ Added workflow template (Phase 2)

Frontend:
├── frontend/src/app/app.routes.ts           ✅ Added combined request + admin routes (Phase 3, 5)
├── frontend/src/app/core/models/permission.models.ts  ✅ Added 7 new permissions (Phase 1)
├── frontend/src/app/core/services/rbac.service.ts     ✅ Added 'combined' module support (Phase 5)
├── frontend/src/app/shared/components/sidebar/sidebar.component.ts   ✅ Added Combined Admin menu (Phase 5)
├── frontend/src/app/shared/components/sidebar/sidebar.component.html ✅ Added Combined Admin link (Phase 5)
├── frontend/src/app/features/requests/components/request-type-selection/ ✅ Added combined option (Phase 3)
```

---

## 12. TECHNICAL CONSIDERATIONS

### 12.1 Form State Management

For the multi-step wizard, consider using:
- Angular Reactive Forms with FormGroups per step
- Store wizard state in a service (not lost on navigation within wizard)
- Auto-save draft functionality

### 12.2 Performance Considerations

- Lazy load the combined request module
- Use pagination for document lists
- Consider chunked file uploads for documents
- Cache form data in localStorage for recovery

### 12.3 Mobile Responsiveness

- Wizard should be mobile-friendly
- Consider collapsible sections on mobile
- Touch-friendly form controls

### 11.4 Validation Strategy

```typescript
// Cross-step validation rules
const validationRules = {
  // Return date must be after departure date
  returnDateAfterDeparture: (form) => form.returnDate > form.departureDate,

  // Accommodation checkout must be on or before return date
  checkoutBeforeReturn: (form) => form.accommodationCheckout <= form.returnDate,

  // Transport dates must be within travel dates
  transportWithinTravelDates: (form) => {
    return form.transportSegments.every(s =>
      s.pickupDatetime >= form.departureDate &&
      s.pickupDatetime <= form.returnDate
    );
  },

  // Visa destination must match travel destination
  visaDestinationMatch: (form) =>
    !form.includeVisa || form.visaDestinationCountry === form.destinationCountry
};
```

---

## 12. RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep | Medium | High | Define MVP clearly, defer enhancements |
| Complex workflow bugs | Medium | High | Comprehensive testing, staged rollout |
| User adoption | Low | Medium | Training, clear documentation, intuitive UI |
| Performance issues | Low | Medium | Lazy loading, pagination, optimization |
| Integration conflicts | Low | Medium | Thorough code review, feature flags |

---

## 13. SUCCESS METRICS

- **Adoption Rate**: % of users using combined vs. individual requests
- **Completion Rate**: % of started combined requests that are submitted
- **Processing Time**: Average time from submission to final approval
- **Error Rate**: Number of rejected requests due to data issues
- **User Satisfaction**: Survey feedback on new feature

---

## 14. CONCLUSION

The Combined Request Module is **highly feasible** and aligns well with the existing TMS architecture. The recommended approach is to create a unified model with a single workflow template that uses conditional steps based on included modules.

### Key Recommendations:

1. **Start with MVP**: Include core fields first, add advanced features later
2. **Reuse Components**: Leverage existing form components where possible
3. **Test Thoroughly**: Especially workflow logic with various module combinations
4. **Train Users**: Provide clear documentation and training
5. **Monitor & Iterate**: Gather feedback and improve based on usage patterns

### Estimated Timeline: 6-8 weeks

This estimate assumes dedicated development resources and no major architectural changes to existing modules.

---

## APPENDIX A: Request Number Format

For Combined Requests, use format:
```
CMB-{YYYYMMDD}-{HHMM}-{DEST}-{RANDOM}
Example: CMB-20250415-0930-DXB-A7K2
```

## APPENDIX B: Status Flow

```
draft → submitted → pending_lm_approval → pending_hod_approval →
pending_transport_review (if applicable) → pending_accommodation_review (if applicable) →
pending_visa_review (if applicable) →
approved → processing → completed

At any step: → rejected / → cancelled
```
