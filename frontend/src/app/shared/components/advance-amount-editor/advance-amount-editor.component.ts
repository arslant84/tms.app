import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { DateUtilsService } from '../../../core/utils/date-utils.service';

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

/**
 * Self-contained itemized advance-amount-requested editor (Date From/To, LH/MA/OA/TR/OE,
 * auto-calculated USD total, Remarks), shared across TSR travel-type forms that collect a
 * cash advance. Unlike itinerary, every consumer uses the exact same field shape, so this
 * is a fixed-shape component rather than config-driven.
 */
@Component({
  selector: 'app-advance-amount-editor',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './advance-amount-editor.component.html',
  styleUrls: ['./advance-amount-editor.component.scss']
})
export class AdvanceAmountEditorComponent implements OnInit, OnDestroy {
  @Input() initialItems: Partial<AdvanceAmountItem>[] = [];
  @Input() initialConsent = false;
  @Output() itemsChange = new EventEmitter<Record<string, any>[]>();
  /** Emits this component's own form validity (items + the required consent checkbox) so the parent form can gate submission on it. */
  @Output() validityChange = new EventEmitter<boolean>();

  form: FormGroup;
  requestorName = '';
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    public dateUtils: DateUtilsService
  ) {
    this.form = this.fb.group({
      items: this.fb.array([]),
      advanceConsent: [false, Validators.requiredTrue]
    });
  }

  get itemsArray(): FormArray {
    return this.form.get('items') as FormArray;
  }

  get totalUSD(): number {
    return this.itemsArray.controls.reduce((sum, item) => sum + (Number(item.get('usd')?.value) || 0), 0);
  }

  get periodFrom(): string | null {
    const dates = this.itemsArray.controls.map(item => item.get('dateFrom')?.value).filter(Boolean);
    return dates.length ? dates.sort()[0] : null;
  }

  get periodTo(): string | null {
    const dates = this.itemsArray.controls.map(item => item.get('dateTo')?.value).filter(Boolean);
    return dates.length ? dates.sort().at(-1) ?? null : null;
  }

  markConsentTouched(): void {
    this.form.get('advanceConsent')?.markAsTouched();
  }

  ngOnInit(): void {
    this.requestorName = this.authService.getCurrentUser()?.name || '';

    const seed = this.initialItems?.length ? this.initialItems : [{}];
    seed.forEach(item => this.itemsArray.push(this.createItem(item)));
    this.form.get('advanceConsent')?.setValue(this.initialConsent);
    this.emitItems();

    this.itemsArray.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.emitItems();
    });

    this.form.statusChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.validityChange.emit(this.form.valid);
    });
    this.validityChange.emit(this.form.valid);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createItem(data: Partial<AdvanceAmountItem>): FormGroup {
    const formGroup = this.fb.group({
      dateFrom: [data?.dateFrom || '', Validators.required],
      dateTo: [data?.dateTo || '', Validators.required],
      lh: [data?.lh || 0, [Validators.min(0)]],
      ma: [data?.ma || 0, [Validators.min(0)]],
      oa: [data?.oa || 0, [Validators.min(0)]],
      tr: [data?.tr || 0, [Validators.min(0)]],
      oe: [data?.oe || 0, [Validators.min(0)]],
      usd: [{ value: data?.usd || 0, disabled: true }],
      remarks: [data?.remarks || '']
    });

    ['lh', 'ma', 'oa', 'tr', 'oe'].forEach(field => {
      formGroup.get(field)?.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
        this.calculateUSD(formGroup);
      });
    });

    return formGroup;
  }

  private calculateUSD(formGroup: FormGroup): void {
    const lh = Number(formGroup.get('lh')?.value) || 0;
    const ma = Number(formGroup.get('ma')?.value) || 0;
    const oa = Number(formGroup.get('oa')?.value) || 0;
    const tr = Number(formGroup.get('tr')?.value) || 0;
    const oe = Number(formGroup.get('oe')?.value) || 0;
    formGroup.get('usd')?.setValue(lh + ma + oa + tr + oe, { emitEvent: false });
  }

  private emitItems(): void {
    this.itemsChange.emit(this.itemsArray.getRawValue());
  }

  addItem(): void {
    this.itemsArray.push(this.createItem({}));
  }

  removeItem(index: number): void {
    if (this.itemsArray.length > 1) {
      this.itemsArray.removeAt(index);
    }
  }
}
