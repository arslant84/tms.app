/**
 * Combined Request Wizard Component
 *
 * Multi-step wizard for creating combined requests that can include
 * TSR, Transport, Accommodation, and Visa in a single submission.
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { FormUtilsService } from '../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../core/utils/date-utils.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ApproverSelectionComponent, SkippedStepsSelection } from '../../../shared/components/approver-selection/approver-selection.component';
import { CombinedRequestService } from './services/combined-request.service';
import type { CombinedRequest, CombinedRequestDocument } from './models/combined-request.model';
import { UserFormHelperService } from '../../../core/utils/user-form-helper.service';
import { ToastService } from '../../../core/services/toast.service';
import { ApproverSelection } from '../../../core/services/workflow.service';

interface ItinerarySegmentValue {
  segmentDate: string;
  fromLocation: string;
  toLocation: string;
  departureTime: string;
  arrivalTime: string;
  modeOfTravel: string;
  flightNumber: string;
}

interface DailyMealRow {
  date: string | null;
  breakfast: boolean;
  lunch: boolean;
  dinner: boolean;
  supper: boolean;
  refreshment: boolean;
}

interface WizardStep {
  id: string;
  title: string;
  description: string;
  icon: string;
  isConditional: boolean;
  condition?: () => boolean;
}

@Component({
  selector: 'app-combined-request-wizard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent, ApproverSelectionComponent],
  templateUrl: './combined-request-wizard.component.html',
  styleUrl: './combined-request-wizard.component.scss'
})
export class CombinedRequestWizardComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Form state
  combinedRequestForm: FormGroup = new FormGroup({});
  isSubmitting = false;
  isLoading = false;
  editMode = false;
  requestId: number | null = null;

  // Visa document upload state
  visaDocumentQueue: { file: File; documentType: string }[] = [];
  uploadedDocuments: CombinedRequestDocument[] = [];
  newDocumentType = 'passport';

  // Approver selection state
  selectedApprovers: ApproverSelection = {};
  skippedSteps: SkippedStepsSelection = {};
  approverSelectionValid = true;

  // Step management
  currentStepIndex = 0;
  allSteps: WizardStep[] = [
    {
      id: 'modules',
      title: 'Select Modules',
      description: 'Choose which services you need',
      icon: 'bi-grid-3x3-gap',
      isConditional: false
    },
    {
      id: 'basic',
      title: 'Basic Information',
      description: 'Your personal and department details',
      icon: 'bi-person',
      isConditional: false
    },
    {
      id: 'travel',
      title: 'Travel Details',
      description: 'Trip itinerary and flight information',
      icon: 'bi-airplane',
      isConditional: true,
      condition: () => this.combinedRequestForm.get('includeTravel')?.value
    },
    {
      id: 'transport',
      title: 'Transport Details',
      description: 'Local transportation requirements',
      icon: 'bi-car-front',
      isConditional: true,
      condition: () => this.combinedRequestForm.get('includeTransport')?.value
    },
    {
      id: 'accommodation',
      title: 'Accommodation',
      description: 'Hotel and lodging preferences',
      icon: 'bi-building',
      isConditional: true,
      condition: () => this.combinedRequestForm.get('includeAccommodation')?.value
    },
    {
      id: 'visa',
      title: 'Visa Details',
      description: 'Passport and visa information',
      icon: 'bi-passport',
      isConditional: true,
      condition: () => this.combinedRequestForm.get('includeVisa')?.value
    },
    {
      id: 'review',
      title: 'Review & Submit',
      description: 'Review your request before submission',
      icon: 'bi-check-circle',
      isConditional: false
    }
  ];

  // Travel type options
  travelTypes = [
    { value: 'domestic', label: 'Domestic Business Trip' },
    { value: 'international', label: 'International Business Trip' },
    { value: 'home_leave', label: 'Home Leave Passage' },
    { value: 'external', label: 'External Parties Travel' }
  ];

  // Visa type options
  visaTypes = [
    { value: 'Tourist', label: 'Tourist' },
    { value: 'Business', label: 'Business' },
    { value: 'Work', label: 'Work' },
    { value: 'Student', label: 'Student' },
    { value: 'Transit', label: 'Transit' },
    { value: 'Diplomatic', label: 'Diplomatic' },
    { value: 'Official', label: 'Official' },
    { value: 'Other', label: 'Other' }
  ];

  entryTypes = ['Single Entry', 'Multiple Entry', 'Transit'];
  maritalStatuses = ['Single', 'Married', 'Divorced', 'Widowed'];

  // Transport type options (matches standalone transport form)
  transportTypes = ['Local', 'Intercity', 'Airport Transfer', 'Charter', 'Other'];

  // Meal provision (domestic only)
  dailyMealDates: Date[] = [];
  mealSummary = { breakfast: 0, lunch: 0, dinner: 0, supper: 0, refreshment: 0 };

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private formUtils: FormUtilsService,
    private combinedRequestService: CombinedRequestService,
    private userFormHelper: UserFormHelperService,
    public dateUtils: DateUtilsService,
    private toastService: ToastService
  ) {
    this.initForm();
  }

  ngOnInit(): void {
    // Check for edit mode
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe(params => {
      if (params['id']) {
        this.editMode = true;
        this.requestId = +params['id'];
        this.loadRequest(this.requestId);
      } else {
        this.loadDraft();
        this.prefillUserInfo(); // Always apply after draft so user fields are current
      }
    });

    // Watch itinerary changes to auto-update meal dates (domestic only)
    this.itinerarySegments.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.updateMealDatesFromItinerary();
    });

    // When travel type changes away from domestic, clear meal selections
    this.combinedRequestForm.get('travelType')?.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(type => {
      if (type !== 'domestic') {
        this.mealDailySelections.clear();
        this.dailyMealDates = [];
        this.updateMealSummary();
      } else {
        this.updateMealDatesFromItinerary();
      }
    });

    // Update required validators when module selection changes
    this.combinedRequestForm.get('includeTransport')?.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.updateConditionalValidators());

    this.combinedRequestForm.get('includeAccommodation')?.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.updateConditionalValidators());

    // Apply initial state (transport off, accommodation off by default)
    this.updateConditionalValidators();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Set or clear required validators on module-specific fields
   * based on which modules are currently selected.
   */
  private updateConditionalValidators(): void {
    const includeTransport = !!this.combinedRequestForm.get('includeTransport')?.value;
    const includeAccommodation = !!this.combinedRequestForm.get('includeAccommodation')?.value;

    // Transport: transportPurpose required only when transport module is on
    const transportPurpose = this.combinedRequestForm.get('transportPurpose');
    if (includeTransport) {
      transportPurpose?.setValidators([Validators.required]);
    } else {
      transportPurpose?.clearValidators();
    }
    transportPurpose?.updateValueAndValidity({ emitEvent: false });

    // Accommodation: four fields required only when accommodation module is on
    const accommodationFields = [
      'accommodationGender',
      'accommodationCheckin',
      'accommodationCheckout',
      'accommodationLocation'
    ];
    accommodationFields.forEach(field => {
      const control = this.combinedRequestForm.get(field);
      if (includeAccommodation) {
        control?.setValidators([Validators.required]);
      } else {
        control?.clearValidators();
      }
      control?.updateValueAndValidity({ emitEvent: false });
    });
  }

  /**
   * Initialize the form with all fields
   */
  private initForm(): void {
    this.combinedRequestForm = this.fb.group({
      // Step 1: Module Selection
      includeTravel: [true],
      includeTransport: [false],
      includeAccommodation: [false],
      includeVisa: [false],

      // Step 2: Basic Information
      requestorName: ['', Validators.required],
      staffId: [''],
      department: ['', Validators.required],
      position: [''],
      email: ['', [Validators.required, Validators.email]],
      phone: [''],
      costCenter: [''],

      // Step 3: Travel Details
      travelType: ['domestic'],
      tripType: ['Round Trip'],
      travelPurpose: [''],
      departureDate: [''],
      returnDate: [''],
      destinationCountry: [''],
      destinationCity: [''],
      mealDailySelections: this.fb.array([]),
      itinerarySegments: this.fb.array([]),

      // Step 4: Transport Details
      transportPurpose: [''],
      transportTsrReference: [''],
      transportSegments: this.fb.array([]),

      // Step 5: Accommodation Details
      accommodationGender: [''],
      accommodationCheckin: [''],
      accommodationCheckout: [''],
      accommodationLocation: [''],
      accommodationRoomType: [''],
      accommodationFlightArrivalTime: [''],
      accommodationFlightDepartureTime: [''],
      accommodationSpecialRequests: [''],

      // Step 6: Visa Details — Section A: Particulars of Applicant
      // Personal Information
      visa_date_of_birth: [''],
      visa_place_of_birth: [''],
      visa_citizenship: [''],
      visa_contact_telephone: [''],
      visa_marital_status: [''],
      visa_home_address: [''],
      visa_family_information: [''],
      visa_education_details: [''],
      // Passport Details
      visa_passport_number: [''],
      visa_passport_expiry_date: [''],
      visa_passport_place_of_issuance: [''],
      visa_passport_date_of_issuance: [''],
      // Employment
      visa_current_employer_name: [''],
      visa_current_employer_address: [''],

      // Section B: Type of Request
      visa_request_type: ['VISA'],
      visa_approximately_arrival_date: [''],
      visa_duration_of_stay: [''],
      visa_entry_type: [''],
      visa_work_visit_category: [''],
      visa_application_fees_borne_by: [''],
      visa_cost_centre_number: [''],

      // Section C: Travel Details
      visaDestinationCountry: [''],
      visaType: [''],
      visa_trf_reference_number: [''],
      visa_trip_start_date: [''],
      visa_trip_end_date: [''],
      visa_travel_purpose: [''],
      visa_itinerary_details: [''],

      // Additional Information
      visa_additional_comments: [''],
      visa_supporting_documents_notes: [''],

      passports: this.fb.array([]),

      // Travel type-specific — Bank Details (international & home_leave)
      advanceBankAccountName: [''],
      advanceBankName: [''],
      advanceBankAccountNumber: [''],
      advanceBankCurrency: ['TMT'],
      advanceBankBranchRemarks: [''],

      // Travel type-specific — Advance Amount Items (international only)
      advanceAmountItems: this.fb.array([]),

      // Travel type-specific — External Party Info
      externalFullName: [''],
      externalOrganization: [''],
      externalRefToAuthorityLetter: [''],
      externalCostCenter: [''],

      // Step 7: Review
      additionalComments: ['']
    });
  }

  /**
   * Prefill user information from auth service
   */
  private prefillUserInfo(): void {
    const defaults = this.userFormHelper.getUserFormDefaults();
    this.combinedRequestForm.patchValue({
      requestorName: defaults.fullName,
      email: defaults.email,
      phone: defaults.phone,
      department: defaults.department,
      position: defaults.position,
      staffId: defaults.staffId
    });
  }

  /**
   * Load existing request for editing
   */
  private loadRequest(id: number): void {
    this.isLoading = true;
    this.combinedRequestService.getById(id).pipe(takeUntil(this.destroy$)).subscribe({
      next: (request) => {
        const s = request.status || '';
        const canEdit = s === 'Draft' || s === 'Rejected' || s.startsWith('Pending');

        if (s && !canEdit) {
          this.isLoading = false;
          this.toastService.error(
            `This request cannot be edited because its status is "${s}". Only Draft, Rejected, or Pending requests can be edited.`
          );
          setTimeout(() => this.router.navigate(['/combined']), 3000);
          return;
        }

        this.patchFormFromRequest(request);
        this.updateConditionalValidators();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading request:', error);
        this.isLoading = false;
        this.router.navigate(['/combined']);
      }
    });
  }

  /**
   * Patch form values from loaded request
   */
  private patchFormFromRequest(request: CombinedRequest): void {
    this.combinedRequestForm.patchValue({
      includeTravel: request.includeTravel,
      includeTransport: request.includeTransport,
      includeAccommodation: request.includeAccommodation,
      includeVisa: request.includeVisa,
      requestorName: request.requestorName,
      staffId: request.staffId,
      department: request.department,
      position: request.position,
      email: request.email,
      phone: request.phone,
      costCenter: request.costCenter,
      transportPurpose: request.transportPurpose,
      transportTsrReference: request.transportTsrReference,
      travelType: request.travelType,
      tripType: request.tripType || 'Round Trip',
      travelPurpose: request.travelPurpose,
      departureDate: request.departureDate,
      returnDate: request.returnDate,
      destinationCountry: request.destinationCountry,
      destinationCity: request.destinationCity,
      accommodationGender: request.accommodationGender,
      accommodationCheckin: request.accommodationCheckin,
      accommodationCheckout: request.accommodationCheckout,
      accommodationLocation: request.accommodationLocation,
      accommodationRoomType: request.accommodationRoomType,
      accommodationFlightArrivalTime: request.accommodationFlightArrivalTime,
      accommodationFlightDepartureTime: request.accommodationFlightDepartureTime,
      accommodationSpecialRequests: request.accommodationSpecialRequests,
      visaDestinationCountry: request.visaDestinationCountry,
      visaType: request.visaType,
      visa_date_of_birth: request.visa_date_of_birth,
      visa_place_of_birth: request.visa_place_of_birth,
      visa_citizenship: request.visa_citizenship,
      visa_contact_telephone: request.visa_contact_telephone,
      visa_marital_status: request.visa_marital_status,
      visa_home_address: request.visa_home_address,
      visa_family_information: request.visa_family_information,
      visa_education_details: request.visa_education_details,
      visa_passport_number: request.visa_passport_number,
      visa_passport_expiry_date: request.visa_passport_expiry_date,
      visa_passport_place_of_issuance: request.visa_passport_place_of_issuance,
      visa_passport_date_of_issuance: request.visa_passport_date_of_issuance,
      visa_current_employer_name: request.visa_current_employer_name,
      visa_current_employer_address: request.visa_current_employer_address,
      visa_request_type: request.visa_request_type || 'VISA',
      visa_approximately_arrival_date: request.visa_approximately_arrival_date,
      visa_duration_of_stay: request.visa_duration_of_stay,
      visa_entry_type: request.visa_entry_type,
      visa_work_visit_category: request.visa_work_visit_category,
      visa_application_fees_borne_by: request.visa_application_fees_borne_by,
      visa_cost_centre_number: request.visa_cost_centre_number,
      visa_trf_reference_number: request.visa_trf_reference_number,
      visa_trip_start_date: request.visa_trip_start_date,
      visa_trip_end_date: request.visa_trip_end_date,
      visa_travel_purpose: request.visa_travel_purpose,
      visa_itinerary_details: request.visa_itinerary_details,
      visa_additional_comments: request.visa_additional_comments,
      visa_supporting_documents_notes: request.visa_supporting_documents_notes,
      advanceBankAccountName: request.advanceBankAccountName,
      advanceBankName: request.advanceBankName,
      advanceBankAccountNumber: request.advanceBankAccountNumber,
      advanceBankCurrency: request.advanceBankCurrency || 'TMT',
      advanceBankBranchRemarks: request.advanceBankBranchRemarks,
      externalFullName: request.externalFullName,
      externalOrganization: request.externalOrganization,
      externalRefToAuthorityLetter: request.externalRefToAuthorityLetter,
      externalCostCenter: request.externalCostCenter,
      additionalComments: request.additionalComments
    });

    // Load advance amount items
    if (request.advanceAmountItems?.length) {
      request.advanceAmountItems.forEach(item => this.addAdvanceAmountItem(item));
    }

    // Load itinerary segments
    if (request.itinerarySegments?.length) {
      request.itinerarySegments.forEach(segment => this.addItinerarySegment(segment));
    }

    // Restore meal selections (loaded from travel_data.meal_selections via toFrontendFormat)
    if (request.mealDailySelections?.length) {
      this.mealDailySelections.clear();
      request.mealDailySelections.forEach(row => {
        this.mealDailySelections.push(this.createDailyMealSelection({
          date: row.date,
          breakfast: row.breakfast,
          lunch: row.lunch,
          dinner: row.dinner,
          supper: row.supper,
          refreshment: row.refreshment
        }));
      });
      this.dailyMealDates = request.mealDailySelections
        .filter(r => r.date)
        .map(r => new Date(r.date as string));
      this.updateMealSummary();
    }

    // Load transport segments
    if (request.transportSegments?.length) {
      request.transportSegments.forEach(segment => this.addTransportSegment(segment));
    }

    // Load passports
    if (request.passports?.length) {
      request.passports.forEach(passport => this.addPassport(passport));
    }

    // Load existing visa documents
    if (request.documents?.length) {
      this.uploadedDocuments = request.documents.filter(d => d.module === 'visa');
    }
  }

  // ===== STEP NAVIGATION =====

  get activeSteps(): WizardStep[] {
    return this.allSteps.filter(step =>
      !step.isConditional || (step.condition && step.condition())
    );
  }

  get currentStep(): WizardStep {
    return this.activeSteps[this.currentStepIndex];
  }

  get totalSteps(): number {
    return this.activeSteps.length;
  }

  get progressPercentage(): number {
    return ((this.currentStepIndex + 1) / this.totalSteps) * 100;
  }

  get isFirstStep(): boolean {
    return this.currentStepIndex === 0;
  }

  get isLastStep(): boolean {
    return this.currentStepIndex === this.totalSteps - 1;
  }

  nextStep(): void {
    if (this.isCurrentStepValid() && !this.isLastStep) {
      this.currentStepIndex++;
      this.autosaveDraft();
      window.scrollTo(0, 0);
    }
  }

  previousStep(): void {
    if (!this.isFirstStep) {
      this.currentStepIndex--;
      window.scrollTo(0, 0);
    }
  }

  goToStep(index: number): void {
    if (index >= 0 && index < this.totalSteps) {
      // Only allow going to previous steps or current step
      if (index <= this.currentStepIndex) {
        this.currentStepIndex = index;
        window.scrollTo(0, 0);
      }
    }
  }

  // ===== VALIDATION =====

  isCurrentStepValid(): boolean {
    const stepId = this.currentStep?.id;
    const fieldsToValidate = this.getFieldsForStep(stepId);

    return fieldsToValidate.every(field => {
      const control = this.combinedRequestForm.get(field);
      return control ? control.valid : true;
    });
  }

  private getFieldsForStep(stepId: string): string[] {
    switch (stepId) {
      case 'modules':
        return []; // At least one module should be selected (custom validation)
      case 'basic':
        return ['requestorName', 'department', 'email'];
      case 'travel':
        return this.combinedRequestForm.get('includeTravel')?.value
          ? ['travelPurpose', 'departureDate', 'returnDate', 'destinationCity']
          : [];
      case 'transport':
        return []; // Transport segments validated in array
      case 'accommodation':
        return this.combinedRequestForm.get('includeAccommodation')?.value
          ? ['accommodationGender', 'accommodationCheckin', 'accommodationCheckout', 'accommodationLocation']
          : [];
      case 'visa':
        return this.combinedRequestForm.get('includeVisa')?.value
          ? ['visaDestinationCountry', 'visaType']
          : [];
      case 'review':
        return [];
      default:
        return [];
    }
  }

  isAtLeastOneModuleSelected(): boolean {
    return (
      this.combinedRequestForm.get('includeTravel')?.value ||
      this.combinedRequestForm.get('includeTransport')?.value ||
      this.combinedRequestForm.get('includeAccommodation')?.value ||
      this.combinedRequestForm.get('includeVisa')?.value
    );
  }

  // ===== FORM ARRAYS =====

  get itinerarySegments(): FormArray {
    return this.combinedRequestForm.get('itinerarySegments') as FormArray;
  }

  get transportSegments(): FormArray {
    return this.combinedRequestForm.get('transportSegments') as FormArray;
  }

  get passports(): FormArray {
    return this.combinedRequestForm.get('passports') as FormArray;
  }

  addItinerarySegment(data?: any): void {
    const segment = this.fb.group({
      segmentOrder: [this.itinerarySegments.length + 1],
      segmentDate: [data?.segmentDate || ''],
      dayOfWeek: [data?.dayOfWeek || ''],
      fromLocation: [data?.fromLocation || '', Validators.required],
      toLocation: [data?.toLocation || '', Validators.required],
      departureTime: [data?.departureTime || ''],
      arrivalTime: [data?.arrivalTime || ''],
      modeOfTravel: [data?.modeOfTravel || 'flight'],
      flightNumber: [data?.flightNumber || ''],
      flightClass: [data?.flightClass || 'economy'],
      purpose: [data?.purpose || ''],
      remarks: [data?.remarks || '']
    });
    this.itinerarySegments.push(segment);
  }

  onItineraryDateChange(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.value) {
      const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      const day = new Date(input.value + 'T00:00:00').getDay();
      this.itinerarySegments.at(index).get('dayOfWeek')?.setValue(weekdays[day]);
    }
  }

  removeItinerarySegment(index: number): void {
    this.itinerarySegments.removeAt(index);
    // Reorder segment numbers
    this.itinerarySegments.controls.forEach((ctrl, i) => {
      ctrl.get('segmentOrder')?.setValue(i + 1);
    });
  }

  addTransportSegment(data?: any): void {
    const segment = this.fb.group({
      segmentOrder: [this.transportSegments.length + 1],
      pickupDate: [data?.pickupDate || '', Validators.required],
      dayOfWeek: [data?.dayOfWeek || ''],
      pickupLocation: [data?.pickupLocation || '', Validators.required],
      dropoffLocation: [data?.dropoffLocation || '', Validators.required],
      pickupTime: [data?.pickupTime || '', Validators.required],
      transportType: [data?.transportType || 'Local', Validators.required],
      passengers: [data?.passengers || 1, [Validators.required, Validators.min(1)]],
      vehicleTypePreference: [data?.vehicleTypePreference || ''],
      notes: [data?.notes || '']
    });
    this.transportSegments.push(segment);
  }

  onTransportDateChange(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.value) {
      const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      const day = new Date(input.value + 'T00:00:00').getDay();
      this.transportSegments.at(index).get('dayOfWeek')?.setValue(weekdays[day]);
    }
  }

  removeTransportSegment(index: number): void {
    this.transportSegments.removeAt(index);
    this.transportSegments.controls.forEach((ctrl, i) => {
      ctrl.get('segmentOrder')?.setValue(i + 1);
    });
  }

  addPassport(data?: any): void {
    const passport = this.fb.group({
      fullName: [data?.fullName || '', Validators.required],
      passportNumber: [data?.passportNumber || '', Validators.required],
      nationality: [data?.nationality || '', Validators.required],
      dateOfBirth: [data?.dateOfBirth || ''],
      placeOfBirth: [data?.placeOfBirth || ''],
      issueDate: [data?.issueDate || ''],
      expiryDate: [data?.expiryDate || '', Validators.required]
    });
    this.passports.push(passport);
  }

  removePassport(index: number): void {
    this.passports.removeAt(index);
  }

  // ===== ADVANCE AMOUNT ITEMS (international only) =====

  get advanceAmountItems(): FormArray {
    return this.combinedRequestForm.get('advanceAmountItems') as FormArray;
  }

  addAdvanceAmountItem(data?: any): void {
    const item = this.fb.group({
      dateFrom: [data?.dateFrom || '', Validators.required],
      dateTo: [data?.dateTo || '', Validators.required],
      lh: [data?.lh ?? 0],
      ma: [data?.ma ?? 0],
      oa: [data?.oa ?? 0],
      tr: [data?.tr ?? 0],
      oe: [data?.oe ?? 0],
      usd: [{ value: data?.usd ?? 0, disabled: true }],
      remarks: [data?.remarks || '']
    });
    this.advanceAmountItems.push(item);
  }

  removeAdvanceAmountItem(index: number): void {
    this.advanceAmountItems.removeAt(index);
  }

  // ===== MEAL PROVISION (domestic only) =====

  get mealDailySelections(): FormArray {
    return this.combinedRequestForm.get('mealDailySelections') as FormArray;
  }

  private createDailyMealSelection(data?: DailyMealRow): FormGroup {
    const group = this.fb.group({
      date: [data?.date ?? null],
      breakfast:   [data?.breakfast   ?? false],
      lunch:       [data?.lunch       ?? false],
      dinner:      [data?.dinner      ?? false],
      supper:      [data?.supper      ?? false],
      refreshment: [data?.refreshment ?? false]
    });
    group.valueChanges.subscribe(() => this.updateMealSummary());
    return group;
  }

  private updateMealDatesFromItinerary(): void {
    if (this.combinedRequestForm.get('travelType')?.value !== 'domestic') return;

    const segments = this.itinerarySegments.value as ItinerarySegmentValue[];
    const dates: Date[] = [];

    segments.forEach(seg => {
      if (seg.segmentDate) {
        const d = new Date(seg.segmentDate);
        if (!Number.isNaN(d.getTime())) dates.push(d);
      }
    });

    if (dates.length === 0) {
      this.mealDailySelections.clear();
      this.dailyMealDates = [];
      this.updateMealSummary();
      return;
    }

    dates.sort((a, b) => a.getTime() - b.getTime());
    const allDates: Date[] = [];
    for (let d = new Date(dates[0]); d <= dates[dates.length - 1]; d.setDate(d.getDate() + 1)) {
      allDates.push(new Date(d));
    }
    this.dailyMealDates = allDates;

    const existing = this.mealDailySelections.value as DailyMealRow[];
    this.mealDailySelections.clear();
    allDates.forEach(date => {
      const prev = existing.find(s => s.date != null && new Date(s.date).toDateString() === date.toDateString());
      this.mealDailySelections.push(this.createDailyMealSelection(
        prev ?? { date: date.toISOString(), breakfast: false, lunch: false, dinner: false, supper: false, refreshment: false }
      ));
    });

    this.updateMealSummary();
  }

  private updateMealSummary(): void {
    const sel = this.mealDailySelections.value as DailyMealRow[];
    this.mealSummary = {
      breakfast:   sel.filter(s => s.breakfast).length,
      lunch:       sel.filter(s => s.lunch).length,
      dinner:      sel.filter(s => s.dinner).length,
      supper:      sel.filter(s => s.supper).length,
      refreshment: sel.filter(s => s.refreshment).length
    };
  }

  selectAllMealType(meal: 'breakfast' | 'lunch' | 'dinner' | 'supper' | 'refreshment'): void {
    this.mealDailySelections.controls.forEach(c => c.patchValue({ [meal]: true }));
  }

  resetMealType(meal: 'breakfast' | 'lunch' | 'dinner' | 'supper' | 'refreshment'): void {
    this.mealDailySelections.controls.forEach(c => c.patchValue({ [meal]: false }));
  }

  // ===== DRAFT MANAGEMENT =====

  private autosaveDraft(): void {
    if (this.editMode) return; // Don't save draft in edit mode

    const draftData = {
      formData: this.combinedRequestForm.value,
      lastStepIndex: this.currentStepIndex,
      timestamp: new Date().toISOString()
    };
    localStorage.setItem('draft_combined_request', JSON.stringify(draftData));
  }

  private loadDraft(): void {
    const savedDraft = localStorage.getItem('draft_combined_request');
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        if (draftData.formData?.department && typeof draftData.formData.department !== 'string') {
          draftData.formData.department = this.normalizeDepartment(draftData.formData.department);
        }
        this.combinedRequestForm.patchValue(draftData.formData);

        // Restore form arrays
        if (draftData.formData.itinerarySegments?.length) {
          draftData.formData.itinerarySegments.forEach((s: any) => this.addItinerarySegment(s));
        }
        if (draftData.formData.transportSegments?.length) {
          draftData.formData.transportSegments.forEach((s: any) => this.addTransportSegment(s));
        }
        if (draftData.formData.passports?.length) {
          draftData.formData.passports.forEach((p: any) => this.addPassport(p));
        }
        if (draftData.formData.advanceAmountItems?.length) {
          draftData.formData.advanceAmountItems.forEach((item: any) => this.addAdvanceAmountItem(item));
        }

        this.currentStepIndex = draftData.lastStepIndex || 0;
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  }

  clearDraft(): void {
    localStorage.removeItem('draft_combined_request');
    this.combinedRequestForm.reset();
    this.initForm();
    this.prefillUserInfo();
    this.currentStepIndex = 0;
  }

  // ===== SUBMISSION =====

  saveAsDraft(): void {
    this.isSubmitting = true;

    const formValue = this.combinedRequestForm.value;
    const requestData = this.prepareRequestData(formValue);

    const saveObservable = this.editMode && this.requestId
      ? this.combinedRequestService.update(this.requestId, requestData)
      : this.combinedRequestService.create(requestData);

    saveObservable.pipe(takeUntil(this.destroy$)).subscribe({
      next: (response) => {
        if (response.id) this.uploadQueuedDocuments(response.id);
        this.isSubmitting = false;
        this.toastService.success('Draft saved successfully');
        this.clearDraft();
        this.router.navigate(['/combined', response.id]);
      },
      error: (error) => {
        console.error('Error saving draft:', error);
        this.isSubmitting = false;
        const msg = error?.error?.detail || error?.message || 'Failed to save draft';
        this.toastService.error(msg);
      }
    });
  }

  submitRequest(): void {
    if (!this.combinedRequestForm.valid) {
      this.formUtils.markFormGroupTouched(this.combinedRequestForm);
      this.toastService.warning('Please fill in all required fields before submitting');
      return;
    }

    if (!this.isAtLeastOneModuleSelected()) {
      this.toastService.warning('Please select at least one service (Travel, Transport, Accommodation, or Visa)');
      return;
    }

    this.isSubmitting = true;

    const formValue = this.combinedRequestForm.value;
    const requestData = this.prepareRequestData(formValue);

    // First create/update the request, then submit
    const saveObservable = this.editMode && this.requestId
      ? this.combinedRequestService.update(this.requestId, requestData)
      : this.combinedRequestService.create(requestData);

    saveObservable.pipe(takeUntil(this.destroy$)).subscribe({
      next: (savedRequest) => {
        if (savedRequest.id) this.uploadQueuedDocuments(savedRequest.id);
        // Now submit the saved request with selected approvers and skipped steps
        this.combinedRequestService.submit(savedRequest.id!, this.selectedApprovers, this.skippedSteps).pipe(takeUntil(this.destroy$)).subscribe({
          next: () => {
            this.isSubmitting = false;
            this.toastService.success('Request submitted successfully and is now pending approval');
            this.clearDraft();
            this.router.navigate(['/combined']);
          },
          error: (error) => {
            console.error('Error submitting request:', error);
            this.isSubmitting = false;
            const msg = error?.error?.detail || error?.message || 'Failed to submit request';
            this.toastService.error(msg);
          }
        });
      },
      error: (error) => {
        console.error('Error saving request:', error);
        this.isSubmitting = false;
        const msg = error?.error?.detail || error?.message || 'Failed to save request';
        this.toastService.error(msg);
      }
    });
  }

  private prepareRequestData(formValue: any): Partial<CombinedRequest> {
    return {
      includeTravel: formValue.includeTravel,
      includeTransport: formValue.includeTransport,
      includeAccommodation: formValue.includeAccommodation,
      includeVisa: formValue.includeVisa,

      requestorName: formValue.requestorName,
      staffId: formValue.staffId,
      department: formValue.department,
      position: formValue.position,
      email: formValue.email,
      phone: formValue.phone,
      costCenter: formValue.costCenter,

      travelType: formValue.travelType,
      tripType: formValue.tripType || 'Round Trip',
      travelPurpose: formValue.travelPurpose,
      departureDate: formValue.departureDate || null,
      returnDate: formValue.returnDate || null,
      destinationCountry: formValue.destinationCountry,
      destinationCity: formValue.destinationCity,
      mealDailySelections: this.mealDailySelections.getRawValue(),

      accommodationGender: formValue.accommodationGender,
      accommodationCheckin: formValue.accommodationCheckin || null,
      accommodationCheckout: formValue.accommodationCheckout || null,
      accommodationLocation: formValue.accommodationLocation,
      accommodationRoomType: formValue.accommodationRoomType,
      accommodationFlightArrivalTime: formValue.accommodationFlightArrivalTime,
      accommodationFlightDepartureTime: formValue.accommodationFlightDepartureTime,
      accommodationSpecialRequests: formValue.accommodationSpecialRequests,

      visaDestinationCountry: formValue.visaDestinationCountry,
      visaType: formValue.visaType,
      visa_trf_reference_number: formValue.visa_trf_reference_number,
      visa_request_type: formValue.visa_request_type,
      visa_trip_start_date: formValue.visa_trip_start_date || null,
      visa_trip_end_date: formValue.visa_trip_end_date || null,
      visa_travel_purpose: formValue.visa_travel_purpose,
      visa_itinerary_details: formValue.visa_itinerary_details,
      visa_approximately_arrival_date: formValue.visa_approximately_arrival_date || null,
      visa_duration_of_stay: formValue.visa_duration_of_stay,
      visa_entry_type: formValue.visa_entry_type,
      visa_work_visit_category: formValue.visa_work_visit_category,
      visa_application_fees_borne_by: formValue.visa_application_fees_borne_by,
      visa_cost_centre_number: formValue.visa_cost_centre_number,
      visa_passport_number: formValue.visa_passport_number,
      visa_passport_expiry_date: formValue.visa_passport_expiry_date || null,
      visa_passport_place_of_issuance: formValue.visa_passport_place_of_issuance,
      visa_passport_date_of_issuance: formValue.visa_passport_date_of_issuance || null,
      visa_date_of_birth: formValue.visa_date_of_birth || null,
      visa_place_of_birth: formValue.visa_place_of_birth,
      visa_citizenship: formValue.visa_citizenship,
      visa_contact_telephone: formValue.visa_contact_telephone,
      visa_marital_status: formValue.visa_marital_status,
      visa_home_address: formValue.visa_home_address,
      visa_family_information: formValue.visa_family_information,
      visa_education_details: formValue.visa_education_details,
      visa_current_employer_name: formValue.visa_current_employer_name,
      visa_current_employer_address: formValue.visa_current_employer_address,
      visa_additional_comments: formValue.visa_additional_comments,
      visa_supporting_documents_notes: formValue.visa_supporting_documents_notes,

      advanceBankAccountName: formValue.advanceBankAccountName,
      advanceBankName: formValue.advanceBankName,
      advanceBankAccountNumber: formValue.advanceBankAccountNumber,
      advanceBankCurrency: formValue.advanceBankCurrency,
      advanceBankBranchRemarks: formValue.advanceBankBranchRemarks,
      externalFullName: formValue.externalFullName,
      externalOrganization: formValue.externalOrganization,
      externalRefToAuthorityLetter: formValue.externalRefToAuthorityLetter,
      externalCostCenter: formValue.externalCostCenter,

      advanceAmountItems: this.advanceAmountItems.getRawValue().map((item: any) => ({
        dateFrom: item.dateFrom || null,
        dateTo: item.dateTo || null,
        lh: item.lh || 0,
        ma: item.ma || 0,
        oa: item.oa || 0,
        tr: item.tr || 0,
        oe: item.oe || 0,
        usd: item.usd || 0,
        remarks: item.remarks
      })),

      additionalComments: formValue.additionalComments,

      itinerarySegments: formValue.itinerarySegments?.map((s: any, i: number) => ({
        segmentOrder: i + 1,
        segmentDate: s.segmentDate || null,
        dayOfWeek: s.dayOfWeek,
        fromLocation: s.fromLocation,
        toLocation: s.toLocation,
        departureTime: s.departureTime || null,
        arrivalTime: s.arrivalTime || null,
        modeOfTravel: s.modeOfTravel,
        flightNumber: s.flightNumber,
        flightClass: s.flightClass,
        purpose: s.purpose,
        remarks: s.remarks
      })),

      transportPurpose: formValue.transportPurpose,
      transportTsrReference: formValue.transportTsrReference,

      transportSegments: formValue.transportSegments?.map((s: any, i: number) => ({
        segmentOrder: i + 1,
        pickupDate: s.pickupDate,
        dayOfWeek: s.dayOfWeek,
        pickupLocation: s.pickupLocation,
        dropoffLocation: s.dropoffLocation,
        pickupTime: s.pickupTime,
        transportType: s.transportType,
        passengers: s.passengers,
        vehicleTypePreference: s.vehicleTypePreference || '',
        notes: s.notes || ''
      })),

      passports: formValue.passports?.map((p: any) => ({
        fullName: p.fullName,
        passportNumber: p.passportNumber,
        nationality: p.nationality,
        dateOfBirth: p.dateOfBirth || null,
        placeOfBirth: p.placeOfBirth,
        issueDate: p.issueDate || null,
        expiryDate: p.expiryDate || null
      }))
    };
  }

  // ===== HELPER METHODS =====

  getIncludedModules(): string[] {
    const modules: string[] = [];
    if (this.combinedRequestForm.get('includeTravel')?.value) modules.push('Travel');
    if (this.combinedRequestForm.get('includeTransport')?.value) modules.push('Transport');
    if (this.combinedRequestForm.get('includeAccommodation')?.value) modules.push('Accommodation');
    if (this.combinedRequestForm.get('includeVisa')?.value) modules.push('Visa');
    return modules;
  }

  onApproverSelectionChange(selection: ApproverSelection): void {
    this.selectedApprovers = selection;
  }

  onApproverValidityChange(isValid: boolean): void {
    this.approverSelectionValid = isValid;
  }

  onSkippedStepsChange(skippedSteps: SkippedStepsSelection): void {
    this.skippedSteps = skippedSteps;
  }

  // ===== VISA DOCUMENT UPLOAD =====

  onVisaDocumentSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    const file = input.files[0];
    this.visaDocumentQueue.push({ file, documentType: this.newDocumentType });
    input.value = '';
  }

  removeQueuedDocument(index: number): void {
    this.visaDocumentQueue.splice(index, 1);
  }

  deleteUploadedDocument(doc: CombinedRequestDocument): void {
    if (!this.requestId) return;
    if (!doc.id) return;
    this.combinedRequestService.deleteDocument(this.requestId, doc.id).pipe(takeUntil(this.destroy$)).subscribe({
      next: () => {
        this.uploadedDocuments = this.uploadedDocuments.filter(d => d.id !== doc.id);
      },
      error: () => {
        this.toastService.error('Failed to delete document.');
      }
    });
  }

  uploadQueuedDocuments(requestId: number): void {
    if (!this.visaDocumentQueue.length) return;
    const queue = [...this.visaDocumentQueue];
    this.visaDocumentQueue = [];
    queue.forEach(item => {
      this.combinedRequestService.uploadDocument(requestId, item.file, item.documentType, 'visa')
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (doc) => this.uploadedDocuments.push(doc),
          error: () => { this.toastService.error('One or more document uploads failed.'); }
        });
    });
  }

  cancel(): void {
    this.clearDraft();
    this.router.navigate(['/combined']);
  }

  private normalizeDepartment(dept: unknown): string {
    const d = dept as { name?: string; code?: string };
    return d?.name || d?.code || '';
  }
}
