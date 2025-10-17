# Bootstrap Standardization

## Overview

This document describes the standardization of the TMS Angular frontend to use Bootstrap 5 exclusively for all styling.

## Decision

**Use Bootstrap 5 CSS Framework exclusively - NO Tailwind CSS utility classes**

## Rationale

1. **Bootstrap Already Configured**: Bootstrap 5 is already set up in `angular.json` with both CSS and JavaScript bundles
2. **Consistency**: Using a single CSS framework ensures consistent styling across all components
3. **Simplicity**: Bootstrap provides comprehensive utility classes without requiring custom CSS definitions
4. **Team Familiarity**: Bootstrap is widely used and well-documented
5. **Component Library**: Bootstrap includes pre-built components (cards, buttons, forms, modals, etc.)

## Implementation

### Bootstrap Configuration

Bootstrap is configured in `frontend/angular.json`:

```json
{
  "styles": [
    "node_modules/bootstrap/dist/css/bootstrap.min.css",
    "src/styles.scss"
  ],
  "scripts": [
    "node_modules/bootstrap/dist/js/bootstrap.bundle.min.js"
  ]
}
```

### Bootstrap Icons

Bootstrap Icons are used for all icon requirements:
- Available classes: `bi-*` (e.g., `bi-house-door`, `bi-globe`, `bi-people`, `bi-check-circle-fill`)
- Size classes: `fs-1`, `fs-2`, `fs-3`, `fs-4`, `fs-5`, `fs-6`

### Bootstrap Classes Used

#### Layout
- `container`, `container-fluid`
- `row`, `col`, `col-md-6`, `col-lg-4`
- `d-flex`, `flex-column`, `align-items-center`, `justify-content-between`
- `gap-2`, `gap-3`, `gap-4`

#### Components
- `card`, `card-header`, `card-body`, `card-footer`
- `btn`, `btn-primary`, `btn-secondary`, `btn-outline-primary`
- `form-control`, `form-label`, `form-select`
- `table`, `table-striped`, `table-hover`
- `badge`, `alert`, `modal`

#### Spacing
- `m-*`, `mt-*`, `mb-*`, `ms-*`, `me-*` (margin)
- `p-*`, `pt-*`, `pb-*`, `ps-*`, `pe-*` (padding)

#### Typography
- `fs-1` through `fs-6` (font sizes)
- `fw-bold`, `fw-semibold`, `fw-normal` (font weights)
- `text-primary`, `text-secondary`, `text-muted`, `text-dark`

#### Colors
- `bg-primary`, `bg-secondary`, `bg-light`, `bg-dark`
- `text-primary`, `text-secondary`, `text-muted`
- `border-primary`, `border-secondary`

#### Positioning
- `position-relative`, `position-absolute`
- `top-0`, `end-0`, `bottom-0`, `start-0`

#### Utilities
- `w-100` (width 100%)
- `h-100` (height 100%)
- `shadow`, `shadow-sm`, `shadow-lg`
- `rounded`, `rounded-lg`

### Bootstrap CSS Variables

Use Bootstrap CSS variables for custom styles to maintain consistency:

```scss
.custom-component {
  color: var(--bs-primary);
  background-color: var(--bs-light);
  border-color: var(--bs-border-color);
}
```

Common Bootstrap CSS variables:
- `--bs-primary`, `--bs-secondary`, `--bs-success`, `--bs-danger`, `--bs-warning`, `--bs-info`
- `--bs-light`, `--bs-dark`
- `--bs-border-color`, `--bs-border-radius`
- `--bs-gray-100` through `--bs-gray-900`

## Migration Example: TRF Wizard Travel Type Selection

### Before (Tailwind CSS)

```html
<div class="w-full rounded-lg border border-gray-200 bg-white shadow-lg">
  <div class="border-b border-gray-200 px-6 py-4">
    <h2 class="flex items-center gap-2 text-xl font-semibold text-gray-900">
      Select Travel Type
    </h2>
  </div>
  <div class="space-y-4 px-6 py-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <button class="relative flex flex-col items-center rounded-lg border-2 border-blue-600 bg-blue-50 px-6 py-8">
        Domestic Travel
      </button>
    </div>
  </div>
</div>
```

Required custom CSS definitions for Tailwind utility classes (100+ lines).

### After (Bootstrap 5)

```html
<div class="card shadow">
  <div class="card-header bg-light">
    <h2 class="d-flex align-items-center gap-2 mb-1 fs-5 fw-semibold text-dark">
      <i class="bi bi-map fs-4 text-primary"></i>
      Select Travel Type
    </h2>
  </div>
  <div class="card-body p-4">
    <div class="row g-3">
      <div class="col-md-6">
        <button class="btn w-100 text-start position-relative p-4 border-primary border-2 bg-primary-subtle">
          <div class="d-flex flex-column align-items-center text-center">
            <i class="bi bi-house-door fs-1 mb-3 text-primary"></i>
            <h3 class="fs-6 fw-semibold mb-2 text-primary">Domestic Travel</h3>
          </div>
        </button>
      </div>
    </div>
  </div>
</div>
```

No custom CSS required - Bootstrap classes work out of the box!

## Component-Specific SCSS

Component SCSS files should:
1. Use Bootstrap CSS variables for colors and spacing
2. Minimize custom styles
3. Extend Bootstrap classes when necessary

Example:

```scss
// Good - uses Bootstrap variables
.wizard-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;

  .loading-overlay {
    .spinner {
      border: 4px solid var(--bs-gray-300);
      border-top-color: var(--bs-primary);
    }
  }
}

// Avoid - hard-coded colors
.wizard-container {
  max-width: 1200px;

  .loading-overlay {
    .spinner {
      border: 4px solid #e5e7eb;  // ❌ Hard-coded color
      border-top-color: #2563eb;  // ❌ Hard-coded color
    }
  }
}
```

## Benefits

1. **Reduced Bundle Size**: No need for custom utility class definitions
2. **Faster Development**: Well-documented Bootstrap classes
3. **Better Maintainability**: Consistent styling across components
4. **Responsive Design**: Bootstrap's responsive utilities built-in
5. **Theme Consistency**: Bootstrap variables ensure color consistency

## Updated Components

- ✅ TRF Wizard Travel Type Selection (frontend/src/app/features/trf-management/components/trf-wizard/)
  - Replaced all Tailwind utility classes with Bootstrap equivalents
  - Updated SCSS to use Bootstrap CSS variables
  - Removed 200+ lines of custom Tailwind utility class definitions

## Next Steps

Apply Bootstrap standardization to remaining components:
1. Requestor Information form
2. Domestic Travel Details form
3. Overseas Travel Details form
4. Home Leave Details form
5. External Parties Details form
6. TRF Detail view
7. TRF List component
8. Dashboard components
9. Expense Claims components
10. All other forms and UI components

## Resources

- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Bootstrap Utilities](https://getbootstrap.com/docs/5.3/utilities/api/)
- [Bootstrap CSS Variables](https://getbootstrap.com/docs/5.3/customize/css-variables/)
