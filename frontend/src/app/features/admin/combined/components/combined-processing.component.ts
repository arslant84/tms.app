import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { CombinedRequestService } from '../../../requests/combined/services/combined-request.service';
import type { CombinedRequest } from '../../../requests/combined/models/combined-request.model';
import { ToastService } from '../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { AccommodationService } from '../../../accommodation/services/accommodation.service';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import type { AccommodationStaffHouse, AccommodationRoom } from '../../../accommodation/services/accommodation.service';

interface FlightForm {
  pnr: string;
  airline: string;
  flightNumber: string;
  departureAirport: string;
  arrivalAirport: string;
  departureDate: string;
  departureTime: string;
  arrivalDate: string;
  arrivalTime: string;
  notes: string;
}

interface TransportForm {
  vehicleType: string;
  vehicleNumber: string;
  driverName: string;
  driverContact: string;
  pickupTime: string;
  dropoffTime: string;
  actualRoute: string;
  bookingReference: string;
  notes: string;
}

interface AccommodationForm {
  staffHouseId: number | null;
  staffHouseName: string;
  roomId: number | null;
  roomName: string;
  checkIn: string;
  checkOut: string;
  notes: string;
}

interface VisaForm {
  visaNumber: string;
  issueDate: string;
  expiryDate: string;
  notes: string;
}

@Component({
  selector: 'app-combined-processing',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './combined-processing.component.html',
  styleUrl: './combined-processing.component.scss'
})
export class CombinedProcessingComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // ===== MODE =====
  mode: 'list' | 'detail' = 'list';

  // ===== LIST MODE =====
  approvedRequests: CombinedRequest[] = [];
  processingRequests: CombinedRequest[] = [];
  completedRequests: CombinedRequest[] = [];
  activeTab: 'approved' | 'processing' | 'completed' = 'approved';

  // ===== DETAIL/PROCESSING MODE =====
  request: CombinedRequest | null = null;
  expandedModules = new Set<string>();
  savingModule: string | null = null;

  flightForm: FlightForm = {
    pnr: '', airline: '', flightNumber: '',
    departureAirport: '', arrivalAirport: '',
    departureDate: '', departureTime: '',
    arrivalDate: '', arrivalTime: '', notes: ''
  };

  transportForm: TransportForm = {
    vehicleType: '', vehicleNumber: '', driverName: '',
    driverContact: '', pickupTime: '', dropoffTime: '',
    actualRoute: '', bookingReference: '', notes: ''
  };

  accommodationForm: AccommodationForm = {
    staffHouseId: null, staffHouseName: '', roomId: null, roomName: '', checkIn: '', checkOut: '', notes: ''
  };

  // Accommodation room selection state
  staffHouses: AccommodationStaffHouse[] = [];
  availableRooms: AccommodationRoom[] = [];
  loadingRooms = false;

  visaForm: VisaForm = {
    visaNumber: '', issueDate: '', expiryDate: '', notes: ''
  };

  // ===== SHARED STATE =====
  loading = true;
  error = '';

  constructor(
    private combinedRequestService: CombinedRequestService,
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    private router: Router,
    private route: ActivatedRoute,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService,
    public rbacService: RbacService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.accommodationService.getAllStaffHouses()
      .pipe(takeUntil(this.destroy$))
      .subscribe({ next: (houses) => { this.staffHouses = houses; }, error: () => {} });

    this.route.queryParamMap.pipe(takeUntil(this.destroy$)).subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.mode = 'detail';
        this.loadRequest(+id);
      } else {
        this.mode = 'list';
        this.loadRequests();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onStaffHouseChange(): void {
    const id = this.accommodationForm.staffHouseId;
    this.accommodationForm.roomId = null;
    this.accommodationForm.roomName = '';
    this.availableRooms = [];
    if (!id) return;

    const house = this.staffHouses.find(h => h.id === +id);
    this.accommodationForm.staffHouseName = house?.name || '';

    this.loadingRooms = true;
    this.accommodationService.getAllRooms(+id).pipe(takeUntil(this.destroy$)).subscribe({
      next: (rooms) => { this.availableRooms = rooms.filter(r => r.status === 'Available'); this.loadingRooms = false; },
      error: () => { this.loadingRooms = false; }
    });
  }

  onRoomChange(): void {
    const id = this.accommodationForm.roomId;
    const room = this.availableRooms.find(r => r.id === +(id ?? 0));
    this.accommodationForm.roomName = room ? `${room.name}${room.room_type ? ` (${room.room_type})` : ''}` : '';
  }

  // ===== LIST MODE =====

  loadRequests(): void {
    this.loading = true;
    this.error = '';
    this.combinedRequestService.getAll({ adminView: true, pageSize: 1000 }).subscribe({
      next: (response) => {
        const all = response.results || [];
        this.approvedRequests = all.filter(r => r.status === 'Approved');
        this.processingRequests = all.filter(r => r.status === 'Processing');
        this.completedRequests = all.filter(r => r.status === 'Completed');
        this.loading = false;
      },
      error: (err) => {
        this.error = err.message || 'Failed to load requests';
        this.loading = false;
      }
    });
  }

  get tabRequests(): CombinedRequest[] {
    switch (this.activeTab) {
      case 'approved':    return this.approvedRequests;
      case 'processing':  return this.processingRequests;
      case 'completed':   return this.completedRequests;
      default:            return [];
    }
  }

  startProcessing(request: CombinedRequest): void {
    this.router.navigate(['/admin/combined/processing'], { queryParams: { id: request.id } });
  }

  // ===== DETAIL/PROCESSING MODE =====

  loadRequest(id: number): void {
    this.loading = true;
    this.error = '';
    this.combinedRequestService.getById(id).subscribe({
      next: (req) => {
        this.request = req;
        this.preFillForms(req);
        this.loading = false;
      },
      error: (err) => {
        this.error = err.message || 'Failed to load request';
        this.loading = false;
      }
    });
  }

  private preFillForms(req: CombinedRequest): void {
    // Pre-fill accommodation dates from request data
    this.accommodationForm.checkIn  = req.accommodationCheckin  || '';
    this.accommodationForm.checkOut = req.accommodationCheckout || '';

    // Pre-fill travel airports from first/last itinerary segment
    if (req.itinerarySegments?.length) {
      const first = req.itinerarySegments[0] as { fromLocation?: string; segmentDate?: string };
      const last  = req.itinerarySegments[req.itinerarySegments.length - 1] as { toLocation?: string };
      this.flightForm.departureAirport = first.fromLocation || '';
      this.flightForm.arrivalAirport   = last.toLocation    || '';
      if (first.segmentDate) this.flightForm.departureDate = first.segmentDate;
    }

    // Re-fill from any previously saved processing data (allow editing)
    const proc = req.additionalData?.['processing'] as Record<string, Record<string, unknown>> | undefined;
    if (proc?.['travel'])         Object.assign(this.flightForm,        proc['travel']);
    if (proc?.['transport'])      Object.assign(this.transportForm,     proc['transport']);
    if (proc?.['accommodation']) {
      Object.assign(this.accommodationForm, proc['accommodation']);
      // Reload room list for the saved staff house so dropdowns reflect saved selection
      if (this.accommodationForm.staffHouseId) {
        this.loadingRooms = true;
        this.accommodationService.getAllRooms(this.accommodationForm.staffHouseId).pipe(takeUntil(this.destroy$)).subscribe({
          next: (rooms) => { this.availableRooms = rooms.filter(r => r.status === 'Available'); this.loadingRooms = false; },
          error: () => { this.loadingRooms = false; }
        });
      }
    }
    if (proc?.['visa'])           Object.assign(this.visaForm,          proc['visa']);

    // Auto-expand modules that are not yet completed
    this.getIncludedModules().forEach(m => {
      if (!this.isModuleCompleted(m)) this.expandedModules.add(m);
    });
  }

  getIncludedModules(): string[] {
    if (!this.request) return [];
    const m: string[] = [];
    if (this.request.includeTravel)        m.push('travel');
    if (this.request.includeTransport)     m.push('transport');
    if (this.request.includeAccommodation) m.push('accommodation');
    if (this.request.includeVisa)          m.push('visa');
    return m;
  }

  isModuleCompleted(module: string): boolean {
    const proc = this.request?.additionalData?.['processing'] as Record<string, any> | undefined;
    return proc?.[module]?.status === 'completed';
  }

  getModuleProcessingData(module: string): Record<string, any> | null {
    const proc = this.request?.additionalData?.['processing'] as Record<string, any> | undefined;
    return proc?.[module] ?? null;
  }

  get completedCount(): number {
    return this.getIncludedModules().filter(m => this.isModuleCompleted(m)).length;
  }

  get totalModuleCount(): number {
    return this.getIncludedModules().length;
  }

  get progressPercent(): number {
    if (this.totalModuleCount === 0) return 0;
    return Math.round((this.completedCount / this.totalModuleCount) * 100);
  }

  toggleModule(module: string): void {
    this.expandedModules.has(module)
      ? this.expandedModules.delete(module)
      : this.expandedModules.add(module);
  }

  isExpanded(module: string): boolean {
    return this.expandedModules.has(module);
  }

  saveModule(module: string): void {
    if (!this.request) return;

    let processingData: Record<string, any>;
    switch (module) {
      case 'travel':         processingData = { ...this.flightForm };        break;
      case 'transport':      processingData = { ...this.transportForm };     break;
      case 'accommodation':  processingData = { ...this.accommodationForm }; break;
      case 'visa':           processingData = { ...this.visaForm };          break;
      default: return;
    }

    this.savingModule = module;
    this.combinedRequestService.processModule(
      this.request.id!,
      module as 'travel' | 'transport' | 'accommodation' | 'visa',
      processingData
    ).subscribe({
      next: (updated) => {
        this.request = updated;
        this.savingModule = null;
        this.expandedModules.delete(module);
        this.toastService.success(`${this.getModuleLabel(module)} processing saved`);
        if (updated.status === 'Completed') {
          this.toastService.success('All modules completed — request marked as Completed');
        }
      },
      error: (err) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, `Failed to save ${module}`));
        this.savingModule = null;
      }
    });
  }

  isSaving(module: string): boolean {
    return this.savingModule === module;
  }

  // ===== UTILITIES =====

  getModuleLabel(module: string): string {
    const labels: Record<string, string> = {
      travel: 'Travel (Flight)',
      transport: 'Transport',
      accommodation: 'Accommodation',
      visa: 'Visa'
    };
    return labels[module] || module;
  }

  getModuleIcon(module: string): string {
    const icons: Record<string, string> = {
      travel: 'bi-airplane',
      transport: 'bi-car-front',
      accommodation: 'bi-building',
      visa: 'bi-passport'
    };
    return icons[module] || 'bi-circle';
  }

  getIncludedModuleLabels(request: CombinedRequest): string[] {
    const m: string[] = [];
    if (request.includeTravel)        m.push('Travel');
    if (request.includeTransport)     m.push('Transport');
    if (request.includeAccommodation) m.push('Accommodation');
    if (request.includeVisa)          m.push('Visa');
    return m;
  }

  goToOverview(): void {
    this.router.navigate(['/admin/combined']);
  }

  backToList(): void {
    this.router.navigate(['/admin/combined/processing']);
  }

  formatDate(date: string | undefined): string {
    if (!date) return '-';
    return this.dateUtils.formatDate(date, 'dd MMM yyyy');
  }

  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  canProcessModule(module: string): boolean {
    return this.rbacService.canProcessCombinedModule(
      module as 'travel' | 'transport' | 'accommodation' | 'visa'
    );
  }
}
