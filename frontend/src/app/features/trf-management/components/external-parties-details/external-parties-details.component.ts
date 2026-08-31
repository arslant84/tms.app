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
  FormArray,
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
  ACCOMMODATION_LOCATIONS,
  ACCOMMODATION_ROOM_TYPES,
  AccommodationDetails,
  TransportDetails,
  TransportJourney,
} from '../domestic-travel-details/domestic-travel-details.component';

export interface PassportUploadDetails {
  file: File | null;
  fileName: string;
  fileUrl: string;
}

export interface MealProvisionDetails {
  dailySelections: DailyMealSelection[];
}

export interface ExternalPartiesDetails {
  purpose: string;
  tripType: 'One Way' | 'Round Trip';
  externalFullName: string;
  externalOrganization: string;
  externalRefToAuthorityLetter?: string;
  externalCostCenter: string;
  itinerary: Record<string, unknown>[];
  mealProvisions: MealProvisionDetails;
  passportUpload?: PassportUploadDetails;
  accommodation: AccommodationDetails;
  transport: TransportDetails;
}

/**
 * Cross-field check: accommodation check-out can't be earlier than check-in.
 * Duplicated from domestic-travel-details.component.ts (not exported there) -
 * see this component's Accommodation section, embedded exactly the same way.
 */
function accommodationDateOrderValidator(group: AbstractControl): ValidationErrors | null {
  const checkIn = group.get('checkInDate')?.value;
  const checkOut = group.get('checkOutDate')?.value;
  if (checkIn && checkOut && checkOut < checkIn) {
    return { checkOutBeforeCheckIn: true };
  }
  return null;
}

/**
 * Cross-field check: accommodation check-in/check-out must fall within this
 * TSR's own itinerary date range. Duplicated from
 * domestic-travel-details.component.ts (not exported there) - see that
 * file's copy for the full rationale.
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

@Component({
  selector: 'app-external-parties-details',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormSectionCardComponent,
    MealProvisionComponent,
    PassportUploadComponent,
    ItineraryEditorComponent,
  ],
  templateUrl: './external-parties-details.component.html',
  styleUrls: ['./external-parties-details.component.scss'],
})
export class ExternalPartiesDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<ExternalPartiesDetails> = {};
  @Output() formSubmit = new EventEmitter<ExternalPartiesDetails>();
  @Output() backClick = new EventEmitter<void>();

  externalForm!: FormGroup;

  itineraryFields: ItineraryFieldConfig[] = [
    {
      key: 'departureDate',
      label: 'Date',
      type: 'date',
      required: true,
      requiredErrorMessage: 'Date is required',
      isPrimaryDate: true,
    },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    {
      key: 'departureTime',
      label: 'Departure Time',
      type: 'time',
      required: true,
      requiredErrorMessage: 'Departure time is required',
    },
    {
      key: 'departureLocation',
      label: 'From',
      type: 'text',
      required: true,
      placeholder: 'Origin city/airport',
      requiredErrorMessage: 'Origin location is required',
      isOrigin: true,
    },
    { key: 'arrivalDate', label: 'Arrival Date', type: 'text', hidden: true },
    {
      key: 'arrivalTime',
      label: 'Arrival Time',
      type: 'time',
      required: true,
      requiredErrorMessage: 'Arrival time is required',
    },
    {
      key: 'arrivalLocation',
      label: 'To',
      type: 'text',
      required: true,
      placeholder: 'Destination city/airport',
      requiredErrorMessage: 'Destination location is required',
      isDestination: true,
    },
    {
      key: 'modeOfTransport',
      label: 'Mode of Transport',
      type: 'text',
      required: true,
      placeholder: 'e.g., Flight, Train, Car',
      requiredErrorMessage: 'Mode of transport is required',
    },
    {
      key: 'remarks',
      label: 'Remarks',
      type: 'text',
      placeholder: 'Any additional information',
      colSpan: 8,
    },
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'One Way';
  itinerarySegments: Record<string, unknown>[] = [];
  itineraryDates: (string | null)[] = [];
  mealSelections: DailyMealSelection[] = [];

  @ViewChild(ItineraryEditorComponent) itineraryEditorRef?: ItineraryEditorComponent;
  @ViewChild('transportJourneyEditor') transportJourneyEditor!: ItineraryEditorComponent;

  // Passport upload
  passportFile: File | null = null;
  passportFileName: string = '';
  passportFileUrl: string = '';

  // Accommodation (embedded, mirrors the Domestic form's own embedded section)
  accommodationLocations = ACCOMMODATION_LOCATIONS;
  accommodationRoomTypes = ACCOMMODATION_ROOM_TYPES;

  // Transport (embedded, mirrors the Domestic form's own embedded section)
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
    if (changes['initialData'] && !changes['initialData'].firstChange && this.externalForm) {
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
  // logic - matches domestic-travel-details.component.ts's own initForm().
  // eslint-disable-next-line complexity
  private initForm(): void {
    const accommodation = this.initialData.accommodation;
    const transport = this.initialData.transport;
    const userDefaults = this.userFormHelper.getUserFormDefaults();

    this.externalForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      tripType: [this.initialData.tripType || 'One Way', Validators.required],
      externalFullName: [this.initialData.externalFullName || '', Validators.required],
      externalOrganization: [this.initialData.externalOrganization || '', Validators.required],
      externalRefToAuthorityLetter: [this.initialData.externalRefToAuthorityLetter || ''],
      externalCostCenter: [this.initialData.externalCostCenter || '', Validators.required],
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

    // See getFormData()'s cast note below - the shared editor's
    // Record<string, unknown>[] contract vs. this form's concrete
    // TransportJourney[] input data.
    this.transportSegments = (transport?.journeys as unknown as Record<string, unknown>[]) || [];

    this.tripTypeValue = this.initialData.tripType || 'One Way';

    // Watch trip type changes to drive the itinerary editor's add/remove gating
    this.externalForm.get('tripType')?.valueChanges.subscribe(tripType => {
      this.tripTypeValue = tripType;
    });

    // Accommodation fields are only mandatory once the requestor opts in
    const accommodationGroup = this.externalForm.get('accommodation');
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
    if (this.externalForm.get('accommodation.required')?.value) {
      this.syncAccommodationDatesFromItinerary();
    }
    // Re-run accommodationWithinItineraryValidatorFactory even when the
    // accommodation dates themselves didn't change - the itinerary dates it
    // checks against just did, and Angular only re-validates a group on its
    // own value changes, not on an external array captured by closure.
    this.externalForm.get('accommodation')?.updateValueAndValidity({ emitEvent: false });
  }

  /**
   * Defaults accommodation Check-in/Check-out to the travel itinerary's date range
   * (first segment date -> last segment date). Only touches fields the user hasn't
   * already edited by hand, so it won't clobber a manual override. Mirrors
   * domestic-travel-details.component.ts's own syncAccommodationDatesFromItinerary().
   */
  private syncAccommodationDatesFromItinerary(): void {
    const validDates = this.itineraryDates.filter((d): d is string => !!d).sort();
    if (validDates.length === 0) {
      return;
    }
    const firstDate = validDates[0];
    const lastDate = validDates[validDates.length - 1];

    const checkInControl = this.externalForm.get('accommodation.checkInDate');
    const checkOutControl = this.externalForm.get('accommodation.checkOutDate');

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

  onSubmit(): void {
    if (this.externalForm.valid) {
      const formValue = this.externalForm.getRawValue();
      this.formSubmit.emit({
        ...formValue,
        itinerary: this.itinerarySegments,
        mealProvisions: { dailySelections: this.mealSelections },
        transport: { ...formValue.transport, journeys: this.transportSegments },
      });
    } else {
      this.logFormErrors(this.externalForm);
      this.formUtils.markFormGroupTouched(this.externalForm);
    }
  }

  private logFormErrors(formGroup: FormGroup | FormArray, path: string = ''): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      const currentPath = path ? `${path}.${key}` : key;

      if (control instanceof FormGroup || control instanceof FormArray) {
        this.logFormErrors(control, currentPath);
      }
    });
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
  getFormData(): ExternalPartiesDetails {
    return {
      ...this.externalForm.getRawValue(),
      // itinerarySegments/transportSegments come back from the shared,
      // generically-typed ItineraryEditorComponent (Record<string, unknown>[]
      // - see the field declarations above) - this cast asserts they actually
      // have the shape this form's own field configs (itineraryFields,
      // transportJourneyFields) define, which is true at runtime but not
      // something the generic editor's type can express. Mirrors
      // domestic-travel-details.component.ts's own getFormData().
      itinerary: this.itinerarySegments,
      mealProvisions: { dailySelections: this.mealSelections },
      transport: {
        ...this.externalForm.getRawValue().transport,
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
    return (
      this.externalForm.get('transport.required')?.value && this.transportSegments.length === 0
    );
  }

  /**
   * Cross-field check: every transport journey date must fall within the TSR's own
   * itinerary date range. Mirrors domestic-travel-details.component.ts's own
   * isTransportOutsideItineraryRange getter.
   */
  get isTransportOutsideItineraryRange(): boolean {
    if (!this.externalForm.get('transport.required')?.value) {
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
      this.externalForm.valid &&
      !this.isItineraryIncomplete &&
      !this.isItineraryOutOfOrder &&
      !this.isTransportIncomplete &&
      !this.isTransportOutsideItineraryRange &&
      (!this.itineraryEditorRef || this.itineraryEditorRef.form.valid) &&
      (!this.transportJourneyEditor || this.transportJourneyEditor.form.valid)
    );
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.externalForm);
    this.itineraryEditorRef?.markAllAsTouched();
    this.transportJourneyEditor?.markAllAsTouched();
  }

  onBack(): void {
    this.backClick.emit();
  }
}
