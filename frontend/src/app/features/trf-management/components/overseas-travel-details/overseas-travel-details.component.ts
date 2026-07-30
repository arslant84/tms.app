import { CommonModule } from "@angular/common";
import {
	Component,
	EventEmitter,
	Input,
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
import { FormSectionCardComponent } from "../../../../shared/components/form-section-card/form-section-card.component";
import { PassportUploadComponent } from "../../../../shared/components/passport-upload/passport-upload.component";
import { ItineraryEditorComponent, type ItineraryFieldConfig } from "../../../../shared/components/itinerary-editor/itinerary-editor.component";

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
	passportUpload?: PassportUploadDetails;
}

@Component({
	selector: "app-overseas-travel-details",
	standalone: true,
	imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, PassportUploadComponent, ItineraryEditorComponent],
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

	// Passport upload
	passportFile: File | null = null;
	passportFileName: string = "";
	passportFileUrl: string = "";

	private fb = inject(FormBuilder);
	private formUtils = inject(FormUtilsService);

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
			advanceAmountRequested: this.fb.array([]),
		});

		this.tripTypeValue = this.initialData.tripType || "One Way";

		// Initialize with one advance amount item
		if (
			this.initialData.advanceAmountRequested &&
			this.initialData.advanceAmountRequested.length > 0
		) {
			this.initialData.advanceAmountRequested.forEach((item) =>
				this.addAdvanceAmountItem(item),
			);
		} else {
			this.addAdvanceAmountItem();
		}

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

	get advanceAmountRequested(): FormArray {
		return this.overseasForm.get("advanceAmountRequested") as FormArray;
	}

	private createAdvanceAmountItem(
		data?: Partial<AdvanceAmountItem>,
	): FormGroup {
		const formGroup = this.fb.group({
			dateFrom: [data?.dateFrom || "", Validators.required],
			dateTo: [data?.dateTo || "", Validators.required],
			lh: [data?.lh || 0, [Validators.min(0)]],
			ma: [data?.ma || 0, [Validators.min(0)]],
			oa: [data?.oa || 0, [Validators.min(0)]],
			tr: [data?.tr || 0, [Validators.min(0)]],
			oe: [data?.oe || 0, [Validators.min(0)]],
			usd: [{ value: data?.usd || 0, disabled: true }],
			remarks: [data?.remarks || ""],
		});

		// Calculate USD when amount fields change
		["lh", "ma", "oa", "tr", "oe"].forEach((field) => {
			formGroup.get(field)?.valueChanges.subscribe(() => {
				this.calculateUSD(formGroup);
			});
		});

		return formGroup;
	}

	private calculateUSD(formGroup: FormGroup): void {
		const lh = Number(formGroup.get("lh")?.value) || 0;
		const ma = Number(formGroup.get("ma")?.value) || 0;
		const oa = Number(formGroup.get("oa")?.value) || 0;
		const tr = Number(formGroup.get("tr")?.value) || 0;
		const oe = Number(formGroup.get("oe")?.value) || 0;
		const total = lh + ma + oa + tr + oe;
		formGroup.get("usd")?.setValue(total, { emitEvent: false });
	}

	addAdvanceAmountItem(data?: Partial<AdvanceAmountItem>): void {
		this.advanceAmountRequested.push(this.createAdvanceAmountItem(data));
	}

	removeAdvanceAmountItem(index: number): void {
		if (this.advanceAmountRequested.length > 1) {
			this.advanceAmountRequested.removeAt(index);
		}
	}

	onItinerarySegmentsChange(segments: Record<string, any>[]): void {
		this.itinerarySegments = segments;
	}

	onSubmit(): void {
		if (this.overseasForm.valid) {
			const formValue = this.overseasForm.getRawValue();
			this.formSubmit.emit({
				...formValue,
				itinerary: this.itinerarySegments,
			});
		} else {
			this.formUtils.markFormGroupTouched(this.overseasForm);
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

	isValid(): boolean {
		return this.overseasForm.valid;
	}

	markAllAsTouched(): void {
		this.formUtils.markFormGroupTouched(this.overseasForm);
	}

	onBack(): void {
		this.backClick.emit();
	}
}
