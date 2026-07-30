import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { DateUtilsService } from '../../../core/utils/date-utils.service';

export interface ItineraryFieldConfig {
  /** Property name on each segment, e.g. 'date', 'departureDate', 'modeOfTransport'. */
  key: string;
  /** Exact label text to render (bilingual labels included verbatim where the original had them). */
  label: string;
  type: 'date' | 'time' | 'text' | 'readonly-text';
  required?: boolean;
  placeholder?: string;
  /** Custom required-error text; defaults to "<label> is required". */
  requiredErrorMessage?: string;
  /** Grid column span at the widest breakpoint (8-col grid). Defaults to 1. */
  colSpan?: number;
  /** Marks the field whose value drives (datesChange) and day-of-week autofill. */
  isPrimaryDate?: boolean;
  /** Present in the data model but not rendered (e.g. External Parties' unused arrivalDate). */
  hidden?: boolean;
}

export type TripType = 'One Way' | 'Round Trip';

/**
 * Self-contained itinerary segment editor, shared across every TSR travel-type form.
 * Each consumer declares its own field shape via [fields] - field keys, types, and
 * validators genuinely differ across the 4 TSR forms (unlike meal-provision/passport-upload,
 * which were byte-identical), so this is config-driven rather than a fixed shape.
 */
@Component({
  selector: 'app-itinerary-editor',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './itinerary-editor.component.html',
  styleUrls: ['./itinerary-editor.component.scss']
})
export class ItineraryEditorComponent implements OnInit, OnChanges, OnDestroy {
  @Input() fields: ItineraryFieldConfig[] = [];
  @Input() initialSegments: Record<string, any>[] = [];
  @Input() tripType: TripType = 'One Way';
  /** Key of the readonly day-of-week field to auto-populate; defaults to 'day'. */
  @Input() dayFieldKey = 'day';

  @Output() segmentsChange = new EventEmitter<Record<string, any>[]>();
  @Output() datesChange = new EventEmitter<(string | null)[]>();

  form: FormGroup;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    public dateUtils: DateUtilsService
  ) {
    this.form = this.fb.group({ segments: this.fb.array([]) });
  }

  get segmentsArray(): FormArray {
    return this.form.get('segments') as FormArray;
  }

  get canAdd(): boolean {
    return this.tripType === 'Round Trip';
  }

  canRemove(index: number): boolean {
    return this.segmentsArray.length > 1 && this.tripType === 'Round Trip';
  }

  ngOnInit(): void {
    const seed = this.initialSegments?.length ? this.initialSegments : [{}];
    seed.forEach(segment => this.segmentsArray.push(this.createSegment(segment)));
    this.emitState();

    this.segmentsArray.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.emitState();
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['tripType'] && !changes['tripType'].firstChange) {
      if (this.tripType === 'One Way') {
        while (this.segmentsArray.length > 1) {
          this.segmentsArray.removeAt(this.segmentsArray.length - 1);
        }
      }
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createSegment(data: Record<string, any>): FormGroup {
    const group: Record<string, any> = {};
    for (const field of this.fields) {
      const value = data?.[field.key] ?? '';
      group[field.key] = field.required
        ? [value, Validators.required]
        : [value];
    }
    const formGroup = this.fb.group(group);

    const primaryDateKey = this.fields.find(f => f.isPrimaryDate)?.key;
    if (primaryDateKey) {
      formGroup.get(primaryDateKey)?.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(value => {
        if (value) {
          const dayName = this.dateUtils.getDayOfWeek(value);
          if (dayName) {
            formGroup.get(this.dayFieldKey)?.setValue(dayName, { emitEvent: false });
          }
        }
      });
    }

    return formGroup;
  }

  addSegment(): void {
    if (!this.canAdd) {
      return;
    }
    this.segmentsArray.push(this.createSegment({}));
  }

  removeSegment(index: number): void {
    if (this.segmentsArray.length > 1) {
      this.segmentsArray.removeAt(index);
    }
  }

  private emitState(): void {
    const value = this.segmentsArray.value as Record<string, any>[];
    this.segmentsChange.emit(value);

    const primaryDateKey = this.fields.find(f => f.isPrimaryDate)?.key;
    if (primaryDateKey) {
      this.datesChange.emit(value.map(segment => segment[primaryDateKey] || null));
    }
  }
}
