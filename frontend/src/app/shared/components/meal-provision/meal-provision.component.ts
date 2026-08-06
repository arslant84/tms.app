import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { DateUtilsService } from '../../../core/utils/date-utils.service';

export interface DailyMealSelection {
  date: Date | string;
  breakfast: boolean;
  lunch: boolean;
  dinner: boolean;
  supper: boolean;
  refreshment: boolean;
}

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'supper' | 'refreshment';

/**
 * Self-contained daily meal selection grid, shared across every TSR travel-type form.
 * Decoupled from each parent's itinerary field names (domestic uses `date`,
 * external-parties uses `departureDate`, etc.) - parents extract raw dates themselves
 * and bind them in via [itineraryDates].
 */
@Component({
  selector: 'app-meal-provision',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './meal-provision.component.html',
  styleUrls: ['./meal-provision.component.scss']
})
export class MealProvisionComponent implements OnChanges {
  /** Raw dates covered by the parent's itinerary (any parseable string/Date). */
  @Input() itineraryDates: (string | Date | null | undefined)[] = [];
  /** Existing selections to restore, e.g. when editing a previously-submitted TSR. */
  @Input() initialSelections: DailyMealSelection[] = [];
  @Output() selectionsChange = new EventEmitter<DailyMealSelection[]>();

  form: FormGroup;
  dailyMealDates: Date[] = [];
  mealSummary = {
    breakfast: 0,
    lunch: 0,
    dinner: 0,
    supper: 0,
    refreshment: 0
  };

  constructor(
    private fb: FormBuilder,
    public dateUtils: DateUtilsService
  ) {
    this.form = this.fb.group({
      dailySelections: this.fb.array([])
    });
  }

  get dailySelectionsArray(): FormArray {
    return this.form.get('dailySelections') as FormArray;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['itineraryDates']) {
      this.updateMealDatesFromItinerary();
    }
  }

  private createDailyMealSelection(data?: Partial<DailyMealSelection>): FormGroup {
    const formGroup = this.fb.group({
      date: [data?.date || null, Validators.required],
      breakfast: [data?.breakfast || false],
      lunch: [data?.lunch || false],
      dinner: [data?.dinner || false],
      supper: [data?.supper || false],
      refreshment: [data?.refreshment || false]
    });

    formGroup.valueChanges.subscribe(() => {
      this.updateMealSummary();
      this.emitSelections();
    });

    return formGroup;
  }

  private updateMealDatesFromItinerary(): void {
    const dates: Date[] = [];
    (this.itineraryDates || []).forEach(raw => {
      if (!raw) return;
      const date = new Date(raw);
      if (!isNaN(date.getTime())) {
        dates.push(date);
      }
    });

    if (dates.length === 0) {
      this.dailyMealDates = [];
      this.dailySelectionsArray.clear();
      this.updateMealSummary();
      this.emitSelections();
      return;
    }

    dates.sort((a, b) => a.getTime() - b.getTime());

    // Generate all dates between first and last date (inclusive)
    const startDate = dates[0];
    const endDate = dates[dates.length - 1];
    const allDates: Date[] = [];
    for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
      allDates.push(new Date(date));
    }
    this.dailyMealDates = allDates;

    // Preserve in-progress edits once the array has been hydrated at least once;
    // otherwise (first run) seed from initialSelections for edit-mode.
    const currentSelections = this.dailySelectionsArray.length
      ? this.dailySelectionsArray.value
      : this.initialSelections;

    this.dailySelectionsArray.clear();

    allDates.forEach(date => {
      const existing = (currentSelections || []).find((sel: DailyMealSelection) => {
        const selDate = new Date(sel.date);
        return selDate.toDateString() === date.toDateString();
      });

      if (existing) {
        this.dailySelectionsArray.push(this.createDailyMealSelection(existing));
      } else {
        this.dailySelectionsArray.push(this.createDailyMealSelection({ date: date.toISOString() }));
      }
    });

    this.updateMealSummary();
    this.emitSelections();
  }

  private updateMealSummary(): void {
    // Read each control's own value rather than the FormArray's aggregated
    // .value: a row's valueChanges fires with {onlySelf: true} on patchValue,
    // which emits before the parent FormArray re-aggregates - so the FormArray's
    // .value is still one change stale at that point.
    const selections = this.dailySelectionsArray.controls.map(c => c.value as DailyMealSelection);
    this.mealSummary = {
      breakfast: selections.filter((s: DailyMealSelection) => s.breakfast).length,
      lunch: selections.filter((s: DailyMealSelection) => s.lunch).length,
      dinner: selections.filter((s: DailyMealSelection) => s.dinner).length,
      supper: selections.filter((s: DailyMealSelection) => s.supper).length,
      refreshment: selections.filter((s: DailyMealSelection) => s.refreshment).length
    };
  }

  private emitSelections(): void {
    this.selectionsChange.emit(this.dailySelectionsArray.value);
  }

  selectAllMealType(mealType: MealType): void {
    this.dailySelectionsArray.controls.forEach(control => {
      control.patchValue({ [mealType]: true });
    });
  }

  resetMealType(mealType: MealType): void {
    this.dailySelectionsArray.controls.forEach(control => {
      control.patchValue({ [mealType]: false });
    });
  }
}
