# Visa Full Implementation Plan - React Design in Angular

## Date: 2025-10-23

---

## ✅ Backend Complete

### What's Done:

1. **Models** - Already have all required fields:
   - Section A: Personal Information (DOB, citizenship, passport, education, etc.)
   - Section B: Request Type (LOI/VISA/WORK_PERMIT, entry type, category)
   - Travel Details (destination, purpose, dates, itinerary)
   - Approval workflow fields (focal, manager, HOD, CEO)
   - Document management

2. **Serializers** - Created 4 specialized serializers:
   - `VisaApplicationListSerializer` - Lightweight for listings
   - `VisaApplicationDetailSerializer` - Full details with nested workflow & documents
   - `VisaApplicationCreateUpdateSerializer` - For form submissions
   - `VisaApprovalStepSerializer` & `VisaDocumentSerializer` - For related models

3. **API Endpoints** - Enhanced with:
   - List/Create/Update/Delete visa applications
   - `/pending-approvals/` - Get applications needing approval
   - `/my-applications/` - Get current user's applications
   - `/{id}/approve/` - Approve at specific step
   - `/{id}/reject/` - Reject application
   - Document management by visa

---

## 📋 Frontend Implementation Needed

### Phase 1: Angular Service & Interfaces

**File:** `frontend/src/app/core/services/visa.service.ts`

```typescript
// Create comprehensive TypeScript interfaces matching backend

export interface VisaApplication {
  // Basic Info
  id: string;
  user?: string;
  user_email?: string;
  applicant_name: string;
  requestor_name: string;
  staff_id?: string;
  department?: string;
  position?: string;
  email?: string;

  // Section A: Personal Information
  date_of_birth?: string;
  place_of_birth?: string;
  citizenship?: string;
  passport_number?: string;
  passport_place_of_issuance?: string;
  passport_date_of_issuance?: string;
  passport_expiry_date?: string;
  contact_telephone?: string;
  home_address?: string;
  education_details?: string;
  current_employer_name?: string;
  current_employer_address?: string;
  marital_status?: string;
  family_information?: string;

  // Section B: Request Type
  request_type: 'LOI' | 'VISA' | 'WORK_PERMIT';
  approximately_arrival_date?: string;
  duration_of_stay?: string;
  visa_entry_type?: 'Multiple' | 'Single' | 'Double';
  work_visit_category?: string;
  application_fees_borne_by?: string;
  cost_centre_number?: string;

  // Travel Details
  destination: string;
  travel_purpose: string;
  visa_type: string;
  trip_start_date?: string;
  trip_end_date?: string;
  itinerary_details?: string;

  // Approval workflow
  line_focal_person?: string;
  line_focal_dept?: string;
  line_focal_contact?: string;
  line_focal_date?: string;
  sponsoring_dept_head?: string;
  sponsoring_dept_head_dept?: string;
  sponsoring_dept_head_contact?: string;
  sponsoring_dept_head_date?: string;
  ceo_approval_name?: string;
  ceo_approval_date?: string;

  // Status & metadata
  status: string;
  submitted_date?: string;
  last_updated_date?: string;
  created_at?: string;
  updated_at?: string;

  // Nested
  approval_workflow?: VisaApprovalStep[];
  documents?: VisaDocument[];
}

export interface VisaApprovalStep {
  id: string;
  step_role: string;
  step_name: string;
  status: string;
  step_date: string;
  comments?: string;
}

export interface VisaDocument {
  id: string;
  document_name: string;
  document_path: string;
  document_type?: string;
  uploaded_at: string;
  uploaded_by?: string;
}

// Service methods
@Injectable({ providedIn: 'root' })
export class VisaService {
  private baseUrl = `${environment.apiUrl}/visa`;

  getApplications(): Observable<VisaApplication[]>
  getApplication(id: string): Observable<VisaApplication>
  createApplication(data: Partial<VisaApplication>): Observable<VisaApplication>
  updateApplication(id: string, data: Partial<VisaApplication>): Observable<VisaApplication>
  deleteApplication(id: string): Observable<void>
  getPendingApprovals(): Observable<VisaApplication[]>
  getMyApplications(): Observable<VisaApplication[]>
  approve(id: string, stepRole: string, comments: string): Observable<VisaApplication>
  reject(id: string, stepRole: string, comments: string): Observable<VisaApplication>
  getDocuments(visaId: string): Observable<VisaDocument[]>
  uploadDocument(visaId: string, file: File, type: string): Observable<VisaDocument>
}
```

---

### Phase 2: Visa Form Component (React Design)

**Files:**
- `frontend/src/app/visa/visa-form/visa-form.component.ts`
- `frontend/src/app/visa/visa-form/visa-form.component.html`
- `frontend/src/app/visa/visa-form/visa-form.component.scss`

**Features:**
- Multi-section form matching React design
- Section A: Particulars of Applicant (11 fields)
- Section B: Type of Request (7 fields)
- Section C: Travel Details (5 fields)
- Date pickers with validation
- Dropdown for visa types and categories
- File upload for passport copy and supporting documents
- Real-time validation
- Form state management (draft/submit)

**Form Structure:**
```html
<div class="visa-application-form">
  <div class="form-header">
    <h1>REQUEST FOR LOI, VISA & WORK PERMIT</h1>
  </div>

  <form [formGroup]="visaForm" (ngSubmit)="onSubmit()">
    <!-- Section A: Particulars of Applicant -->
    <div class="card form-section">
      <div class="card-header">
        <h2><i class="bi bi-person"></i> Section A: PARTICULARS OF APPLICANT</h2>
      </div>
      <div class="card-body">
        <div class="form-subsection">
          <h3>Personal Information</h3>
          <div class="row">
            <div class="col-md-4">
              <label>Full Name *</label>
              <input formControlName="applicantName" class="form-control">
            </div>
            <div class="col-md-4">
              <label>Date of Birth *</label>
              <input type="date" formControlName="dateOfBirth" class="form-control">
            </div>
            <div class="col-md-4">
              <label>Place of Birth *</label>
              <input formControlName="placeOfBirth" class="form-control">
            </div>
            <!-- More fields... -->
          </div>
        </div>

        <div class="form-subsection">
          <h3>Passport Information</h3>
          <!-- Passport fields... -->
        </div>

        <div class="form-subsection">
          <h3>Employment Information</h3>
          <!-- Employment fields... -->
        </div>
      </div>
    </div>

    <!-- Section B: Type of Request -->
    <div class="card form-section">
      <div class="card-header">
        <h2><i class="bi bi-file-text"></i> Section B: TYPE OF REQUEST</h2>
      </div>
      <div class="card-body">
        <!-- Request type fields... -->
      </div>
    </div>

    <!-- Section C: Travel Details -->
    <div class="card form-section">
      <div class="card-header">
        <h2><i class="bi bi-airplane"></i> Section C: TRAVEL DETAILS</h2>
      </div>
      <div class="card-body">
        <!-- Travel fields... -->
      </div>
    </div>

    <!-- Form Actions -->
    <div class="form-actions">
      <button type="button" class="btn btn-secondary" (click)="onCancel()">Cancel</button>
      <button type="submit" class="btn btn-primary" [disabled]="!visaForm.valid || isSubmitting">
        <span *ngIf="isSubmitting" class="spinner-border spinner-border-sm me-2"></span>
        {{ isEditMode ? 'Update Application' : 'Submit Application' }}
      </button>
    </div>
  </form>
</div>
```

---

### Phase 3: Visa Detail View Component (React Design)

**Files:**
- `frontend/src/app/visa/visa-detail/visa-detail.component.ts`
- `frontend/src/app/visa/visa-detail/visa-detail.component.html`
- `frontend/src/app/visa/visa-detail/visa-detail.component.scss`

**Features:**
- Comprehensive read-only view matching React VisaApplicationView
- Header card with application ID and status badge
- Section A: Personal Information card
- Section B: Request Type card
- Section C: Travel Details card
- Approval Workflow card (timeline display)
- Documents Management card
- Print-friendly layout
- Action buttons (Edit, Approve, Reject based on permissions)

**Template Structure:**
```html
<div class="visa-detail-view">
  <!-- Header Card -->
  <div class="card header-card">
    <div class="card-header text-center">
      <h1>REQUEST FOR LOI, VISA & WORK PERMIT</h1>
      <div class="application-info">
        Application ID: {{ visa.id }} | Status:
        <span class="badge" [ngClass]="getStatusClass(visa.status)">
          {{ visa.status }}
        </span>
      </div>
    </div>
  </div>

  <!-- Section A: Personal Information -->
  <div class="card info-card">
    <div class="card-header">
      <h2><i class="bi bi-person-circle"></i> Section A: PARTICULARS OF APPLICANT</h2>
    </div>
    <div class="card-body">
      <div class="info-subsection">
        <h3>Personal Information</h3>
        <div class="info-grid">
          <div class="info-item">
            <label>Full Name</label>
            <div class="info-value">{{ visa.applicant_name }}</div>
          </div>
          <div class="info-item">
            <label>Date of Birth</label>
            <div class="info-value">{{ visa.date_of_birth | date }}</div>
          </div>
          <!-- More fields... -->
        </div>
      </div>

      <div class="info-subsection">
        <h3>Passport Information</h3>
        <!-- Passport info... -->
      </div>

      <div class="info-subsection">
        <h3>Employment Information</h3>
        <!-- Employment info... -->
      </div>
    </div>
  </div>

  <!-- Section B: Request Type -->
  <div class="card info-card">
    <!-- Request type details... -->
  </div>

  <!-- Section C: Travel Details -->
  <div class="card info-card">
    <!-- Travel details... -->
  </div>

  <!-- Approval Workflow -->
  <div class="card workflow-card" *ngIf="visa.approval_workflow?.length">
    <div class="card-header">
      <h2><i class="bi bi-check-circle"></i> Approval Workflow</h2>
    </div>
    <div class="card-body">
      <div class="workflow-timeline">
        <div class="workflow-step" *ngFor="let step of visa.approval_workflow">
          <div class="step-icon" [ngClass]="getStepIconClass(step.status)">
            <i class="bi" [ngClass]="getStepIcon(step.status)"></i>
          </div>
          <div class="step-content">
            <div class="step-title">{{ step.step_name }}</div>
            <div class="step-status">{{ step.status }}</div>
            <div class="step-date">{{ step.step_date | date:'medium' }}</div>
            <div class="step-comments" *ngIf="step.comments">{{ step.comments }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Documents -->
  <div class="card documents-card">
    <div class="card-header">
      <h2><i class="bi bi-paperclip"></i> Documents</h2>
      <button class="btn btn-sm btn-primary" (click)="openDocumentUpload()" *ngIf="canManageDocuments">
        <i class="bi bi-upload"></i> Upload Document
      </button>
    </div>
    <div class="card-body">
      <div class="documents-grid">
        <div class="document-item" *ngFor="let doc of visa.documents">
          <i class="bi bi-file-earmark-pdf"></i>
          <div class="document-name">{{ doc.document_name }}</div>
          <div class="document-meta">
            {{ doc.uploaded_by }} • {{ doc.uploaded_at | date:'short' }}
          </div>
          <button class="btn btn-sm btn-outline-secondary" (click)="downloadDocument(doc)">
            <i class="bi bi-download"></i>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Action Buttons -->
  <div class="action-buttons" *ngIf="canTakeAction">
    <button class="btn btn-outline-secondary" routerLink="/visa">Back to List</button>
    <button class="btn btn-outline-primary" (click)="onEdit()" *ngIf="canEdit">
      <i class="bi bi-pencil"></i> Edit
    </button>
    <button class="btn btn-success" (click)="onApprove()" *ngIf="canApprove">
      <i class="bi bi-check-circle"></i> Approve
    </button>
    <button class="btn btn-danger" (click)="onReject()" *ngIf="canReject">
      <i class="bi bi-x-circle"></i> Reject
    </button>
    <button class="btn btn-outline-secondary" (click)="onPrint()">
      <i class="bi bi-printer"></i> Print
    </button>
  </div>
</div>
```

---

### Phase 4: Visa List Component (Enhanced)

**Files:**
- `frontend/src/app/visa/visa-list/visa-list.component.ts`
- `frontend/src/app/visa/visa-list/visa-list.component.html`
- `frontend/src/app/visa/visa-list/visa-list.component.scss`

**Enhancements:**
- Add status badges with colors
- Add request type column
- Add visa entry type column
- Improve filters (status, request type, visa entry type, date range)
- Add sorting
- Add pagination
- Quick action buttons (View, Edit, Delete)

---

### Phase 5: Styling (React Design)

**Files:** Component SCSS files

**Design Elements:**
- Card-based layout
- Teal color scheme (#0d9488)
- Section headers with icons
- Info boxes with blue background for event types
- Timeline design for approval workflow
- Print styles
- Responsive grid layouts
- Badge components for status

**SCSS Structure:**
```scss
// Visa form and detail styles
.visa-application-form,
.visa-detail-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;

  .form-header,
  .card-header {
    background: #f8f9fa;
    border-bottom: 2px solid #0d9488;
    padding: 1.5rem;

    h1, h2 {
      color: #0d9488;
      font-weight: 600;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
  }

  .form-section,
  .info-card {
    margin-bottom: 2rem;
    border: 1px solid #dee2e6;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .form-subsection,
  .info-subsection {
    margin-bottom: 1.5rem;

    h3 {
      font-size: 1.125rem;
      font-weight: 600;
      color: #212529;
      margin-bottom: 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid #e5e7eb;
    }
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
  }

  .info-item {
    label {
      font-size: 0.75rem;
      font-weight: 600;
      color: #6c757d;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 0.25rem;
      display: block;
    }

    .info-value {
      font-size: 0.9375rem;
      color: #212529;
    }
  }

  // Workflow timeline
  .workflow-timeline {
    position: relative;
    padding-left: 2rem;

    &::before {
      content: '';
      position: absolute;
      left: 1rem;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #e5e7eb;
    }

    .workflow-step {
      position: relative;
      padding-bottom: 2rem;

      .step-icon {
        position: absolute;
        left: -2rem;
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 50%;
        background: white;
        border: 2px solid #e5e7eb;
        display: flex;
        align-items: center;
        justify-content: center;

        &.approved {
          background: #14b8a6;
          border-color: #14b8a6;
          color: white;
        }

        &.rejected {
          background: #dc3545;
          border-color: #dc3545;
          color: white;
        }

        &.pending {
          background: #fbbf24;
          border-color: #fbbf24;
          color: white;
        }
      }
    }
  }
}

// Print styles
@media print {
  .visa-detail-view {
    .action-buttons {
      display: none !important;
    }

    .card {
      break-inside: avoid;
      box-shadow: none !important;
      border: 1px solid #dee2e6 !important;
    }
  }
}
```

---

## 🔄 Implementation Order

1. ✅ **Backend API** - COMPLETE
2. **Phase 1: Service & Interfaces** - Create TypeScript interfaces and service methods
3. **Phase 2: Visa Form** - Build comprehensive multi-section form
4. **Phase 3: Detail View** - Build detailed read-only view with workflow
5. **Phase 4: List Enhancement** - Enhance list with filters and actions
6. **Phase 5: Styling** - Apply React design styles throughout

---

## 📝 Key Differences from Current Implementation

### Current Angular (Simple):
- Basic table list
- Simple form with essential fields
- Minimal detail view
- No approval workflow display
- No document management UI

### React Design (Comprehensive):
- Detailed multi-section form (A, B, C)
- All LOI request fields
- Comprehensive detail view with sections
- Visual approval workflow timeline
- Document management interface
- Print-friendly layouts
- Status badges with colors
- Better UX with field grouping

---

## 🚀 Quick Start Implementation

To implement this fully, start with:

1. **Service layer** - Copy/paste the TypeScript interfaces and service methods
2. **Form component** - Build section by section (A → B → C)
3. **Detail component** - Build each card one at a time
4. **Test workflow** - Create → View → Edit → Approve → Reject

---

## ✅ Testing Checklist

After implementation:

- [ ] Can create new visa application with all fields
- [ ] All sections (A, B, C) display correctly
- [ ] Date pickers work properly
- [ ] Dropdowns have correct options
- [ ] Form validation works
- [ ] Can view application detail
- [ ] All sections visible in detail view
- [ ] Approval workflow displays correctly
- [ ] Can approve/reject (with permissions)
- [ ] Documents can be uploaded
- [ ] Documents can be viewed/downloaded
- [ ] Print layout works
- [ ] List view shows all applications
- [ ] Filters work (status, type, dates)
- [ ] Can edit existing application
- [ ] Status badges display correctly

---

**Ready to implement!** All backend is done, just need frontend components.
