# TRF Wizard Travel Type Selection Debug Guide

**Issue:** Cannot select travel types (Home Leave, Domestic, etc.) during TRF creation

## Debugging Steps

### 1. Check Browser Console
Open the browser developer console (F12) and look for:

```
TRF Wizard initialized
Current step: 1
Total steps: 3
Selected travel type: null
```

### 2. Navigate to Step 2
1. Fill in Requestor Information (Step 1)
2. Click "Next" button
3. You should see Step 2 with 4 travel type cards

### 3. Click on a Travel Type Card
Click on any of the 4 cards (Domestic, Overseas, Home Leave, External Parties)

**Expected Console Output:**
```
Travel type selected: Domestic (or whichever you clicked)
Selected travel type now: Domestic
```

### 4. Visual Feedback
When you click a travel type card, you should see:
- Border changes from gray (`border-gray-300`) to blue (`border-blue-600`)
- Background changes from white to blue-50 (`bg-blue-50`)
- A check mark icon appears in the top-right corner
- Text colors change to blue tones

### 5. Common Issues and Solutions

#### Issue A: Buttons Are Not Clickable
**Symptoms:** No console logs when clicking buttons
**Possible Causes:**
1. CSS z-index issue - another element is overlaying the buttons
2. Pointer-events disabled
3. Component not properly loaded

**Solution:**
Check in browser DevTools → Elements → Inspect the button element
- Look for `pointer-events: none` in computed styles
- Check if there's an overlay div
- Verify button has `type="button"` attribute

#### Issue B: Clicks Work But No Visual Feedback
**Symptoms:** Console logs appear but UI doesn't change
**Possible Causes:**
1. Tailwind CSS not loaded
2. Class bindings not working
3. Change detection not triggered

**Solution:**
1. Check if Tailwind CSS is included:
   - Open DevTools → Network tab
   - Look for `styles.css` or similar
   - Check if Tailwind utility classes are present

2. Force change detection by adding to component:
```typescript
import { ChangeDetectorRef } from '@angular/core';

constructor(
  private trfService: TrfService,
  private router: Router,
  private cdr: ChangeDetectorRef
) {}

onTravelTypeSelect(type: '...') {
  this.selectedTravelType = type;
  this.cdr.detectChanges(); // Force change detection
}
```

#### Issue C: Can Click But Can't Proceed to Step 3
**Symptoms:** Selection works but "Next" button doesn't move to Step 3
**Possible Cause:** Validation is blocking navigation

**Solution:**
Check console for validation error:
- Should see: `this.submitError = 'Please select a travel type'`
- If error appears even though you selected, there's a timing issue

Fix by adding slight delay:
```typescript
onTravelTypeSelect(type: '...') {
  this.selectedTravelType = type;
  this.submitError = '';
  setTimeout(() => {
    console.log('Type is now:', this.selectedTravelType);
  }, 100);
}
```

#### Issue D: Tailwind Classes Not Applied
**Symptoms:** Buttons look plain, no styling
**Possible Causes:**
1. Tailwind not configured in project
2. JIT mode not watching HTML files
3. Content paths not including component HTML

**Solution:**
Check `tailwind.config.js`:
```javascript
module.exports = {
  content: [
    "./src/**/*.{html,ts}",  // Must include .html files
  ],
  // ...
}
```

Restart dev server after making changes.

### 6. Quick Test Commands

**Check if component is loading:**
```bash
# In browser console
angular.getComponent(document.querySelector('app-trf-wizard'))
```

**Check selected travel type:**
```javascript
// In browser console
angular.getComponent(document.querySelector('app-trf-wizard')).selectedTravelType
```

**Manually set travel type:**
```javascript
// In browser console
let comp = angular.getComponent(document.querySelector('app-trf-wizard'));
comp.selectedTravelType = 'Domestic';
comp.cdr.detectChanges();
```

### 7. Check Network Tab
When you click "Next" from Step 2, there should be NO network requests.
The travel type selection is purely client-side state management.

### 8. Check for JavaScript Errors
Look in Console tab for any red errors like:
- `Cannot read property 'selectedTravelType' of undefined`
- `TypeError: ...`
- `ReferenceError: ...`

These would indicate a bigger problem with component loading.

### 9. Verify Step Navigation
**Expected Flow:**
```
Step 1 (Requestor Info) → Fill form → Click "Next"
Step 2 (Travel Type) → Click travel type card → Click "Next"
Step 3 (Travel Details) → Appropriate form loads
```

**Current Step Indicator:**
- Check stepper component shows current step correctly
- Step 2 label should be "Travel Type"

### 10. Last Resort: Simplify Button
If nothing works, temporarily simplify one button to test:

```html
<button (click)="testClick()">TEST</button>
```

```typescript
testClick() {
  alert('Button clicked!');
  this.selectedTravelType = 'Domestic';
}
```

If this works, the issue is with the complex class bindings.

## Expected Behavior Summary

1. **Step 1:** Requestor fills personal info → clicks Next
2. **Step 2:** User sees 4 travel type cards
3. **User clicks one card:**
   - Console logs "Travel type selected: X"
   - Card border turns blue
   - Card background turns light blue
   - Check mark appears
4. **User clicks Next:**
   - Validation passes (selectedTravelType is not null)
   - Wizard moves to Step 3
5. **Step 3:** Appropriate form loads based on selection

## File Locations

- **Component TS:** `frontend/src/app/features/trf-management/components/trf-wizard/trf-wizard.component.ts`
- **Component HTML:** `frontend/src/app/features/trf-management/components/trf-wizard/trf-wizard.component.html`
- **Component SCSS:** `frontend/src/app/features/trf-wizard/trf-wizard.component.scss`

## Key Code Sections

**Selection Method (TS):**
```typescript
onTravelTypeSelect(type: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties'): void {
  console.log('Travel type selected:', type);
  this.selectedTravelType = type;
  this.submitError = '';
}
```

**Button HTML:**
```html
<button
  type="button"
  (click)="onTravelTypeSelect('Domestic')"
  [class]="selectedTravelType === 'Domestic' ? '...' : '...'">
  <!-- Content -->
</button>
```

**Validation (TS):**
```typescript
if (this.currentStep === 2) {
  if (!this.selectedTravelType) {
    this.submitError = 'Please select a travel type';
    return false;
  }
}
```

## Contact for Help

If issue persists after all debugging steps:
1. Provide console log output
2. Provide screenshot of Step 2
3. Provide browser/OS information
4. Check if any browser extensions are blocking JavaScript

---

**Last Updated:** 2025-10-15
**Issue Status:** Under Investigation
