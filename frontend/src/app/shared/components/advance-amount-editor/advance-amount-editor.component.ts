import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';

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
  @Output() itemsChange = new EventEmitter<Record<string, any>[]>();

  form: FormGroup;
  private destroy$ = new Subject<void>();

  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({ items: this.fb.array([]) });
  }

  get itemsArray(): FormArray {
    return this.form.get('items') as FormArray;
  }

  ngOnInit(): void {
    const seed = this.initialItems?.length ? this.initialItems : [{}];
    seed.forEach(item => this.itemsArray.push(this.createItem(item)));
    this.emitItems();

    this.itemsArray.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.emitItems();
    });
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
