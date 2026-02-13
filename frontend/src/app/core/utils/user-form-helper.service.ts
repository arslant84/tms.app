import { Injectable } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * User form data interface for auto-population
 */
export interface UserFormDefaults {
  fullName: string;
  staffId: string;
  department: string;
  position: string;
  email: string;
  phone: string;
}

/**
 * Shared utility service for auto-populating user details in forms
 */
@Injectable({
  providedIn: 'root'
})
export class UserFormHelperService {

  constructor(private authService: AuthService) {}

  /**
   * Get current user details for form auto-population
   * @returns User form defaults with current user data
   */
  getUserFormDefaults(): UserFormDefaults {
    const currentUser = this.authService.getCurrentUser();
    const position = this.authService.getUserPosition(currentUser);

    return {
      fullName: currentUser?.name || '',
      staffId: currentUser?.staff_id || '',
      department: currentUser?.department || '',
      position: position || '',
      email: currentUser?.email || '',
      phone: currentUser?.phone || ''
    };
  }

  /**
   * Get user full name
   * @returns Current user's full name or empty string
   */
  getUserFullName(): string {
    return this.authService.getCurrentUser()?.name || '';
  }

  /**
   * Get user staff ID
   * @returns Current user's staff ID or empty string
   */
  getUserStaffId(): string {
    return this.authService.getCurrentUser()?.staff_id || '';
  }

  /**
   * Get user department
   * @returns Current user's department or empty string
   */
  getUserDepartment(): string {
    return this.authService.getCurrentUser()?.department || '';
  }

  /**
   * Get user position/title
   * @returns Current user's position or empty string
   */
  getUserPosition(): string {
    const currentUser = this.authService.getCurrentUser();
    return this.authService.getUserPosition(currentUser) || '';
  }

  /**
   * Get user email
   * @returns Current user's email or empty string
   */
  getUserEmail(): string {
    return this.authService.getCurrentUser()?.email || '';
  }

  /**
   * Get user phone
   * @returns Current user's phone or empty string
   */
  getUserPhone(): string {
    return this.authService.getCurrentUser()?.phone || '';
  }

  /**
   * Merge user defaults with initial data (for edit mode)
   * Prioritizes initial data over user defaults
   * @param initialData The initial data from edit mode
   * @returns Merged data with fallbacks to user defaults
   */
  mergeWithUserDefaults(initialData: Partial<UserFormDefaults>): UserFormDefaults {
    const userDefaults = this.getUserFormDefaults();

    return {
      fullName: initialData.fullName || userDefaults.fullName,
      staffId: initialData.staffId || userDefaults.staffId,
      department: initialData.department || userDefaults.department,
      position: initialData.position || userDefaults.position,
      email: initialData.email || userDefaults.email,
      phone: initialData.phone || userDefaults.phone
    };
  }
}
