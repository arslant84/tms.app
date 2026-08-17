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
  type: 'date' | 'time' | 'text' | 'readonly-text' | 'select';
  required?: boolean;
  placeholder?: string;
  /** Options for type: 'select'. */
  options?: string[];
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
  /**
   * Segment indices whose primary date is earlier than the preceding
   * segment's - plain component state, not a reactive-forms error. Native
   * `<input type="date">` exposes weird zero-padded interim values while
   * the year is being typed (e.g. "0002-08-25" for a not-yet-complete
   * "2026-08-25"), so routing this through `AbstractControl.setErrors()`
   * meant every such keystroke re-ran validity/status propagation up the
   * FormArray - on top of Angular's own per-keystroke updateValueAndValidity
   * for the same control, that compounded into a real CPU-pinning loop
   * while typing a date right after a sibling segment already had one.
   * Keeping this as inert state read directly by the template avoids
   * touching the form's validity machinery altogether.
   */
  outOfOrderIndices = new Set<number>();
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
    this.revalidateChronology();
    this.emitState();

    this.segmentsArray.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.revalidateChronology();
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
      // Date fields update on blur, not on every keystroke: native
      // `<input type="date">` reports intermediate zero-padded values while
      // the year is mid-typed (e.g. "0002-08-25"), and running this
      // component's reactive-forms pipeline (valueChanges subscribers,
      // cross-segment revalidation, Output emissions to the parent) on
      // every one of those keystrokes compounds into the browser tab
      // hanging once a second segment already holds a complete date -
      // reproduced directly with a CPU profiler showing the renderer
      // pinned at 100% mid-keystroke. Deferring to blur keeps the same
      // validation/highlighting, just computed once instead of per digit.
      group[field.key] = field.type === 'date'
        ? this.fb.control(value, {
            validators: field.required ? Validators.required : null,
            updateOn: 'blur',
          })
        : field.required
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

  /**
   * Recomputes which segments' primary date is earlier than the one before
   * it, for the red-border/inline-message highlight in the template.
   * `warnIfItineraryOutOfOrder` in the parent wizard is what actually
   * blocks the Next button - this is display-only, this component doesn't
   * know whether it's embedded in a form the wizard consults.
   */
  private revalidateChronology(): void {
    const primaryDateKey = this.fields.find(f => f.isPrimaryDate)?.key;
    if (!primaryDateKey) {
      return;
    }

    const nextOutOfOrder = new Set<number>();
    let previousDate: string | null = null;
    this.segmentsArray.controls.forEach((segment, index) => {
      const currentDate = this.asCompleteDate(segment.get(primaryDateKey)?.value);
      if (previousDate && currentDate && currentDate < previousDate) {
        nextOutOfOrder.add(index);
      }
      if (currentDate) {
        previousDate = currentDate;
      }
    });
    this.outOfOrderIndices = nextOutOfOrder;
  }

  /**
   * Native `<input type="date">` reports zero-padded interim values while
   * the year is still being typed (e.g. "0002-08-25" partway through
   * "2026-08-25"), which is syntactically a valid ISO date but not a real
   * one - excluded here so mid-typing keystrokes never feed nonsense years
   * into the chronology comparison.
   */
  private asCompleteDate(value: unknown): string | null {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return null;
    }
    return Number(value.slice(0, 4)) >= 1000 ? value : null;
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
