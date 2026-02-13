import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AccommodationService, AccommodationStaffHouse, AccommodationRoom } from '../../../accommodation/services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { LocationDialogComponent, LocationDialogData } from './location-dialog.component';
import { RoomDialogComponent, RoomDialogData } from './room-dialog.component';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';

@Component({
  selector: 'app-accommodation-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, LocationDialogComponent, RoomDialogComponent],
  templateUrl: './accommodation-admin.component.html',
  styleUrl: './accommodation-admin.component.scss'
})
export class AccommodationAdminComponent implements OnInit {
  @ViewChild(LocationDialogComponent) locationDialog?: LocationDialogComponent;
  @ViewChild(RoomDialogComponent) roomDialog?: RoomDialogComponent;

  // Stats
  stats = {
    total: 0,
    pending: 0,
    approved: 0,
    processing: 0,
    completed: 0,
    rejected: 0
  };

  // Tab state
  activeTab: 'locations' | 'rooms' = 'locations';

  // Locations
  locations: AccommodationStaffHouse[] = [];
  loadingLocations = false;

  // Rooms
  rooms: AccommodationRoom[] = [];
  filteredRooms: AccommodationRoom[] = [];
  loadingRooms = false;
  filterLocation = 'all';
  filterStaffHouse = 'all';

  // Dialog states
  locationDialogOpen = false;
  locationDialogData: LocationDialogData | null = null;

  roomDialogOpen = false;
  roomDialogData: RoomDialogData | null = null;

  constructor(
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    public router: Router,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.fetchStats();
    this.fetchLocations();
    this.fetchRooms();
  }

  /**
   * Fetch accommodation statistics
   */
  fetchStats(): void {
    this.accommodationService.getAllRequests({ adminView: true }).subscribe({
      next: (response: any) => {
        const requests = response.results || response || [];

        this.stats.total = requests.length;
        this.stats.pending = requests.filter((r: any) =>
          r.status && r.status.toLowerCase().includes('pending')
        ).length;
        this.stats.approved = requests.filter((r: any) =>
          r.status === 'Approved'
        ).length;
        this.stats.processing = requests.filter((r: any) =>
          r.status && r.status.toLowerCase().includes('processing')
        ).length;
        this.stats.completed = requests.filter((r: any) =>
          r.status === 'Completed'
        ).length;
        this.stats.rejected = requests.filter((r: any) =>
          r.status === 'Rejected'
        ).length;
      },
      error: (err) => {
        console.error('Error fetching stats:', err);
        // Keep default values on error
      }
    });
  }

  /**
   * Set active tab
   */
  setActiveTab(tab: 'locations' | 'rooms'): void {
    this.activeTab = tab;
  }

  /**
   * Fetch locations/staff houses
   */
  fetchLocations(): void {
    this.loadingLocations = true;

    this.accommodationService.getAllStaffHouses().subscribe({
      next: (data) => {
        this.locations = data;
        this.loadingLocations = false;
      },
      error: (err) => {
        console.error('❌ Error fetching locations:', err);
        this.toastService.error('Failed to load locations');
        this.loadingLocations = false;
      }
    });
  }

  /**
   * Fetch rooms
   */
  fetchRooms(): void {
    this.loadingRooms = true;

    this.accommodationService.getAllRooms().subscribe({
      next: (data) => {
        this.rooms = data;
        this.applyRoomFilters();
        this.loadingRooms = false;
      },
      error: (err) => {
        console.error('Error fetching rooms:', err);
        this.toastService.error('Failed to load rooms');
        this.loadingRooms = false;
      }
    });
  }

  /**
   * Apply room filters
   */
  applyRoomFilters(): void {
    this.filteredRooms = this.rooms.filter(room => {
      const matchesLocation = this.filterLocation === 'all' ||
        this.getStaffHouseLocation(room.staff_house) === this.filterLocation;
      const matchesStaffHouse = this.filterStaffHouse === 'all' ||
        room.staff_house.toString() === this.filterStaffHouse;
      return matchesLocation && matchesStaffHouse;
    });
  }

  /**
   * Get staff house location by ID
   */
  getStaffHouseLocation(staffHouseId: number): string {
    const staffHouse = this.locations.find(loc => loc.id === staffHouseId);
    return staffHouse?.location || '';
  }

  /**
   * Get staff house name by ID
   */
  getStaffHouseName(staffHouseId: number): string {
    const staffHouse = this.locations.find(loc => loc.id === staffHouseId);
    return staffHouse?.name || 'Unknown';
  }

  /**
   * Get room count for a staff house
   */
  getRoomCount(staffHouseId: number): number {
    return this.rooms.filter(room => room.staff_house === staffHouseId).length;
  }

  /**
   * Get unique locations
   */
  get uniqueLocations(): string[] {
    return Array.from(new Set(this.locations.map(loc => loc.location)));
  }

  /**
   * Get filtered staff houses based on location filter
   */
  get filteredStaffHouses(): AccommodationStaffHouse[] {
    return this.filterLocation === 'all'
      ? this.locations
      : this.locations.filter(house => house.location === this.filterLocation);
  }

  /**
   * Badge classes
   */
  getLocationBadgeClass(location: string): string {
    switch (location) {
      case 'Ashgabat': return 'badge-blue';
      case 'Kiyanly': return 'badge-green';
      case 'Turkmenbashy': return 'badge-amber';
      default: return 'badge-gray';
    }
  }

  getRoomTypeBadgeClass(type: string): string {
    switch (type) {
      case 'Single': return 'badge-blue';
      case 'Double': return 'badge-purple';
      case 'Suite': return 'badge-indigo';
      case 'Tent': return 'badge-green';
      default: return 'badge-gray';
    }
  }

  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Location management methods
   */
  openLocationDialog(): void {
    this.locationDialogData = null;
    this.locationDialogOpen = true;
  }

  editLocation(location: AccommodationStaffHouse): void {
    this.locationDialogData = {
      id: location.id,
      name: location.name,
      location: location.location as any,
      address: location.address || '',
      description: location.description || ''
    };
    this.locationDialogOpen = true;
  }

  onLocationDialogClose(): void {
    this.locationDialogOpen = false;
    this.locationDialogData = null;
  }

  onLocationSave(data: LocationDialogData): void {
    const payload = {
      name: data.name,
      location: data.location,
      address: data.address,
      description: data.description
    };

    if (data.id) {
      // Update existing location
      this.accommodationService.updateStaffHouse(data.id, payload).subscribe({
        next: (response) => {
          this.toastService.success('Location updated successfully');
          this.fetchLocations();
          this.locationDialogOpen = false;
          this.locationDialogData = null;
          if (this.locationDialog) {
            this.locationDialog.setSubmitting(false);
          }
        },
        error: (err) => {
          console.error('Error updating location:', err);
          this.toastService.error('Failed to update location: ' + (err.error?.detail || err.message));
          if (this.locationDialog) {
            this.locationDialog.setSubmitting(false);
          }
        }
      });
    } else {
      // Create new location
      this.accommodationService.createStaffHouse(payload).subscribe({
        next: () => {
          this.toastService.success('Location created successfully');
          this.fetchLocations();
          this.locationDialogOpen = false;
          this.locationDialogData = null;
          if (this.locationDialog) {
            this.locationDialog.setSubmitting(false);
          }
        },
        error: (err) => {
          console.error('❌ Error creating location:', err);
          console.error('Error details:', err.error);
          this.toastService.error('Failed to create location: ' + (err.error?.detail || err.message));
          if (this.locationDialog) {
            this.locationDialog.setSubmitting(false);
          }
        }
      });
    }
  }

  confirmDeleteLocation(location: AccommodationStaffHouse): void {
    if (confirm(`Are you sure you want to delete "${location.name}"? This will also delete all rooms in this location.`)) {
      this.deleteLocation(location);
    }
  }

  deleteLocation(location: AccommodationStaffHouse): void {
    this.accommodationService.deleteStaffHouse(location.id).subscribe({
      next: () => {
        this.toastService.success('Location deleted successfully');
        this.fetchLocations();
        this.fetchRooms(); // Refresh rooms as they may be affected
      },
      error: (err) => {
        console.error('Error deleting location:', err);
        this.toastService.error('Failed to delete location: ' + (err.error?.detail || err.message));
      }
    });
  }

  /**
   * Room management methods
   */
  openRoomDialog(): void {
    this.roomDialogData = null;
    this.roomDialogOpen = true;
  }

  editRoom(room: AccommodationRoom): void {
    this.roomDialogData = {
      id: room.id,
      staff_house: room.staff_house,
      name: room.name,
      room_type: room.room_type || '',
      capacity: room.capacity,
      status: room.status as any
    };
    this.roomDialogOpen = true;
  }

  onRoomDialogClose(): void {
    this.roomDialogOpen = false;
    this.roomDialogData = null;
  }

  onRoomSave(data: RoomDialogData): void {
    const payload = {
      staff_house: data.staff_house,
      name: data.name,
      room_type: data.room_type,
      capacity: data.capacity,
      status: data.status
    };

    if (data.id) {
      // Update existing room
      this.accommodationService.updateRoom(data.id, payload).subscribe({
        next: (response) => {
          this.toastService.success('Room updated successfully');
          this.fetchRooms();
          this.roomDialogOpen = false;
          this.roomDialogData = null;
          if (this.roomDialog) {
            this.roomDialog.setSubmitting(false);
          }
        },
        error: (err) => {
          console.error('Error updating room:', err);
          this.toastService.error('Failed to update room: ' + (err.error?.detail || err.message));
          if (this.roomDialog) {
            this.roomDialog.setSubmitting(false);
          }
        }
      });
    } else {
      // Create new room
      this.accommodationService.createRoom(payload).subscribe({
        next: (response) => {
          this.toastService.success('Room created successfully');
          this.fetchRooms();
          this.roomDialogOpen = false;
          this.roomDialogData = null;
          if (this.roomDialog) {
            this.roomDialog.setSubmitting(false);
          }
        },
        error: (err) => {
          console.error('Error creating room:', err);
          this.toastService.error('Failed to create room: ' + (err.error?.detail || err.message));
          if (this.roomDialog) {
            this.roomDialog.setSubmitting(false);
          }
        }
      });
    }
  }

  confirmDeleteRoom(room: AccommodationRoom): void {
    if (confirm(`Are you sure you want to delete "${room.name}"?`)) {
      this.deleteRoom(room);
    }
  }

  deleteRoom(room: AccommodationRoom): void {
    this.accommodationService.deleteRoom(room.id).subscribe({
      next: () => {
        this.toastService.success('Room deleted successfully');
        this.fetchRooms();
      },
      error: (err) => {
        console.error('Error deleting room:', err);
        this.toastService.error('Failed to delete room: ' + (err.error?.detail || err.message));
      }
    });
  }
}
