import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, FormGroup, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { UserFormHelperService } from '../../../../core/utils/user-form-helper.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import { MealProvisionComponent, DailyMealSelection } from '../../../../shared/components/meal-provision/meal-provision.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';
import { ItineraryEditorComponent, ItineraryFieldConfig } from '../../../../shared/components/itinerary-editor/itinerary-editor.component';
import { LocationType, GuestGender, PreferredRoomType } from '../../../accommodation/models/accommodation.model';

export const DOMESTIC_CITIES = ['Ashgabat', 'Turkmenbashi', 'Turkmenabat', 'Dashoguz', 'Mary'];
export const ACCOMMODATION_LOCATIONS: LocationType[] = ['Ashgabat', 'Kiyanly', 'Turkmenbashy'];
export const ACCOMMODATION_ROOM_TYPES: PreferredRoomType[] = ['Hotel', 'Staff House', 'PKC Camp'];

export interface ItinerarySegment {
  date: Date | null;
  day: string;
  from: string;
  to: string;
  etd: string;
  eta: string;
  flightNumber: string;
  remarks?: string;
}

export interface MealProvisionDetails {
  dailySelections: DailyMealSelection[];
}

export interface PassportUploadDetails {
  file: File | null;
  fileName: string;
  fileUrl: string;
}

/** Mirrors the standalone accommodation-create form's fields exactly. */
export interface AccommodationDetails {
  required: boolean;
  gender: GuestGender | '';
  location: LocationType | '';
  checkInDate: string;
  checkInTime: string;
  checkOutDate: string;
  checkOutTime: string;
  roomType: PreferredRoomType | '';
  specialRequests: string;
}

/** Cross-field check: accommodation check-out can't be earlier than check-in. */
function accommodationDateOrderValidator(group: AbstractControl): ValidationErrors | null {
  const checkIn = group.get('checkInDate')?.value;
  const checkOut = group.get('checkOutDate')?.value;
  if (checkIn && checkOut && checkOut < checkIn) {
    return { checkOutBeforeCheckIn: true };
  }
  return null;
}

/** Mirrors the standalone transport-create form's per-journey fields exactly. */
export interface TransportJourney {
  date: string;
  day: string;
  from: string;
  to: string;
  departureTime: string;
  numberOfPassengers: number | string;
}

/** Mirrors the standalone transport-create form's fields exactly. */
export interface TransportDetails {
  required: boolean;
  purpose: string;
  journeys: TransportJourney[];
}

export interface DomesticTravelSpecificDetails {
  purposeOfTravel: string;
  tripType: 'One Way' | 'Round Trip';
  itinerary: ItinerarySegment[];
  mealProvisions: MealProvisionDetails;
  passportUpload?: PassportUploadDetails;
  accommodation: AccommodationDetails;
  transport: TransportDetails;
}

@Component({
  selector: 'app-domestic-travel-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, MealProvisionComponent, PassportUploadComponent, ItineraryEditorComponent],
  templateUrl: './domestic-travel-details.component.html',
  styleUrls: ['./domestic-travel-details.component.scss']
})
export class DomesticTravelDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<DomesticTravelSpecificDetails> = {};
  @Output() formSubmit = new EventEmitter<DomesticTravelSpecificDetails>();
  @Output() backClick = new EventEmitter<void>();

  travelForm!: FormGroup;

  itineraryFields: ItineraryFieldConfig[] = [
    { key: 'date', label: 'Date', type: 'date', required: true, requiredErrorMessage: 'Date is required', isPrimaryDate: true },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    { key: 'from', label: 'From', type: 'select', options: DOMESTIC_CITIES, required: true, requiredErrorMessage: 'Origin is required' },
    { key: 'to', label: 'To', type: 'select', options: DOMESTIC_CITIES, required: true, requiredErrorMessage: 'Destination is required' },
    { key: 'etd', label: 'ETD', type: 'text', placeholder: 'e.g. 14:30 or Morning' },
    { key: 'eta', label: 'ETA', type: 'text', placeholder: 'e.g. 14:30 or Morning' },
    { key: 'flightNumber', label: 'Flight', type: 'text' },
    { key: 'remarks', label: 'Remarks', type: 'text', colSpan: 8 }
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'Round Trip';
  itinerarySegments: Record<string, any>[] = [];
  itineraryDates: (string | null)[] = [];
  mealSelections: DailyMealSelection[] = [];

  // Passport upload
  passportFile: File | null = null;
  passportFileName: string = '';
  passportFileUrl: string = '';

  // Accommodation (embedded, mirrors the standalone accommodation-create form)
  accommodationLocations = ACCOMMODATION_LOCATIONS;
  accommodationRoomTypes = ACCOMMODATION_ROOM_TYPES;

  // Transport (embedded, mirrors the standalone transport-create form's journeys)
  transportJourneyFields: ItineraryFieldConfig[] = [
    { key: 'date', label: 'Date', type: 'date', required: true, requiredErrorMessage: 'Date is required', isPrimaryDate: true },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    { key: 'from', label: 'From', type: 'text', required: true, requiredErrorMessage: 'From location is required', placeholder: 'Starting location' },
    { key: 'to', label: 'To', type: 'text', required: true, requiredErrorMessage: 'To location is required', placeholder: 'Destination' },
    { key: 'departureTime', label: 'Departure Time', type: 'time', required: true, requiredErrorMessage: 'Departure time is required' },
    { key: 'numberOfPassengers', label: 'Number of Passengers', type: 'number', required: true, requiredErrorMessage: 'Number of passengers is required', min: 1 }
  ];
  transportSegments: Record<string, any>[] = [];

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService,
    public dateUtils: DateUtilsService,
    private userFormHelper: UserFormHelperService
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.travelForm) {
      this.initForm();  // Rebuild form with new data
    }

    // Load existing passport file URL if available
    if (changes['initialData'] && this.initialData?.passportUpload) {
      this.passportFileName = this.initialData.passportUpload.fileName || '';
      this.passportFileUrl = this.initialData.passportUpload.fileUrl || '';
    }
  }

  private initForm(): void {
    const accommodation = this.initialData.accommodation;
    const transport = this.initialData.transport;
    const userDefaults = this.userFormHelper.getUserFormDefaults();

    this.travelForm = this.fb.group({
      purposeOfTravel: [this.initialData.purposeOfTravel || '', Validators.required],
      tripType: [this.initialData.tripType || 'Round Trip', Validators.required],
      accommodation: this.fb.group({
        required: [accommodation?.required || false],
        gender: [accommodation?.gender || userDefaults.gender || ''],
        location: [accommodation?.location || ''],
        checkInDate: [accommodation?.checkInDate || '', { updateOn: 'blur' }],
        checkInTime: [accommodation?.checkInTime || ''],
        checkOutDate: [accommodation?.checkOutDate || '', { updateOn: 'blur' }],
        checkOutTime: [accommodation?.checkOutTime || ''],
        roomType: [accommodation?.roomType || ''],
        specialRequests: [accommodation?.specialRequests || '']
      }, { validators: accommodationDateOrderValidator }),
      transport: this.fb.group({
        required: [transport?.required || false],
        purpose: [transport?.purpose || '']
      })
    });

    this.transportSegments = transport?.journeys || [];

    this.tripTypeValue = this.initialData.tripType || 'Round Trip';

    // Watch trip type changes to drive the itinerary editor's add/remove gating
    this.travelForm.get('tripType')?.valueChanges.subscribe(tripType => {
      this.tripTypeValue = tripType;
    });

    // Accommodation fields are only mandatory once the requestor opts in
    const accommodationGroup = this.travelForm.get('accommodation');
    const conditionalFields = ['gender', 'location', 'checkInDate', 'checkOutDate'];
    const applyAccommodationValidators = (required: boolean) => {
      conditionalFields.forEach(key => {
        const control = accommodationGroup?.get(key);
        control?.setValidators(required ? [Validators.required] : []);
        control?.updateValueAndValidity({ emitEvent: false });
      });
    };
    applyAccommodationValidators(accommodationGroup?.get('required')?.value || false);
    accommodationGroup?.get('required')?.valueChanges.subscribe(required =>
      this.onAccommodationRequiredChange(required, applyAccommodationValidators)
    );

    // Transport's Purpose field is only mandatory once the requestor opts in,
    // matching the standalone transport-create form (Purpose of Transport is
    // always required there, since it only ever exists once you're creating one).
    const transportGroup = this.travelForm.get('transport');
    const applyTransportValidators = (required: boolean) => {
      const control = transportGroup?.get('purpose');
      control?.setValidators(required ? [Validators.required] : []);
      control?.updateValueAndValidity({ emitEvent: false });
    };
    applyTransportValidators(transportGroup?.get('required')?.value || false);
    transportGroup?.get('required')?.valueChanges.subscribe(required =>
      applyTransportValidators(required)
    );

    this.mealSelections = this.initialData.mealProvisions?.dailySelections || [];
  }

  private onAccommodationRequiredChange(required: boolean, applyValidators: (required: boolean) => void): void {
    applyValidators(required);
    if (required) {
      this.syncAccommodationDatesFromItinerary();
    }
  }

  onItinerarySegmentsChange(segments: Record<string, any>[]): void {
    this.itinerarySegments = segments;
  }

  onItineraryDatesChange(dates: (string | null)[]): void {
    this.itineraryDates = dates;
    if (this.travelForm.get('accommodation.required')?.value) {
      this.syncAccommodationDatesFromItinerary();
    }
  }

  /**
   * Defaults accommodation Check-in/Check-out to the travel itinerary's date range
   * (first segment date -> last segment date), since the requestor's stay logically
   * spans their trip. Only touches fields the user hasn't already edited by hand,
   * so it won't clobber a manual override.
   */
  private syncAccommodationDatesFromItinerary(): void {
    const validDates = this.itineraryDates.filter((d): d is string => !!d).sort();
    if (validDates.length === 0) {
      return;
    }
    const firstDate = validDates[0];
    const lastDate = validDates[validDates.length - 1];

    const checkInControl = this.travelForm.get('accommodation.checkInDate');
    const checkOutControl = this.travelForm.get('accommodation.checkOutDate');

    if (checkInControl && !checkInControl.dirty) {
      checkInControl.setValue(firstDate);
    }
    if (checkOutControl && !checkOutControl.dirty) {
      checkOutControl.setValue(lastDate);
    }
  }

  onMealSelectionsChange(selections: DailyMealSelection[]): void {
    this.mealSelections = selections;
  }

  onTransportSegmentsChange(segments: Record<string, any>[]): void {
    this.transportSegments = segments;
  }

  // Form submission
  onSubmit(): void {
    if (this.travelForm.valid) {
      this.formSubmit.emit({
        ...this.travelForm.value,
        itinerary: this.itinerarySegments,
        mealProvisions: { dailySelections: this.mealSelections },
        transport: { ...this.travelForm.value.transport, journeys: this.transportSegments }
      });
    } else {
      this.formUtils.markFormGroupTouched(this.travelForm);
    }
  }

  // Navigation
  onBack(): void {
    this.backClick.emit();
  }

  // Passport file handling
  onPassportFileSelected(file: File): void {
    this.passportFile = file;
    this.passportFileName = file.name;
  }

  onPassportFileRemoved(): void {
    this.passportFile = null;
    this.passportFileName = '';
    this.passportFileUrl = '';
  }

  // Public methods for wizard integration
  getFormData(): DomesticTravelSpecificDetails {
    return {
      ...this.travelForm.value,
      itinerary: this.itinerarySegments,
      mealProvisions: { dailySelections: this.mealSelections },
      transport: { ...this.travelForm.value.transport, journeys: this.transportSegments },
      passportUpload: {
        file: this.passportFile,
        fileName: this.passportFileName,
        fileUrl: this.passportFileUrl
      }
    };
  }

  getPassportFile(): File | null {
    return this.passportFile;
  }

  get isItineraryIncomplete(): boolean {
    return this.tripTypeValue === 'Round Trip' && this.itinerarySegments.length < 2;
  }

  get isItineraryOutOfOrder(): boolean {
    return !this.dateUtils.isChronological(this.itineraryDates);
  }

  get isTransportIncomplete(): boolean {
    return this.travelForm.get('transport.required')?.value && this.transportSegments.length === 0;
  }

  isValid(): boolean {
    return this.travelForm.valid && !this.isItineraryIncomplete && !this.isItineraryOutOfOrder
      && !this.isTransportIncomplete;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.travelForm);
  }
}
