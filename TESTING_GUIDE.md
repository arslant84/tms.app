# TMS Application - End-to-End Testing Guide

**Date:** October 30, 2025
**Version:** 1.0
**Status:** Ready for Testing

---

## Prerequisites

### 1. Backend Setup
```bash
cd backend
python manage.py migrate  # Already done ✅
python manage.py runserver
```

### 2. Frontend Setup
```bash
cd frontend
npm install  # If not already done
npm start    # Runs on http://localhost:4200
```

### 3. Create Test Users
You'll need users with different roles to test the approval workflow:
- **Admin** - System administrator
- **Staff** - Regular employee (creates requests)
- **Line Manager** - First level approver
- **HOD** - Department head approver
- **Travel Desk** - Travel coordinator
- **Finance** - Financial approver

---

## Testing Checklist

### ✅ **Step 1: System Setup (Pre-Testing)**

#### 1.1 Create Roles and Users
- [ ] Login to Django admin: http://localhost:8000/admin
- [ ] Create roles in Accounts → Roles:
  - Line Manager
  - HOD (Head of Department)
  - Travel Desk
  - Finance Officer
- [ ] Create test users with different roles:
  - test-staff@example.com (Staff role)
  - test-manager@example.com (Line Manager role)
  - test-hod@example.com (HOD role)
  - test-travel@example.com (Travel Desk role)
  - test-finance@example.com (Finance Officer role)

#### 1.2 Configure Workflows
- [ ] Login to Angular frontend as Admin
- [ ] Navigate to System Settings → Enhanced Workflow Configuration
- [ ] Configure workflow for **Transport Requests**:
  - Step 1: Line Manager (approver role)
  - Step 2: HOD (approver role)
  - Optional Step 3: Admin (if needed)
- [ ] Configure workflow for **Travel Requests (TRF)**:
  - Step 1: Department Focal
  - Step 2: HOD
  - Step 3: Travel Desk
  - Step 4: Finance
- [ ] Configure workflow for **Visa Applications**:
  - Step 1: Department Focal
  - Step 2: HR Admin
- [ ] Configure workflow for **Accommodation Requests**:
  - Step 1: Line Manager
  - Step 2: Accommodation Admin
- [ ] Configure workflow for **Expense Claims**:
  - Step 1: Line Manager
  - Step 2: Finance Officer

---

### 🔄 **Step 2: TRF (Travel Request Form) Workflow Testing**

#### 2.1 Create Domestic Travel Request
- [ ] Login as Staff user
- [ ] Navigate to Travel Requests → New Request
- [ ] Select "Domestic Travel"
- [ ] Fill in Requestor Information:
  - Full name
  - Staff ID
  - Department
  - Contact number
- [ ] Fill in Domestic Travel Details:
  - Travel dates
  - Destinations
  - Purpose of travel
  - Itinerary segments
  - Accommodation needs
  - Meal provisions
- [ ] Click "Next: Approval & Submission"
- [ ] Review travel summary
- [ ] Check confirmation checkboxes
- [ ] Click "Submit Request"
- [ ] **Expected:** Request status = "Pending Department Focal"

#### 2.2 Approve at Department Focal Level
- [ ] Logout and login as Department Focal user
- [ ] Navigate to Travel Requests
- [ ] Click on pending request
- [ ] Verify workflow timeline shows current step
- [ ] Click "Approve" button
- [ ] Enter approval comments
- [ ] Submit approval
- [ ] **Expected:** Request status = "Pending HOD"

#### 2.3 Approve at HOD Level
- [ ] Logout and login as HOD user
- [ ] Navigate to Travel Requests
- [ ] Click on pending request
- [ ] Verify workflow timeline shows current step (HOD)
- [ ] Click "Approve" button
- [ ] Enter approval comments
- [ ] Submit approval
- [ ] **Expected:** Request status = "Pending Travel Desk"

#### 2.4 Approve at Travel Desk Level
- [ ] Logout and login as Travel Desk user
- [ ] Navigate to Travel Requests
- [ ] Click on pending request
- [ ] Verify workflow timeline shows current step
- [ ] Click "Approve" button
- [ ] Enter approval comments
- [ ] Submit approval
- [ ] **Expected:** Request status = "Pending Finance"

#### 2.5 Final Approval at Finance Level
- [ ] Logout and login as Finance user
- [ ] Navigate to Travel Requests
- [ ] Click on pending request
- [ ] Verify workflow timeline shows all previous approvals
- [ ] Click "Approve" button
- [ ] Enter final approval comments
- [ ] Submit approval
- [ ] **Expected:** Request status = "Approved" or "Completed"

#### 2.6 Test Rejection Flow
- [ ] Create another TRF as Staff user
- [ ] Login as Department Focal
- [ ] Click "Reject" button
- [ ] Enter rejection reason (required)
- [ ] Submit rejection
- [ ] **Expected:** Request status = "Rejected"
- [ ] Verify original requestor can see rejection reason

#### 2.7 Test Edit Draft
- [ ] Login as Staff user
- [ ] Create TRF but Save as Draft (don't submit)
- [ ] Navigate back to Travel Requests list
- [ ] Click "Edit" button on draft request
- [ ] Verify all form fields are pre-populated
- [ ] Make changes
- [ ] Submit request
- [ ] **Expected:** Request moves to workflow

---

### 🚗 **Step 3: Transport Request Workflow Testing**

#### 3.1 Create Multi-Segment Transport Request
- [ ] Login as Staff user
- [ ] Navigate to Transport → New Request
- [ ] Fill in basic information:
  - Title/purpose
  - Number of passengers
  - Passenger names
- [ ] Add transport segment #1:
  - From location
  - To location
  - Departure date and time
  - Arrival date and time
  - Vehicle type (Company Vehicle)
  - Estimated cost
- [ ] Click "Add Segment"
- [ ] Add transport segment #2 (return journey)
- [ ] Submit request
- [ ] **Expected:** Request status = "Pending Line Manager"

#### 3.2 Approve Transport Request
- [ ] Login as Line Manager
- [ ] Navigate to Transport Requests
- [ ] Click on pending request
- [ ] Verify multi-segment details displayed correctly
- [ ] Approve request
- [ ] **Expected:** Request status = "Pending HOD"
- [ ] Login as HOD
- [ ] Approve request
- [ ] **Expected:** Request status = "Approved"

#### 3.3 Admin Assigns Vehicle
- [ ] Login as Admin
- [ ] Navigate to Admin → Transport Admin
- [ ] Find approved request
- [ ] Click "Assign Vehicle"
- [ ] Fill in vehicle assignment form:
  - Vehicle number
  - Vehicle type
  - Driver name
  - Driver contact
  - Driver license number
  - Assignment date
  - Odometer start reading
- [ ] Submit assignment
- [ ] **Expected:** Assignment saved, status updated

#### 3.4 Test Edit Mode
- [ ] Login as Staff user
- [ ] Create transport request as Draft
- [ ] Click "Edit" on draft
- [ ] Verify segments are pre-populated
- [ ] Add/remove segments
- [ ] Submit
- [ ] **Expected:** Request enters workflow

---

### 🏨 **Step 4: Accommodation Request Workflow Testing**

#### 4.1 Create Accommodation Request
- [ ] Login as Staff user
- [ ] Navigate to Accommodation → New Request
- [ ] Fill in request details:
  - Purpose
  - Check-in date
  - Check-out date
  - Number of guests
  - Room type preference
  - Special requirements
  - Estimated cost
- [ ] Submit request
- [ ] **Expected:** Request status = "Pending Line Manager"

#### 4.2 Approve Accommodation Request
- [ ] Login as Line Manager
- [ ] Navigate to Accommodation Requests
- [ ] Approve pending request
- [ ] **Expected:** Request status = "Pending Accommodation Admin"
- [ ] Login as Accommodation Admin
- [ ] Navigate to Admin → Accommodation Admin
- [ ] Click "Assign Room"
- [ ] Select staff house
- [ ] Select available room
- [ ] Confirm dates
- [ ] Submit assignment
- [ ] **Expected:** Request status = "Confirmed"

#### 4.3 Test Accommodation Management
- [ ] Verify room assignment shows in request detail
- [ ] Check room availability updates
- [ ] Test check-in functionality (if implemented)
- [ ] Test check-out functionality (if implemented)

---

### 🛂 **Step 5: Visa Application Workflow Testing**

#### 5.1 Create Visa Application (6-Step Wizard)
- [ ] Login as Staff user
- [ ] Navigate to Visa Applications → New Application
- [ ] **Step 1: Personal Information**
  - Full name
  - Date of birth
  - Nationality
  - Contact details
- [ ] **Step 2: Travel Details**
  - Destination country
  - Travel purpose
  - Travel dates
  - Intended length of stay
- [ ] **Step 3: Visa Information**
  - Visa type (Business/Tourist/Work/Student)
  - Visa category
  - Entry type (Single/Multiple)
- [ ] **Step 4: Passport & Personal Details**
  - Passport number
  - Issue date and expiry date
  - Place of issue
  - Marital status
  - Occupation
- [ ] **Step 5: Approval Information**
  - Approver details
  - Estimated cost
  - Payment method
- [ ] **Step 6: Additional Information**
  - Special requests
  - Attachments
- [ ] Click "Submit Application"
- [ ] **Expected:** Application status = "Pending Department Focal"

#### 5.2 Approve Visa Application
- [ ] Login as Department Focal
- [ ] Approve application
- [ ] **Expected:** Status = "Pending HR Admin"
- [ ] Login as HR Admin
- [ ] Navigate to Admin → Visa Admin
- [ ] Click "Start Processing"
- [ ] Approve application
- [ ] **Expected:** Status = "Approved"

#### 5.3 Process Visa Application
- [ ] As Visa Admin, click "Start Processing"
- [ ] **Expected:** Status = "Processing"
- [ ] Upload visa documents (if implemented)
- [ ] Click "Complete"
- [ ] **Expected:** Status = "Completed"

---

### 💰 **Step 6: Expense Claims Workflow Testing**

#### 6.1 Create Expense Claim (7 Sections)
- [ ] Login as Staff user
- [ ] Navigate to Expense Claims → New Claim
- [ ] **Section 1: Header Details**
  - Document type
  - Staff information
  - Department
  - Time period
- [ ] **Section 2: Bank Details**
  - Bank name
  - Account number
  - Payment purpose
- [ ] **Section 3: Medical Claim** (if applicable)
  - Select medical claim type
  - Add family member details
- [ ] **Section 4: Expense Items**
  - Add expense item row #1
  - Fill in: Date, Description, Mileage, Transport, Hotel, Outstation, Misc, Other
  - Add more rows as needed
  - Verify totals auto-calculate
- [ ] **Section 5: Foreign Exchange Rates** (if applicable)
  - Add FX rate row
  - Currency type
  - Selling rate
- [ ] **Section 6: Financial Summary**
  - Total expenses (auto-calculated)
  - Less advance received
  - Less credit card charges
  - Balance due (auto-calculated)
- [ ] **Section 7: Declaration**
  - Check declaration checkbox
  - Enter date
- [ ] Submit claim
- [ ] **Expected:** Claim status = "Pending Line Manager"

#### 6.2 Approve Expense Claim
- [ ] Login as Line Manager
- [ ] Navigate to Expense Claims
- [ ] Click on pending claim
- [ ] Verify all sections displayed correctly
- [ ] Verify calculations are correct
- [ ] Approve claim
- [ ] **Expected:** Status = "Pending Finance Officer"
- [ ] Login as Finance Officer
- [ ] Navigate to Admin → Claims Admin
- [ ] Approve claim
- [ ] **Expected:** Status = "Approved"

#### 6.3 Mark Claim as Paid
- [ ] As Finance Officer, click "Mark as Paid"
- [ ] Fill in payment details:
  - Payment method (Cheque/Bank Transfer/Cash)
  - Payment reference or cheque number
  - Payment date
- [ ] Submit payment
- [ ] **Expected:** Status = "Paid"

---

## 🎯 **Step 7: Cross-Cutting Features Testing**

### 7.1 Notifications System
- [ ] Create any request as Staff user
- [ ] Check notification bell icon (top right)
- [ ] Verify unread count badge shows
- [ ] Click bell to open dropdown
- [ ] Verify 5 recent notifications displayed
- [ ] Click "View All"
- [ ] Navigate to Notifications page
- [ ] Test filters: All/Unread/Read
- [ ] Test priority filters: Urgent/High/Normal/Low
- [ ] Mark notification as read
- [ ] Delete notification

### 7.2 Approvals Dashboard
- [ ] Login as any approver user
- [ ] Navigate to Approvals (from sidebar)
- [ ] Verify unified approval queue shows all pending requests
- [ ] Test tab navigation:
  - All
  - Travel (TRF)
  - Accommodation
  - Transport
  - Visa
  - Expenses
- [ ] Click on a request
- [ ] Verify detail panel shows type-specific information
- [ ] Click "View Full Details" button
- [ ] **Expected:** Navigates to request detail page

### 7.3 User Profile
- [ ] Navigate to user profile (click avatar/name)
- [ ] Verify profile information displayed
- [ ] Edit profile:
  - Update phone number
  - Update gender
- [ ] Save changes
- [ ] Change password:
  - Enter current password
  - Enter new password
  - Confirm new password
- [ ] Submit password change
- [ ] Logout and login with new password

### 7.4 System Settings (Admin Only)
- [ ] Login as Admin
- [ ] Navigate to System Settings
- [ ] **General Settings Tab:**
  - Update app name
  - Update support email
  - Change currency
  - Change timezone
- [ ] **Email Settings Tab:**
  - Configure SMTP settings
  - Test email notifications (if configured)
- [ ] **Notifications Tab:**
  - Enable/disable email notifications
- [ ] **Approvals Tab:**
  - Set auto-approval threshold
  - Enable manager approval requirement
  - Enable finance approval requirement
- [ ] **Maintenance Tab:**
  - Enable maintenance mode (WARNING: blocks users)
  - Add maintenance message
- [ ] Save all settings
- [ ] Verify settings persist after page reload

### 7.5 Role Management
- [ ] Navigate to System Settings → Role Management
- [ ] Create new role:
  - Role name
  - Description
- [ ] Assign permissions to role
- [ ] Edit existing role
- [ ] Delete role (if no users assigned)

---

## 🐛 **Step 8: Bug Tracking**

### Known Issues (Already Fixed)
- ✅ External parties details component TypeScript errors - FIXED
- ✅ TRF edit mode not pre-populating data - FIXED
- ✅ Authentication errors in detail components - FIXED

### Issues to Watch For
- [ ] Workflow status not updating correctly
- [ ] Approval actions not triggering status change
- [ ] Form validation errors
- [ ] Data not persisting after page reload
- [ ] Notification count not updating
- [ ] File upload issues (if implemented)
- [ ] Date/time picker issues
- [ ] Mobile responsiveness issues

---

## 📊 **Step 9: Performance Testing**

### 9.1 Load Testing
- [ ] Create 10+ requests of each type
- [ ] Verify list pages load within 2 seconds
- [ ] Test pagination performance
- [ ] Test search functionality with large dataset
- [ ] Test filter performance

### 9.2 API Response Times
- [ ] Monitor Django console for slow queries
- [ ] Check browser Network tab for slow API calls
- [ ] Optimize queries if needed

---

## 📝 **Step 10: Documentation**

### 10.1 User Guide
- [ ] Create user guide for staff (how to create requests)
- [ ] Create approver guide (how to approve requests)
- [ ] Create admin guide (system configuration)

### 10.2 API Documentation
- [ ] Document all API endpoints
- [ ] Include request/response examples
- [ ] Document authentication requirements

---

## ✅ **Testing Completion Checklist**

### Core Functionality
- [ ] All 5 module workflows tested (TRF, Transport, Accommodation, Visa, Expense Claims)
- [ ] Create, Edit, View, Delete operations work
- [ ] Approval workflow progresses correctly
- [ ] Status updates reflect workflow state
- [ ] Notifications trigger correctly

### UI/UX
- [ ] All buttons have consistent styling
- [ ] Badges show correct colors
- [ ] Loading states display properly
- [ ] Error messages are user-friendly
- [ ] Empty states show helpful messages
- [ ] Forms validate correctly
- [ ] Responsive design works on mobile

### Security
- [ ] Users can only see their own requests (unless approver/admin)
- [ ] Role-based access control works
- [ ] Authentication required for all protected routes
- [ ] API endpoints respect permissions

### Integration
- [ ] Backend and frontend communicate correctly
- [ ] Database migrations applied successfully
- [ ] Workflow engine integrates with all modules
- [ ] Notification system integrates with workflow events

---

## 🎉 **Expected Results**

By the end of testing, you should have:

1. ✅ **5 complete request workflows** (TRF, Transport, Accommodation, Visa, Expense Claims)
2. ✅ **Dynamic status updates** based on workflow progression
3. ✅ **Role-based approvals** working correctly
4. ✅ **Notifications** triggering on workflow events
5. ✅ **Admin panels** functioning for all modules
6. ✅ **System settings** persisting correctly
7. ✅ **User profile** management working
8. ✅ **Consistent UI/UX** across all modules

---

## 🚀 **Next Steps After Testing**

1. **Document bugs** found during testing
2. **Prioritize bug fixes** (critical → high → medium → low)
3. **Plan next features** (Hotel Bookings, Document Upload, etc.)
4. **Prepare for production deployment**
5. **Create user training materials**
6. **Set up production database**
7. **Configure production email server**
8. **Set up monitoring and logging**

---

## 📞 **Support**

If you encounter issues during testing:
1. Check browser console for errors
2. Check Django console for backend errors
3. Verify database migrations are applied
4. Verify workflow configuration is correct
5. Document the issue with screenshots and steps to reproduce

---

**End of Testing Guide**
