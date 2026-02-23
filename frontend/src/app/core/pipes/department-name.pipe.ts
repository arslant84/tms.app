import { Pipe, PipeTransform } from '@angular/core';

/**
 * Pipe to safely extract department name from various formats.
 * Handles: string, object with 'name' property, null/undefined
 *
 * Usage: {{ department | departmentName }}
 *        {{ department | departmentName:'N/A' }}
 */
@Pipe({
  name: 'departmentName',
  standalone: true
})
export class DepartmentNamePipe implements PipeTransform {
  transform(value: any, fallback: string = 'N/A'): string {
    if (!value) {
      return fallback;
    }

    if (typeof value === 'string') {
      return value || fallback;
    }

    if (typeof value === 'object' && 'name' in value) {
      return value.name || fallback;
    }

    return fallback;
  }
}
