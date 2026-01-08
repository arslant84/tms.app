# Modal Usage Guide

## Overview

The application now has a centralized modal system that provides:
- ✅ Modals centered in the current viewport (not fixed to top of page)
- ✅ Background scroll disabled while modal is active
- ✅ Modal content scrollable if taller than viewport
- ✅ Save/Cancel buttons always accessible (sticky footer)
- ✅ Proper cleanup on component destroy

## Files

### Global Styles
- **`frontend/src/styles/modal.scss`** - Global modal styles with proper positioning
- **`frontend/src/styles.scss`** - Imports the modal styles

### Modal Service
- **`frontend/src/app/core/services/modal.service.ts`** - Manages body scroll locking

## How to Use in Your Component

### 1. Import the Modal Service

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { ModalService } from '../../../../core/services/modal.service';

@Component({
  selector: 'app-your-component',
  templateUrl: './your-component.component.html',
  styleUrls: ['./your-component.component.scss']
})
export class YourComponent implements OnInit, OnDestroy {
  showModal = false;

  constructor(private modalService: ModalService) {}

  ngOnDestroy(): void {
    // Cleanup: ensure modal is closed and scroll unlocked
    if (this.showModal) {
      this.modalService.close();
    }
  }
}
```

### 2. Update Modal Open/Close Methods

```typescript
openModal(): void {
  this.showModal = true;
  this.modalService.open(); // Lock body scroll
}

closeModal(): void {
  this.showModal = false;
  this.modalService.close(); // Unlock body scroll
}
```

### 3. HTML Template Structure

```html
<!-- Modal -->
<div class="modal fade" [class.show]="showModal" [style.display]="showModal ? 'block' : 'none'" tabindex="-1">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">

      <!-- Header (sticky at top) -->
      <div class="modal-header">
        <h5 class="modal-title">Modal Title</h5>
        <button type="button" class="btn-close" (click)="closeModal()"></button>
      </div>

      <!-- Body (scrollable if content is long) -->
      <div class="modal-body">
        <!-- Your modal content here -->
        <p>Modal content...</p>
      </div>

      <!-- Footer (sticky at bottom, always visible) -->
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" (click)="closeModal()">
          Cancel
        </button>
        <button type="submit" class="btn btn-primary">
          Save
        </button>
      </div>

    </div>
  </div>
</div>

<!-- Modal Backdrop -->
<div class="modal-backdrop fade" [class.show]="showModal" *ngIf="showModal"></div>
```

## Modal Sizes

Available modal sizes via CSS classes on `.modal-dialog`:

- **Default (500px)**: No additional class
- **Small (300px)**: Add class `modal-sm`
- **Large (800px)**: Add class `modal-lg`
- **Extra Large (1140px)**: Add class `modal-xl`

Example:
```html
<div class="modal-dialog modal-lg">
  <!-- Large modal content -->
</div>
```

## Features

### 1. Viewport Centering
The modal is always positioned in the center of the current viewport, regardless of page scroll position. This is achieved using:
- `position: fixed` on the modal container
- Flexbox centering on the modal dialog

### 2. Body Scroll Locking
When a modal opens, the background page scroll is disabled:
- `body.modal-open` class is added
- Body overflow is hidden
- Scroll position is preserved and restored on close

### 3. Modal Content Scrolling
If modal content exceeds viewport height:
- The modal overlay scrolls (not the background)
- Custom scrollbar styling for better UX
- Header and footer remain sticky and visible

### 4. Always Accessible Buttons
Save/Cancel buttons in the footer are:
- Positioned sticky at the bottom
- Always visible even with long content
- Never hidden by scrolling

## Example: User Admin Component

See the implementation in:
- `frontend/src/app/features/user-management/components/user-admin/`

Key files:
- `user-admin.component.ts` - Modal service usage
- `user-admin.component.html` - Modal template structure
- `user-admin.component.scss` - Component-specific styles (minimal)

## Responsive Behavior

### Desktop (>576px)
- Modal has margins on all sides
- Centered in viewport
- Smooth animations

### Mobile (≤576px)
- Reduced margins (0.5rem)
- Full-width modal
- Optimized spacing

## Advanced Usage

### Multiple Modals
The ModalService tracks multiple open modals:
```typescript
// Opens first modal
this.modalService.open();

// Opens second modal (body still locked)
this.modalService.open();

// Closes second modal (body still locked)
this.modalService.close();

// Closes first modal (body unlocked)
this.modalService.close();
```

### Force Close All
```typescript
this.modalService.closeAll(); // Close all modals and unlock scroll
```

### Check Open Modals
```typescript
const count = this.modalService.getOpenModalsCount();
console.log(`${count} modals are currently open`);
```

## Troubleshooting

### Modal appears at top of page
- Ensure `frontend/src/styles/modal.scss` is imported in `styles.scss`
- Check that `position: fixed` is applied to `.modal`

### Background still scrollable
- Verify `modalService.open()` is called when modal opens
- Check that `body.modal-open` class is added
- Ensure `ngOnDestroy()` calls `modalService.close()` for cleanup

### Buttons not visible with long content
- Verify `modal-footer` has `position: sticky; bottom: 0;`
- Check that `modal-body` has `overflow-y: auto`

### Scroll position jumps
- Ensure `modalService.close()` is called (restores scroll position)
- Check that scroll position is saved in `modalService.open()`

## Migration Checklist

To update existing components to use the new modal system:

- [ ] Import `ModalService` in component
- [ ] Add `OnDestroy` lifecycle hook
- [ ] Call `modalService.open()` when opening modal
- [ ] Call `modalService.close()` when closing modal
- [ ] Add `ngOnDestroy()` with cleanup
- [ ] Ensure modal HTML has backdrop element
- [ ] Remove component-specific modal styles (use global)
- [ ] Test scroll locking and viewport centering
- [ ] Test on mobile devices

## Support

For questions or issues with the modal system, contact the development team or create an issue in the project repository.
