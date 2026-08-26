import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  OnChanges,
  SimpleChanges,
  Output,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { UserFormHelperService } from '../../../../core/utils/user-form-helper.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import {
  MealProvisionComponent,
  DailyMealSelection,
} from '../../../../shared/components/meal-provision/meal-provision.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';
import {
  ItineraryEditorComponent,
  ItineraryFieldConfig,
} from '../../../../shared/components/itinerary-editor/itinerary-editor.component';
import {
  LocationType,
  GuestGender,
  PreferredRoomType,
} from '../../../accommodation/models/accommodation.model';

export const DOMESTIC_CITIES = [
  'Ashgabat',
  'Balkanabat',
  'Turkmenbashi',
  'Turkmenabat',
  'Dashoguz',
  'Mary',
];
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

/**
 * Cross-field check: accommodation check-in/check-out must fall within the TSR's
 * own itinerary date range. This mirrors AccommodationRequestSerializer.validate()
 * on the backend (accommodation/serializers.py) - today that backend check is the
 * *only* place this rule is enforced, so a mismatch (e.g. a One Way TSR with a
 * single itinerary date, but the requestor manually extends checkOutDate to a
 * later date for a multi-night stay) doesn't surface until the accommodation
 * POST 400s on submit. At that point it's too late to just fix the field -
 * TrfSubmissionService.createNestedResources fires the TSR's other nested
 * resources (meals, transport, ...) concurrently via Promise.all, so that late
 * failure aborts the TSR's own submit-to-workflow call while sibling requests
 * that already fired may still have gone through, leaving a confusing
 * half-created Draft. Surfacing it here lets the user fix it before submitting.
 */
function accommodationWithinItineraryValidatorFactory(
  getItineraryDates: () => (string | null)[]
): (group: AbstractControl) => ValidationErrors | null {
  return (group: AbstractControl): ValidationErrors | null => {
    const checkIn = group.get('checkInDate')?.value;
    const checkOut = group.get('checkOutDate')?.value;
    if (!checkIn && !checkOut) {
      return null;
    }

    const validDates = getItineraryDates()
      .filter((d): d is string => !!d)
      .sort();
    if (validDates.length === 0) {
      return null;
    }

    const first = validDates[0];
    const last = validDates[validDates.length - 1];
    const outOfRange =
      (checkIn && (checkIn < first || checkIn > last)) ||
      (checkOut && (checkOut < first || checkOut > last));

    return outOfRange ? { outsideItineraryRange: { first, last } } : null;
  };
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

/**
 * Unlike the standalone transport-create form, this embedded section has no
 * purpose field of its own - the linked transport request submitted from
 * here reuses the TSR's own purposeOfTravel instead (see trf-wizard's
 * createNestedResources), since the two would otherwise say the same thing.
 */
export interface TransportDetails {
  required: boolean;
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
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormSectionCardComponent,
    MealProvisionComponent,
    PassportUploadComponent,
    ItineraryEditorComponent,
  ],
  templateUrl: './domestic-travel-details.component.html',
  styleUrls: ['./domestic-travel-details.component.scss'],
})
export class DomesticTravelDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<DomesticTravelSpecificDetails> = {};
  @Output() formSubmit = new EventEmitter<DomesticTravelSpecificDetails>();
  @Output() backClick = new EventEmitter<void>();

  @ViewChild('tripItineraryEditor') tripItineraryEditor!: ItineraryEditorComponent;
  @ViewChild('transportJourneyEditor') transportJourneyEditor!: ItineraryEditorComponent;

  travelForm!: FormGroup;

  itineraryFields: ItineraryFieldConfig[] = [
    {
      key: 'date',
      label: 'Date',
      type: 'date',
      required: true,
      requiredErrorMessage: 'Date is required',
      isPrimaryDate: true,
    },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    {
      key: 'from',
      label: 'From',
      type: 'select',
      options: DOMESTIC_CITIES,
      required: true,
      requiredErrorMessage: 'Origin is required',
      isOrigin: true,
    },
    {
      key: 'to',
      label: 'To',
      type: 'select',
      options: DOMESTIC_CITIES,
      required: true,
      requiredErrorMessage: 'Destination is required',
      isDestination: true,
    },
    {
      key: 'etd',
      label: 'ETD',
      type: 'text',
      placeholder: 'e.g. 14:30 or Morning',
      required: true,
      requiredErrorMessage: 'Departure time is required',
    },
    {
      key: 'eta',
      label: 'ETA',
      type: 'text',
      placeholder: 'e.g. 14:30 or Morning',
      required: true,
      requiredErrorMessage: 'Arrival time is required',
    },
    { key: 'flightNumber', label: 'Flight', type: 'text' },
    { key: 'remarks', label: 'Remarks', type: 'text', colSpan: 8 },
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'Round Trip';
  // ItineraryEditorComponent is shared across several travel-detail forms
  // with different segment shapes, so its own segmentsChange/initialSegments
  // are typed Record<string, unknown>[] generically - an index-signature
  // type isn't assignable to a concrete interface with named required
  // properties, so this field has to match that generic shape rather than
  // ItinerarySegment[]. See onItinerarySegmentsChange below.
  itinerarySegments: Record<string, unknown>[] = [];
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
    {
      key: 'date',
      label: 'Date',
      type: 'date',
      required: true,
      requiredErrorMessage: 'Date is required',
      isPrimaryDate: true,
    },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    {
      key: 'from',
      label: 'From',
      type: 'text',
      required: true,
      requiredErrorMessage: 'From location is required',
      placeholder: 'Starting location',
    },
    {
      key: 'to',
      label: 'To',
      type: 'text',
      required: true,
      requiredErrorMessage: 'To location is required',
      placeholder: 'Destination',
    },
    {
      key: 'departureTime',
      label: 'Departure Time',
      type: 'time',
      required: true,
      requiredErrorMessage: 'Departure time is required',
    },
    {
      key: 'numberOfPassengers',
      label: 'Number of Passengers',
      type: 'number',
      required: true,
      requiredErrorMessage: 'Number of passengers is required',
      min: 1,
    },
  ];
  // Same constraint as itinerarySegments above - matches the shared
  // ItineraryEditorComponent's generic Record<string, unknown>[] contract.
  transportSegments: Record<string, unknown>[] = [];

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
      this.initForm(); // Rebuild form with new data
    }

    // Load existing passport file URL if available
    if (changes['initialData'] && this.initialData?.passportUpload) {
      this.passportFileName = this.initialData.passportUpload.fileName || '';
      this.passportFileUrl = this.initialData.passportUpload.fileUrl || '';
    }
  }

  // High complexity here is straight-line reactive-form field setup for
  // three independent sections (main/accommodation/transport), not branchy
  // logic - a real split-up is better done on its own.
  // eslint-disable-next-line complexity
  private initForm(): void {
    const accommodation = this.initialData.accommodation;
    const transport = this.initialData.transport;
    const userDefaults = this.userFormHelper.getUserFormDefaults();

    this.travelForm = this.fb.group({
      purposeOfTravel: [this.initialData.purposeOfTravel || '', Validators.required],
      tripType: [this.initialData.tripType || 'Round Trip', Validators.required],
      accommodation: this.fb.group(
        {
          required: [accommodation?.required || false],
          gender: [accommodation?.gender || userDefaults.gender || ''],
          location: [accommodation?.location || ''],
          checkInDate: [accommodation?.checkInDate || '', { updateOn: 'blur' }],
          checkInTime: [accommodation?.checkInTime || ''],
          checkOutDate: [accommodation?.checkOutDate || '', { updateOn: 'blur' }],
          checkOutTime: [accommodation?.checkOutTime || ''],
          roomType: [accommodation?.roomType || ''],
          specialRequests: [accommodation?.specialRequests || ''],
        },
        {
          validators: [
            accommodationDateOrderValidator,
            accommodationWithinItineraryValidatorFactory(() => this.itineraryDates),
          ],
        }
      ),
      transport: this.fb.group({
        required: [transport?.required || false],
      }),
    });

    // See the getFormData() cast note above - the shared editor's
    // Record<string, unknown>[] contract vs. this form's concrete
    // TransportJourney[] input data.
    this.transportSegments = (transport?.journeys as unknown as Record<string, unknown>[]) || [];

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
    accommodationGroup
      ?.get('required')
      ?.valueChanges.subscribe(required =>
        this.onAccommodationRequiredChange(required, applyAccommodationValidators)
      );

    this.mealSelections = this.initialData.mealProvisions?.dailySelections || [];
  }

  private onAccommodationRequiredChange(
    required: boolean,
    applyValidators: (required: boolean) => void
  ): void {
    applyValidators(required);
    if (required) {
      this.syncAccommodationDatesFromItinerary();
    }
  }

  onItinerarySegmentsChange(segments: Record<string, unknown>[]): void {
    this.itinerarySegments = segments;
  }

  onItineraryDatesChange(dates: (string | null)[]): void {
    this.itineraryDates = dates;
    if (this.travelForm.get('accommodation.required')?.value) {
      this.syncAccommodationDatesFromItinerary();
    }
    // Re-run accommodationWithinItineraryValidatorFactory even when the
    // accommodation dates themselves didn't change - the itinerary dates it
    // checks against just did, and Angular only re-validates a group on its
    // own value changes, not on an external array captured by closure.
    this.travelForm.get('accommodation')?.updateValueAndValidity({ emitEvent: false });
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

  onTransportSegmentsChange(segments: Record<string, unknown>[]): void {
    this.transportSegments = segments;
  }

  // Form submission
  onSubmit(): void {
    if (this.travelForm.valid) {
      this.formSubmit.emit({
        ...this.travelForm.value,
        itinerary: this.itinerarySegments,
        mealProvisions: { dailySelections: this.mealSelections },
        transport: { ...this.travelForm.value.transport, journeys: this.transportSegments },
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
      // itinerarySegments/transportSegments come back from the shared,
      // generically-typed ItineraryEditorComponent (Record<string, unknown>[]
      // - see the field declarations above) - this cast asserts they actually
      // have the shape this form's own field configs (itineraryFields,
      // transportJourneyFields) define, which is true at runtime but not
      // something the generic editor's type can express.
      itinerary: this.itinerarySegments as unknown as ItinerarySegment[],
      mealProvisions: { dailySelections: this.mealSelections },
      transport: {
        ...this.travelForm.value.transport,
        journeys: this.transportSegments as unknown as TransportJourney[],
      },
      passportUpload: {
        file: this.passportFile,
        fileName: this.passportFileName,
        fileUrl: this.passportFileUrl,
      },
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

  /**
   * Cross-field check: every transport journey date must fall within the TSR's own
   * itinerary date range. Mirrors accommodationWithinItineraryValidatorFactory above
   * (see its comment for why this matters) but for transport - previously there was
   * NO date validation at all for transport journeys, client-side or backend-side, so
   * an out-of-range journey date would only be caught by whatever happened downstream
   * (or not caught at all - see TransportRequestCreateSerializer.validate() in
   * transport/serializers.py, which historically had no itinerary-date check either).
   */
  get isTransportOutsideItineraryRange(): boolean {
    if (!this.travelForm.get('transport.required')?.value) {
      return false;
    }
    const validDates = this.itineraryDates.filter((d): d is string => !!d).sort();
    if (validDates.length === 0) {
      return false;
    }
    const first = validDates[0];
    const last = validDates[validDates.length - 1];
    return this.transportSegments.some(segment => {
      const date = segment['date'] as string | undefined;
      return !!date && (date < first || date > last);
    });
  }

  get transportItineraryRangeText(): { first: string; last: string } | null {
    const validDates = this.itineraryDates.filter((d): d is string => !!d).sort();
    if (validDates.length === 0) {
      return null;
    }
    return { first: validDates[0], last: validDates[validDates.length - 1] };
  }

  isValid(): boolean {
    return (
      this.travelForm.valid &&
      !this.isItineraryIncomplete &&
      !this.isItineraryOutOfOrder &&
      !this.isTransportIncomplete &&
      !this.isTransportOutsideItineraryRange &&
      (!this.tripItineraryEditor || this.tripItineraryEditor.form.valid) &&
      (!this.transportJourneyEditor || this.transportJourneyEditor.form.valid)
    );
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.travelForm);
    this.tripItineraryEditor?.markAllAsTouched();
    this.transportJourneyEditor?.markAllAsTouched();
  }
}
