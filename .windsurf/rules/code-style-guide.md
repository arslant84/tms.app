---
trigger: manual
---

Accommodation Module Requirements
#accommodation_module
#requirements
#trf_integration
#staff_houses
#camps
Edit
The TMS application needs an Accommodation Request Module that allows staff to book staff houses/camps, tracks room availability, and integrates with the broader travel requisition workflow.

Key requirements include:
1. Staff View:
   - Selection between Staff House (Ashgabat) and Camp (Kiyanly)
   - Date picker for check-in/check-out (nights-only booking)
   - Gender selection for gender-segregated rooms
   - Room availability calendar (color-coded)
   - Display of max capacity per apartment

2. Admin Focal View:
   - Room management (add/remove staff houses or camps)
   - Block rooms for VIPs/maintenance
   - Calendar view with color-coding
   - Approval workflow
   - Business rules for room assignment

3. Security & Compliance:
   - Role-based access
   - Audit logs for booking changes

The module should integrate with the existing TRF workflow and provide real-time validation to prevent invalid bookings.

Travel Request Form Component Structure
#trf
#component_structure
#angular_conversion

Edit
The user has React travel components in C:\Users\Arslan\Desktop\syntra\src\components\trf that need to be converted to Angular.

Key components include:
1. TrfStepper - A stepper component for navigating through the form
2. RequestorInformationForm - For capturing requestor details
3. DomesticTravelDetailsForm - For domestic travel specifics
4. OverseasTravelDetailsForm - For overseas travel specifics
5. ExternalTravelDetailsForm - For external travel specifics
6. ApprovalWorkflow - For handling the approval process
7. TrfView - For viewing travel request details

The components use form validation, dynamic form arrays, and conditional rendering based on travel type.


