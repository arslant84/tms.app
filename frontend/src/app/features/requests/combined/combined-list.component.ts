import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import type { Observable } from 'rxjs';
import { BaseListComponent } from '../../../shared/base/base-list.component';
import { CombinedRequestService } from './services/combined-request.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

interface CombinedListItem {
  id: number;
  requestNumber?: string;
  requestorName?: string;
  staffId?: string;
  department?: string;
  status?: string;
  submittedAt?: string;
  travelPurpose?: string;
  transportPurpose?: string;
  includeTravel?: boolean;
  includeTransport?: boolean;
  includeAccommodation?: boolean;
  includeVisa?: boolean;
}

@Component({
  selector: 'app-combined-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './combined-list.component.html',
  styleUrls: ['./combined-list.component.scss']
})
export class CombinedListComponent extends BaseListComponent<CombinedListItem> {
  protected entityName = 'combined';
  protected basePath = '/combined';

  private combinedRequestService = inject(CombinedRequestService);
  statuses: string[] = [];

  protected fetchDataFromService(): Observable<unknown> {
    return this.combinedRequestService.getAll(this.buildFetchParams());
  }

  protected deleteFromService(id: number): Observable<unknown> {
    return this.combinedRequestService.delete(id);
  }

  protected override handleFetchResponse(response: { results?: CombinedListItem[]; count?: number }): void {
    super.handleFetchResponse(response);
    if (this.statuses.length === 0) {
      this.statuses = [...new Set(
        (this.items as CombinedListItem[]).map(r => r.status ?? '').filter(Boolean)
      )].sort();
    }
  }

  getModuleIcons(item: CombinedListItem): { icon: string; title: string }[] {
    const modules: { icon: string; title: string }[] = [];
    if (item.includeTravel)        modules.push({ icon: 'bi-airplane',    title: 'TSR' });
    if (item.includeTransport)     modules.push({ icon: 'bi-truck',       title: 'Transport' });
    if (item.includeAccommodation) modules.push({ icon: 'bi-house-door',  title: 'Accommodation' });
    if (item.includeVisa)          modules.push({ icon: 'bi-passport',    title: 'Visa' });
    return modules;
  }

  deleteRequest(id: number, event: Event): void {
    this.deleteItem(id, event);
  }
}
