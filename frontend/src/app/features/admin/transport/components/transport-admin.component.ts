import { CommonModule } from "@angular/common";
import { Component, inject, type OnDestroy, type OnInit } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink } from "@angular/router";
import { Subject } from "rxjs";
import { takeUntil } from "rxjs/operators";
import { AppSettingsService } from "../../../../core/services/app-settings.service";
import { ConfirmationService } from "../../../../core/services/confirmation.service";
import { ToastService } from "../../../../core/services/toast.service";
import { DateUtilsService } from "../../../../core/utils/date-utils.service";

import { LoadingSpinnerComponent } from "../../../../shared/components/loading-spinner/loading-spinner.component";
import type {
	TransportRequest,
	VehicleAssignment,
} from "../../../transport/services/transport.service";
import { TransportService } from "../../../transport/services/transport.service";

@Component({
	selector: "app-transport-admin",
	standalone: true,
	imports: [CommonModule, FormsModule, RouterLink, LoadingSpinnerComponent],
	templateUrl: "./transport-admin.component.html",
	styleUrl: "./transport-admin.component.scss",
})
export class TransportAdminComponent implements OnInit, OnDestroy {
	private destroy$ = new Subject<void>();

	requests: TransportRequest[] = [];
	filteredRequests: TransportRequest[] = [];
	selectedRequest: TransportRequest | null = null;

	// Stats
	totalRequestsCount = 0;
	pendingReviewCount = 0;
	approvedCount = 0;
	processingCount = 0;

	// Filter criteria
	filterCriteria = {
		status: "all",
		search: "",
		dateFrom: "",
		dateTo: "",
	};

	// Pagination
	currentPage = 1;
	pageSize = 20;
	totalRequests = 0;

	// Loading states
	loading: boolean = true;
	error: string = "";
	processingId: number | string | null = null;

	// Assign vehicle modal
	showAssignVehicleModal: boolean = false;
	vehicleData: VehicleAssignment = {
		vehicle_number: "",
		vehicle_type: "COMPANY_VEHICLE",
		vehicle_capacity: 4,
		driver_name: "",
		driver_contact: "",
		driver_license: "",
		assignment_date: new Date().toISOString().split("T")[0],
	};

	// Status options for filter - populated dynamically
	statusOptions: { value: string; label: string }[] = [
		{ value: "all", label: "All Statuses" },
	];

	// Vehicle types
	vehicleTypes = [
		{ value: "COMPANY_VEHICLE", label: "Company Vehicle" },
		{ value: "HIRED_VEHICLE", label: "Hired Vehicle" },
		{ value: "RENTAL", label: "Rental" },
	];

	private transportService = inject(TransportService);
	private toastService = inject(ToastService);
	private confirmationService = inject(ConfirmationService);
	private appSettingsService = inject(AppSettingsService);
	router = inject(Router);
	dateUtils = inject(DateUtilsService);

	ngOnInit(): void {
		this.loadFilterOptions();
		this.loadRequests();
	}

	ngOnDestroy(): void {
		this.destroy$.next();
		this.destroy$.complete();
	}

	/**
	 * Load filter options dynamically from real data
	 */
	private loadFilterOptions(): void {
		this.transportService
			.getAllRequests({ adminView: true, page_size: 1000 })
			.pipe(takeUntil(this.destroy$))
			.subscribe({
				next: (response: any) => {
					const requests = response.results || response || [];
					const uniqueStatuses = [
						...new Set<string>(
							requests.map((r: any) => r.status).filter(Boolean),
						),
					].sort();
					this.statusOptions = [
						{ value: "all", label: "All Statuses" },
						...uniqueStatuses.map((s: string) => ({ value: s, label: s })),
					];
				},
				error: (err) => {
					console.error("Error loading filter options for transport:", err);
				},
			});
	}

	/**
	 * Load transport requests from API
	 */
	loadRequests(): void {
		this.loading = true;
		this.error = "";

		const filters: any = {
			page: this.currentPage,
			page_size: this.pageSize,
			adminView: true, // Show all transport requests for admin processing
		};

		if (this.filterCriteria.status !== "all") {
			filters.status = this.filterCriteria.status;
		}

		if (this.filterCriteria.search) {
			filters.search = this.filterCriteria.search;
		}

		this.transportService.getAllRequests(filters).subscribe({
			next: (response) => {
				this.requests = response.results || response;
				this.totalRequests = response.count || this.requests.length;
				this.filteredRequests = [...this.requests];
				this.calculateStats();
				this.loading = false;
			},
			error: (err) => {
				this.error =
					"Failed to load transport requests: " +
					(err.error?.message || err.message || "Unknown error");
				this.loading = false;
				console.error("Error loading requests:", err);
			},
		});
	}

	/**
	 * Calculate statistics for dashboard cards
	 */
	calculateStats(): void {
		this.totalRequestsCount = this.requests.length;
		this.pendingReviewCount = this.requests.filter((req) =>
			req.status?.toLowerCase().includes("pending"),
		).length;
		this.approvedCount = this.requests.filter(
			(req) =>
				req.status?.toLowerCase().includes("approved") &&
				!req.status?.toLowerCase().includes("processing"),
		).length;
		this.processingCount = this.requests.filter(
			(req) =>
				req.status === "Processing with Transport Admin" ||
				req.status === "Completed",
		).length;
	}

	/**
	 * Apply filters
	 */
	applyFilters(): void {
		this.currentPage = 1;
		this.loadRequests();
	}

	/**
	 * Reset filters
	 */
	resetFilters(): void {
		this.filterCriteria = {
			status: "all",
			search: "",
			dateFrom: "",
			dateTo: "",
		};
		this.currentPage = 1;
		this.loadRequests();
	}

	/**
	 * Change page
	 */
	changePage(page: number): void {
		this.currentPage = page;
		this.loadRequests();
	}

	/**
	 * View request details
	 */
	viewRequest(request: TransportRequest): void {
		this.router.navigate(["/transport", request.id]);
	}

	/**
	 * Open assign vehicle modal
	 */
	openAssignVehicleModal(request: TransportRequest): void {
		this.selectedRequest = request;
		this.vehicleData = {
			vehicle_number: "",
			vehicle_type: "COMPANY_VEHICLE",
			vehicle_capacity: 4,
			driver_name: "",
			driver_contact: "",
			driver_license: "",
			assignment_date: new Date().toISOString().split("T")[0],
		};
		this.showAssignVehicleModal = true;
	}

	/**
	 * Close assign vehicle modal
	 */
	closeAssignVehicleModal(): void {
		this.showAssignVehicleModal = false;
		this.selectedRequest = null;
	}

	/**
	 * Assign vehicle to request
	 */
	assignVehicle(): void {
		if (!this.selectedRequest) return;

		if (
			!this.vehicleData.vehicle_number ||
			!this.vehicleData.driver_name ||
			!this.vehicleData.driver_contact
		) {
			this.toastService.error("Please fill in all required fields");
			return;
		}

		this.processingId = this.selectedRequest.id;

		this.transportService
			.assignVehicle(this.selectedRequest.id, this.vehicleData)
			.subscribe({
				next: () => {
					this.toastService.success("Vehicle assigned successfully");
					this.closeAssignVehicleModal();
					this.processingId = null;
					this.loadRequests();
				},
				error: (err) => {
					this.toastService.error(
						"Failed to assign vehicle: " +
							(err.error?.message || err.message || "Unknown error"),
					);
					this.processingId = null;
					console.error("Error assigning vehicle:", err);
				},
			});
	}

	/**
	 * Approve request
	 */
	approveRequest(request: TransportRequest): void {
		this.confirmationService
			.confirm({
				title: "Approve Request",
				message: `Are you sure you want to approve request #${request.id}?`,
				confirmText: "Approve",
				type: "success",
			})
			.subscribe((confirmed) => {
				if (!confirmed) return;
				this.executeApproveRequest(request);
			});
	}

	private executeApproveRequest(request: TransportRequest): void {
		this.processingId = request.id;

		this.transportService
			.approveRequest(request.id, "Approved by Admin")
			.subscribe({
				next: () => {
					this.toastService.success("Request approved successfully");
					this.processingId = null;
					this.loadRequests();
				},
				error: (err) => {
					this.toastService.error(
						"Failed to approve request: " +
							(err.error?.message || err.message || "Unknown error"),
					);
					this.processingId = null;
					console.error("Error approving request:", err);
				},
			});
	}

	/**
	 * Reject request
	 */
	rejectRequest(request: TransportRequest): void {
		const reason = prompt("Please provide a reason for rejection:");

		if (!reason || reason.trim() === "") {
			this.toastService.error("Rejection reason is required");
			return;
		}

		this.processingId = request.id;

		this.transportService.rejectRequest(request.id, reason).subscribe({
			next: () => {
				this.toastService.success("Request rejected successfully");
				this.processingId = null;
				this.loadRequests();
			},
			error: (err) => {
				this.toastService.error(
					"Failed to reject request: " +
						(err.error?.message || err.message || "Unknown error"),
				);
				this.processingId = null;
				console.error("Error rejecting request:", err);
			},
		});
	}

	/**
	 * Complete request
	 */
	completeRequest(request: TransportRequest): void {
		this.confirmationService
			.confirm({
				title: "Complete Request",
				message: `Mark request #${request.id} as completed?`,
				confirmText: "Complete",
				type: "success",
			})
			.subscribe((confirmed) => {
				if (!confirmed) return;
				this.executeCompleteRequest(request);
			});
	}

	private executeCompleteRequest(request: TransportRequest): void {
		this.processingId = request.id;

		this.transportService.completeRequest(request.id).subscribe({
			next: () => {
				this.toastService.success("Request marked as completed");
				this.processingId = null;
				this.loadRequests();
			},
			error: (err) => {
				this.toastService.error(
					"Failed to complete request: " +
						(err.error?.message || err.message || "Unknown error"),
				);
				this.processingId = null;
				console.error("Error completing request:", err);
			},
		});
	}

	/**
	 * Get status badge class
	 */
	getStatusClass(status: string): string {
		const statusLower = status.toLowerCase();
		if (statusLower.includes("completed")) return "badge-success";
		if (statusLower.includes("approved")) return "badge-green";
		if (statusLower.includes("progress")) return "badge-info";
		if (statusLower.includes("rejected")) return "badge-red";
		if (statusLower.includes("cancelled")) return "badge-gray";
		if (statusLower.includes("pending")) return "badge-warning";
		return "badge-gray";
	}

	/**
	 * Format currency
	 */
	formatCurrency(
		amount: number | null | undefined,
		currency?: string | null,
	): string {
		if (amount === null || amount === undefined || Number.isNaN(amount)) {
			return "N/A";
		}

		const currencyCode =
			currency || this.appSettingsService.getDefaultCurrency();

		try {
			return new Intl.NumberFormat("en-US", {
				style: "currency",
				currency: currencyCode,
				minimumFractionDigits: 2,
				maximumFractionDigits: 2,
			}).format(amount);
		} catch (error) {
			console.error("Error formatting currency:", error);
			return `${currencyCode} ${amount.toFixed(2)}`;
		}
	}

	/**
	 * Check if request can be approved
	 * Dynamically checks if status starts with "Pending" (approval workflow step)
	 */
	canApprove(request: TransportRequest): boolean {
		// Any status starting with "Pending" indicates it's awaiting approval
		return request.status?.startsWith("Pending") || false;
	}

	/**
	 * Check if vehicle can be assigned
	 */
	canAssignVehicle(request: TransportRequest): boolean {
		return (
			request.status === "Approved" ||
			request.status === "Processing with Transport Admin"
		);
	}

	/**
	 * Check if request can be completed
	 */
	canComplete(request: TransportRequest): boolean {
		return request.status === "Processing with Transport Admin";
	}

	/**
	 * Check if request is processing
	 */
	isProcessing(requestId: number | string): boolean {
		return this.processingId === requestId;
	}

	getTotalPassengers(request: TransportRequest): number {
		if (!request.transportDetails || request.transportDetails.length === 0)
			return 0;
		return request.transportDetails.reduce(
			(sum, detail) => sum + (detail.numberOfPassengers || 0),
			0,
		);
	}

	getFirstTransportType(request: TransportRequest): string {
		if (!request.transportDetails || request.transportDetails.length === 0)
			return "N/A";
		return request.transportDetails[0].transportType || "N/A";
	}

	/**
	 * Get total pages
	 */
	get totalPages(): number {
		return Math.ceil(this.totalRequests / this.pageSize);
	}

	/**
	 * Get page numbers for pagination
	 */
	getPageNumbers(): number[] {
		const pages: number[] = [];
		const maxPages = 5;
		let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
		const endPage = Math.min(this.totalPages, startPage + maxPages - 1);

		if (endPage - startPage + 1 < maxPages) {
			startPage = Math.max(1, endPage - maxPages + 1);
		}

		for (let i = startPage; i <= endPage; i++) {
			pages.push(i);
		}

		return pages;
	}
}
