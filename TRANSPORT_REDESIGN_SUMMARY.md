# Transport Module Redesign Summary

**Date:** 2025-10-20
**Status:** Backend ✅ Complete | Frontend 🔄 In Progress (40%)

---

## Overview

The transport module has been completely redesigned to match the React source project (`pctsb.syntra`) exactly. This redesign eliminates all cost-related fields and simplifies the data structure to use JSON arrays instead of separate models.

---

## ✅ Backend Changes (100% Complete)

### 1. Model Redesign

**File:** `backend/transport/models.py`

#### Removed Fields:
- ❌ `title` - Not in React source
- ❌ `transport_type` - Moved to JSON array items
- ❌ `number_of_passengers` - Moved to JSON array items
- ❌ `passenger_names` - Not in React source
- ❌ `vehicle_type` - Moved to booking_details
- ❌ `special_requirements` - Not in React source
- ❌ `estimated_cost` - NO COST FIELDS
- ❌ `currency` - NO COST FIELDS
- ❌ `additional_data` - Replaced with specific JSON fields
- ❌ `TransportSegment` model - Replaced with JSON field

#### Added Fields:
- ✅ `requestor_name` (CharField, max_length=255)
- ✅ `staff_id` (CharField, max_length=50)
- ✅ `department` (CharField, max_length=255)
- ✅ `position` (CharField, max_length=255)
- ✅ `transport_details` (JSONField) - Array of transport detail objects
- ✅ `tsr_reference` (CharField, blank=True, null=True)
- ✅ `confirm_policy` (BooleanField, default=False)
- ✅ `confirm_manager_approval` (BooleanField, default=False)
- ✅ `confirm_terms_and_conditions` (BooleanField, default=False)
- ✅ `booking_details` (JSONField, blank=True, null=True)

#### Updated Status Choices:
```python
STATUS_CHOICES = [
    ('Draft', 'Draft'),
    ('Pending Department Focal', 'Pending Department Focal'),
    ('Pending Line Manager', 'Pending Line Manager'),
    ('Pending HOD', 'Pending HOD'),
    ('Approved', 'Approved'),
    ('Processing with Transport Admin', 'Processing with Transport Admin'),
    ('Completed', 'Completed'),
    ('Rejected', 'Rejected'),
    ('Cancelled', 'Cancelled'),
]
```

### 2. Transport Details JSON Structure

Each item in `transport_details` array:
```json
{
  "date": "2024-01-15",
  "day": "Monday",
  "from": "Riyadh Office",
  "to": "Jeddah Airport",
  "departureTime": "08:00",
  "transportType": "Intercity",
  "numberOfPassengers": 3
}
```

**Transport Types:**
- Local
- Intercity
- Airport Transfer
- Charter
- Other

### 3. Booking Details JSON Structure

Filled by transport admin:
```json
{
  "vehicleType": "SUV",
  "vehicleNumber": "ABC-123",
  "driverName": "John Doe",
  "driverContact": "+966...",
  "pickupTime": "07:45",
  "dropoffTime": "14:30",
  "actualRoute": "Route details",
  "bookingReference": "BK-2024-001",
  "additionalNotes": "Special instructions"
}
```

### 4. Migration

**File:** `backend/transport/migrations/0002_transport_redesign_to_match_react.py`

- Renamed old fields with `_deprecated_` prefix for backward compatibility
- Added all new fields with default values
- Migration applied successfully ✅

### 5. Serializers Rewrite

**File:** `backend/transport/serializers.py`

Completely rewritten serializers:

1. **TransportRequestSerializer** - Basic list view serializer
   - Includes all new fields
   - Calculates `detail_count` from JSON array
   - Validates transport_details structure

2. **TransportRequestDetailSerializer** - Detail view with nested data
   - Extends TransportRequestSerializer
   - Includes approval_steps

3. **TransportRequestCreateSerializer** - Create/submit serializer
   - NO cost fields
   - Validates required fields in transport_details array
   - Validates confirmations for submission

4. **TransportRequestUpdateSerializer** - Update serializer
   - Can only update Draft or Rejected requests
   - Validates transport_details if provided

5. **ApprovalActionSerializer** - Approval actions (unchanged)

6. **VehicleAssignmentSerializer** - Marked as deprecated (kept for backward compatibility)

### 6. Views Update

**File:** `backend/transport/views.py`

**TransportRequestViewSet changes:**

1. **perform_create()** - Auto-populates requestor info:
```python
def perform_create(self, serializer):
    user = self.request.user
    
    # Auto-populate requestor information if not provided
    validated_data = serializer.validated_data
    if not validated_data.get('requestor_name'):
        validated_data['requestor_name'] = user.get_full_name() or user.email
    if not validated_data.get('staff_id'):
        validated_data['staff_id'] = getattr(user, 'employee_id', '') or getattr(user, 'staff_id', '')
    # ... etc
```

2. **submit()** - Updated validation:
   - Checks `transport_details` instead of segments
   - Sets status to 'Pending Department Focal'

3. **TransportSegmentViewSet** - Commented out (deprecated)

### 7. Admin Interface Update

**File:** `backend/transport/admin.py`

- Updated list_display to show new fields
- Removed cost and segment fields
- Added JSON field displays for transport_details and booking_details
- Updated fieldsets for better organization

### 8. URL Configuration

**File:** `backend/transport/urls.py`

- Commented out segments endpoint (deprecated)
- Kept other endpoints unchanged

---

## 🔄 Frontend Changes (40% Complete)

### 1. TypeScript Models ✅

**File:** `frontend/src/app/features/transport/models/transport.model.ts`

Created comprehensive interfaces matching React source:

- `TransportRequestStatus` - 9 status types
- `TransportType` - 5 transport types
- `TransportRequestorInformation` - Requestor data structure
- `TransportDetail` - Individual journey detail
- `TransportRequestData` - Core request data
- `TransportApprovalSubmissionData` - Confirmation checkboxes
- `TransportRequestForm` - Complete form structure
- `TransportApprovalStep` - Approval workflow step
- `TransportBookingDetails` - Admin booking info
- `TransportRequestSummary` - List view data

**Helper Functions:**
- `toBackendFormat()` - Converts frontend camelCase to backend snake_case
- `toFrontendFormat()` - Converts backend data to frontend structure

### 2. Transport Create Component ✅

**File:** `frontend/src/app/features/transport/components/transport-create/transport-create.component.ts`

Completely rewritten (203 lines):

**Form Structure:**
```typescript
transportForm = {
  // Requestor information
  requestorName: string (required)
  staffId: string (required)
  department: string (required)
  position: string

  // Request details
  purpose: string (required)
  tsrReference: string

  // Transport details array (FormArray)
  transportDetails: [
    {
      date: date (required)
      day: string (auto-filled from date)
      from: string (required)
      to: string (required)
      departureTime: time (required)
      transportType: select (required)
      numberOfPassengers: number (required, min: 1)
    }
  ]

  // Submission confirmations
  additionalComments: string
  confirmPolicy: boolean (required for submit)
  confirmManagerApproval: boolean (required for submit)
  confirmTermsAndConditions: boolean
}
```

**Key Features:**
- Auto-loads user details from AuthService
- Dynamic FormArray for transport details
- Auto-fills day name from selected date
- Validates all required fields before submission
- Two submit modes:
  - Save Draft (status='Draft')
  - Submit Request (status='Pending Department Focal')
- Uses `toBackendFormat()` helper for API calls

### 3. Transport Create Component HTML ✅

**File:** `frontend/src/app/features/transport/components/transport-create/transport-create.component.html`

Completely rewritten (212 lines):

**Sections:**
1. Loading State
2. Page Header
3. Requestor Information (4 fields)
4. Request Details (purpose, TSR reference)
5. Transport Details (dynamic array with 7 fields each)
6. Approval & Submission Confirmations (3 checkboxes + comments)
7. Form Actions (Cancel, Save Draft, Submit)

**Features:**
- Validation error messages for all required fields
- Add/Remove transport detail buttons
- Auto-fill day from date selection
- Disabled states while submitting
- Confirmation checkboxes with required indicators

### 4. Transport Create Component SCSS ⏳

**File:** `frontend/src/app/features/transport/components/transport-create/transport-create.component.scss`

**Status:** Pending
**Next:** Match React design with teal color scheme

---

## ⏳ Pending Frontend Tasks

### 1. Complete Transport Create SCSS (tsp_2)

Match React design:
- Card-based layout
- Teal color scheme (#0d9488)
- Responsive grid
- Form validation styling

### 2. Redesign Transport Detail Component (tsp_3)

**File:** `frontend/src/app/features/transport/components/transport-detail/transport-detail.component.ts`

Display all fields:
- Requestor information
- Purpose and TSR reference
- Transport details table
- Confirmation status
- Booking details (if assigned)
- Approval workflow timeline
- Status-based action buttons

### 3. Update Transport Service (tsp_4)

**File:** `frontend/src/app/features/transport/services/transport.service.ts`

- Update API calls to use new field names
- Use `toBackendFormat()` and `toFrontendFormat()` helpers
- Remove cost-related methods

### 4. Update Transport List Component (tsp_5)

**File:** `frontend/src/app/features/transport/components/transport-list/transport-list.component.ts`

Display new fields:
- Requestor name and department
- Purpose (truncated)
- Detail count
- Status
- Submitted date

### 5. End-to-End Testing (tsp_6)

Test complete flow:
1. Create transport request
2. Submit to workflow
3. Admin assigns vehicle (booking_details)
4. View request details
5. Approve/reject

### 6. Update Documentation (tsp_7)

Update ROADMAP.md with completion status

---

## Key Differences from Old Structure

### Before (Cost-focused)
```
TransportRequest {
  title: string
  transport_type: string
  number_of_passengers: number
  estimated_cost: decimal
  currency: string
  segments: [
    TransportSegment {
      from_location: string
      to_location: string
      segment_cost: decimal
      ...
    }
  ]
}
```

### After (Simplified, NO costs)
```
TransportRequest {
  requestor_name: string
  staff_id: string
  department: string
  position: string
  purpose: string
  transport_details: [
    {
      date: date
      from: string
      to: string
      departureTime: time
      transportType: enum
      numberOfPassengers: number
    }
  ]
  confirm_policy: boolean
  confirm_manager_approval: boolean
  booking_details: {
    vehicleType: string
    driverName: string
    ...
  }
}
```

---

## API Endpoints

Base URL: `/api/transport/`

### Transport Requests

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/requests/` | List all requests (with filters) |
| POST | `/requests/` | Create new request |
| GET | `/requests/:id/` | Get request details |
| PUT | `/requests/:id/` | Update request (Draft/Rejected only) |
| PATCH | `/requests/:id/` | Partial update |
| DELETE | `/requests/:id/` | Delete request |
| POST | `/requests/:id/submit/` | Submit request to workflow |
| POST | `/requests/:id/approve/` | Approve request |
| POST | `/requests/:id/reject/` | Reject request |
| POST | `/requests/:id/cancel/` | Cancel request |
| GET | `/requests/pending-approvals/` | Get pending approvals |

### Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/approval-steps/` | List approval steps |
| GET | `/vehicle-assignments/` | List vehicle assignments (deprecated) |

---

## Testing Checklist

### Backend ✅
- [x] Django check passes (0 issues)
- [x] Migration applied successfully
- [x] Models created correctly
- [x] Serializers validate data properly
- [x] Views auto-populate requestor info
- [x] Admin interface displays correctly

### Frontend 🔄
- [x] TypeScript models created
- [x] Create component TypeScript completed
- [x] Create component HTML completed
- [ ] Create component SCSS completed
- [ ] Detail component redesigned
- [ ] Service updated
- [ ] List component updated
- [ ] Build compiles successfully
- [ ] End-to-end flow works

---

## Next Steps

1. **Complete Transport Create SCSS** - Match React design
2. **Redesign Transport Detail Component** - All 3 files (TS, HTML, SCSS)
3. **Update Transport Service** - Use new conversion helpers
4. **Update Transport List Component** - Display new fields
5. **Test Complete Flow** - Create, submit, approve, view
6. **Update ROADMAP.md** - Mark transport module as complete

---

## Files Modified

### Backend (6 files)
1. `backend/transport/models.py` - Complete model redesign
2. `backend/transport/serializers.py` - Complete rewrite
3. `backend/transport/views.py` - Updated for JSON structure
4. `backend/transport/admin.py` - Updated field displays
5. `backend/transport/urls.py` - Removed deprecated endpoints
6. `backend/transport/migrations/0002_transport_redesign_to_match_react.py` - Migration file

### Frontend (3 files)
1. `frontend/src/app/features/transport/models/transport.model.ts` - New file (212 lines)
2. `frontend/src/app/features/transport/components/transport-create/transport-create.component.ts` - Rewritten (203 lines)
3. `frontend/src/app/features/transport/components/transport-create/transport-create.component.html` - Rewritten (212 lines)

### Documentation (1 file)
1. `TRANSPORT_REDESIGN_SUMMARY.md` - This file

---

**Status:** Backend 100% ✅ | Frontend 40% 🔄
**Estimated Time to Complete Frontend:** 4-6 hours
**Priority:** High (blocking transport request submissions)
