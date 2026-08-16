import { CommonModule } from "@angular/common";
import {
	Component,
	EventEmitter,
	Input,
	ViewChild,
	inject,
	type OnChanges,
	type OnDestroy,
	type OnInit,
	Output,
	type SimpleChanges,
} from "@angular/core";
import {
	type FormArray,
	FormBuilder,
	type FormGroup,
	ReactiveFormsModule,
	Validators,
} from "@angular/forms";
import { Subject, takeUntil } from "rxjs";
import { FormUtilsService } from "../../../../core/utils/form-utils.service";
import { DateUtilsService } from "../../../../core/utils/date-utils.service";
import { FormSectionCardComponent } from "../../../../shared/components/form-section-card/form-section-card.component";
import { PassportUploadComponent } from "../../../../shared/components/passport-upload/passport-upload.component";
import { ItineraryEditorComponent, type ItineraryFieldConfig } from "../../../../shared/components/itinerary-editor/itinerary-editor.component";
import { AdvanceAmountEditorComponent } from "../../../../shared/components/advance-amount-editor/advance-amount-editor.component";

export interface ItinerarySegment {
	date: string;
	day: string;
	from: string;
	to: string;
	etd: string;
	eta: string;
	flightNumber: string;
	remarks?: string;
}

export interface AdvanceBankDetails {
	bankName: string;
	accountNumber: string;
	accountName?: string;
	branchAddress?: string;
	currency?: string;
}

export interface AdvanceAmountItem {
	dateFrom: string;
	dateTo: string;
	lh: number;
	ma: number;
	oa: number;
	tr: number;
	oe: number;
	usd: number;
	remarks?: string;
}

export interface PassportUploadDetails {
	file: File | null;
	fileName: string;
	fileUrl: string;
}

export interface OverseasTravelDetails {
	purpose: string;
	tripType: "One Way" | "Round Trip";
	itinerary: ItinerarySegment[];
	advanceBankDetails?: AdvanceBankDetails;
	advanceAmountRequested?: AdvanceAmountItem[];
	advanceConsentAccepted?: boolean;
	passportUpload?: PassportUploadDetails;
}

@Component({
	selector: "app-overseas-travel-details",
	standalone: true,
	imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, PassportUploadComponent, ItineraryEditorComponent, AdvanceAmountEditorComponent],
	templateUrl: "./overseas-travel-details.component.html",
	styleUrls: ["./overseas-travel-details.component.scss"],
})
export class OverseasTravelDetailsComponent
	implements OnInit, OnChanges, OnDestroy
{
	private destroy$ = new Subject<void>();

	@Input() initialData: Partial<OverseasTravelDetails> = {};
	@Output() formSubmit = new EventEmitter<OverseasTravelDetails>();
	@Output() backClick = new EventEmitter<void>();

	overseasForm!: FormGroup;

	itineraryFields: ItineraryFieldConfig[] = [
		{ key: "date", label: "Date / Дата", type: "date", required: true, requiredErrorMessage: "Date is required", isPrimaryDate: true },
		{ key: "day", label: "Day / День", type: "readonly-text" },
		{ key: "from", label: "From / Откуда", type: "text", required: true, placeholder: "Origin city/airport", requiredErrorMessage: "Origin is required" },
		{ key: "to", label: "To / Куда", type: "text", required: true, placeholder: "Destination city/airport", requiredErrorMessage: "Destination is required" },
		{ key: "etd", label: "ETD / Вылет", type: "text", placeholder: "e.g. 14:30 or Morning" },
		{ key: "eta", label: "ETA / Прилет", type: "text", placeholder: "e.g. 14:30 or Morning" },
		{ key: "flightNumber", label: "Flight", type: "text", placeholder: "e.g., LH1234" },
		{ key: "remarks", label: "Remarks / Примечания", type: "text", placeholder: "Any additional information", colSpan: 8 },
	];
	tripTypeValue: "One Way" | "Round Trip" = "One Way";
	itinerarySegments: Record<string, any>[] = [];
	itineraryDates: (string | null)[] = [];
	advanceAmounts: Record<string, any>[] = [];
	advanceAmountEditorValid = false;
	advanceConsentAccepted = false;

	@ViewChild(AdvanceAmountEditorComponent) advanceAmountEditor?: AdvanceAmountEditorComponent;

	// Passport upload
	passportFile: File | null = null;
	passportFileName: string = "";
	passportFileUrl: string = "";

	private fb = inject(FormBuilder);
	private formUtils = inject(FormUtilsService);
	private dateUtils = inject(DateUtilsService);

	ngOnInit(): void {
		this.initForm();
	}

	ngOnDestroy(): void {
		this.destroy$.next();
		this.destroy$.complete();
	}

	ngOnChanges(changes: SimpleChanges): void {
		// When initialData changes (e.g., loaded from API in edit mode), rebuild the form
		if (
			changes['initialData'] &&
			!changes['initialData'].firstChange &&
			this.overseasForm
		) {
			this.initForm(); // Rebuild form with new data
		}

		// Load existing passport file URL if available
		if (changes['initialData'] && this.initialData?.passportUpload) {
			this.passportFileName = this.initialData.passportUpload.fileName || "";
			this.passportFileUrl = this.initialData.passportUpload.fileUrl || "";
		}
	}

	private initForm(): void {
		this.overseasForm = this.fb.group({
			purpose: [
				this.initialData.purpose || "",
				[Validators.required, Validators.minLength(10)],
			],
			tripType: [this.initialData.tripType || "One Way", Validators.required],
			advanceBankDetails: this.fb.group({
				bankName: ["", Validators.required],
				accountNumber: ["", Validators.required],
				accountName: [""],
				branchAddress: [""],
				currency: ["USD"],
			}),
		});

		this.tripTypeValue = this.initialData.tripType || "One Way";

		// Set bank details if provided
		if (this.initialData.advanceBankDetails) {
			this.overseasForm.get("advanceBankDetails")?.patchValue({
				bankName: this.initialData.advanceBankDetails.bankName || "",
				accountNumber: this.initialData.advanceBankDetails.accountNumber || "",
				accountName: this.initialData.advanceBankDetails.accountName || "",
				branchAddress: this.initialData.advanceBankDetails.branchAddress || "",
				currency: this.initialData.advanceBankDetails.currency || "USD",
			});
		}

		// Watch trip type changes to drive the itinerary editor's add/remove gating
		this.overseasForm
			.get("tripType")
			?.valueChanges.pipe(takeUntil(this.destroy$))
			.subscribe((tripType) => {
				this.tripTypeValue = tripType;
			});
	}

	onItinerarySegmentsChange(segments: Record<string, any>[]): void {
		this.itinerarySegments = segments;
	}

	onItineraryDatesChange(dates: (string | null)[]): void {
		this.itineraryDates = dates;
	}

	onAdvanceAmountsChange(items: Record<string, any>[]): void {
		this.advanceAmounts = items;
	}

	onAdvanceValidityChange(valid: boolean): void {
		this.advanceAmountEditorValid = valid;
	}

	onAdvanceConsentChange(accepted: boolean): void {
		this.advanceConsentAccepted = accepted;
	}

	onSubmit(): void {
		if (this.overseasForm.valid && this.advanceAmountEditorValid) {
			const formValue = this.overseasForm.getRawValue();
			this.formSubmit.emit({
				...formValue,
				itinerary: this.itinerarySegments,
				advanceAmountRequested: this.advanceAmounts,
				advanceConsentAccepted: this.advanceConsentAccepted,
			});
		} else {
			this.formUtils.markFormGroupTouched(this.overseasForm);
			this.advanceAmountEditor?.markConsentTouched();
		}
	}

	// Passport file handling
	onPassportFileSelected(file: File): void {
		this.passportFile = file;
		this.passportFileName = file.name;
	}

	onPassportFileRemoved(): void {
		this.passportFile = null;
		this.passportFileName = "";
		this.passportFileUrl = "";
	}

	// Public methods for wizard integration
	getFormData(): OverseasTravelDetails {
		return {
			...this.overseasForm.getRawValue(),
			itinerary: this.itinerarySegments,
			advanceAmountRequested: this.advanceAmounts,
			advanceConsentAccepted: this.advanceConsentAccepted,
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

	isValid(): boolean {
		return this.overseasForm.valid && this.advanceAmountEditorValid && !this.isItineraryIncomplete && !this.isItineraryOutOfOrder;
	}

	markAllAsTouched(): void {
		this.formUtils.markFormGroupTouched(this.overseasForm);
		this.advanceAmountEditor?.markConsentTouched();
	}

	onBack(): void {
		this.backClick.emit();
	}
}
