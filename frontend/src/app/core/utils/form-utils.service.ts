import { Injectable } from '@angular/core';
import { FormGroup, FormControl, FormArray, AbstractControl } from '@angular/forms';

/**
 * Shared utility service for common form operations
 */
@Injectable({
  providedIn: 'root'
})
export class FormUtilsService {

  /**
   * Recursively marks all controls in a FormGroup as touched
   * Useful for triggering validation display on submit
   * @param formGroup The form group to mark as touched
   * @param collectInvalidFields If true, returns names of invalid required fields
   * @returns Array of invalid field names if collectInvalidFields is true
   */
  markFormGroupTouched(formGroup: FormGroup, collectInvalidFields = false): string[] {
    const invalidFields: string[] = [];

    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();

      if (collectInvalidFields && control?.invalid && control?.errors?.['required']) {
        invalidFields.push(key);
      }

      if (control instanceof FormGroup) {
        const nestedInvalid = this.markFormGroupTouched(control, collectInvalidFields);
        invalidFields.push(...nestedInvalid);
      } else if (control instanceof FormArray) {
        control.controls.forEach((ctrl: any) => {
          if (ctrl instanceof FormGroup) {
            const nestedInvalid = this.markFormGroupTouched(ctrl, collectInvalidFields);
            invalidFields.push(...nestedInvalid);
          } else {
            ctrl.markAsTouched();
          }
        });
      }
    });

    return invalidFields;
  }

  /**
   * Resets a form to its initial state
   */
  resetForm(formGroup: FormGroup): void {
    formGroup.reset();
    formGroup.markAsUntouched();
    formGroup.markAsPristine();
  }

  /**
   * Checks if a form control has an error and has been touched
   */
  hasError(control: AbstractControl | null, errorType: string): boolean {
    return !!(control && control.hasError(errorType) && control.touched);
  }

  /**
   * Gets the error message for a control
   */
  getErrorMessage(control: AbstractControl | null, fieldName: string): string {
    if (!control || !control.errors || !control.touched) {
      return '';
    }

    if (control.hasError('required')) {
      return `${fieldName} is required`;
    }
    if (control.hasError('email')) {
      return 'Please enter a valid email address';
    }
    if (control.hasError('minlength')) {
      const minLength = control.errors['minlength'].requiredLength;
      return `${fieldName} must be at least ${minLength} characters`;
    }
    if (control.hasError('maxlength')) {
      const maxLength = control.errors['maxlength'].requiredLength;
      return `${fieldName} must not exceed ${maxLength} characters`;
    }
    if (control.hasError('pattern')) {
      return `${fieldName} format is invalid`;
    }
    if (control.hasError('min')) {
      const min = control.errors['min'].min;
      return `${fieldName} must be at least ${min}`;
    }
    if (control.hasError('max')) {
      const max = control.errors['max'].max;
      return `${fieldName} must not exceed ${max}`;
    }

    return 'Invalid value';
  }
}
