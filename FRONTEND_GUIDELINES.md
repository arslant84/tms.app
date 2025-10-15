# Frontend Development Guidelines

## Critical Design Rule

**IMPORTANT:** The Angular frontend (`tms-app`) MUST match the design of the existing React project located at:

**Reference Project:** `C:\Users\Arslan\Documents\Projects\tms-app\pctsb.syntra`

## Core Principles

### 1. DO NOT Create New Components Without Review

Before creating any new component:
- ✅ Check if the component already exists in the current Angular project
- ✅ Review the corresponding React component in `pctsb.syntra` for design patterns
- ✅ Only create new components if they absolutely don't exist and are required

### 2. Revise Existing Components, Don't Replace

When working with existing Angular components:
- ✅ **Review first** - Read the existing component code
- ✅ **Compare with React** - Check the equivalent component in `pctsb.syntra`
- ✅ **Revise incrementally** - Update to match the React design
- ❌ **Don't delete and recreate** - Preserve existing structure where possible

### 3. Match Exact Design from pctsb.syntra

Ensure consistency with the React project:
- **Colors** - Use the same color palette and theme
- **Layouts** - Match spacing, padding, margins, and grid systems
- **Typography** - Use identical font families, sizes, and weights
- **Components** - Match button styles, form controls, cards, tables, etc.
- **UX Patterns** - Follow the same user interaction flows
- **Icons** - Use the same icon library and styles
- **Navigation** - Match sidebar, header, and routing patterns

## Development Process

### Step-by-Step Workflow

1. **Identify the Task**
   - Determine which module/component needs work
   - Example: "Create Dashboard component"

2. **Check Angular Project**
   ```bash
   # Search for existing components
   frontend/src/app/features/[module-name]/
   frontend/src/app/components/
   ```

3. **Review React Reference**
   ```bash
   # Check the React equivalent
   pctsb.syntra/[corresponding-path]
   ```

4. **Compare & Plan**
   - If component exists: Plan revisions needed
   - If component missing: Plan new component matching React design

5. **Implement with Consistency**
   - Use the same CSS classes/styles
   - Match HTML structure
   - Preserve Angular-specific syntax (directives, pipes, etc.)
   - Integrate with backend APIs

6. **Test & Verify**
   - Visual comparison with React version
   - Functionality testing
   - Responsive design check

## Module-by-Module Guidance

### Dashboard Module

**React Reference:** `pctsb.syntra/[dashboard-path]`

- Match card layouts for statistics
- Use the same chart library and styling
- Maintain consistent widget spacing
- Follow the same color scheme for status indicators

### TRF (Travel Request Form) Module

**React Reference:** `pctsb.syntra/[trf-path]`

- Match wizard/stepper pattern if used
- Use identical form layouts
- Preserve validation styling
- Match approval status displays

### Expense Claims Module

**React Reference:** `pctsb.syntra/[expenses-path]`

- Match expense item table design
- Use same receipt upload UI
- Follow approval workflow visualization
- Match currency/calculation displays

### Bookings Module

**React Reference:** `pctsb.syntra/[bookings-path]`

- Match flight/hotel card layouts
- Use same date picker styling
- Follow booking status indicators
- Match search and filter UI

### Admin Panel

**React Reference:** `pctsb.syntra/[admin-path]`

- Match user management table design
- Use same modal/dialog patterns
- Follow role/permission UI
- Match approval queue layouts

## Styling Standards

### CSS/SCSS Approach

Based on the React project structure, maintain:

```scss
// Use consistent spacing variables
$spacing-xs: 4px;
$spacing-sm: 8px;
$spacing-md: 16px;
$spacing-lg: 24px;
$spacing-xl: 32px;

// Match color palette
$primary-color: [from React project];
$secondary-color: [from React project];
$success-color: [from React project];
$warning-color: [from React project];
$danger-color: [from React project];

// Typography
$font-family-base: [from React project];
$font-size-base: [from React project];
```

### Component Libraries

If the React project uses specific UI libraries:
- Identify which library (Material-UI, Ant Design, Bootstrap, etc.)
- Use the Angular equivalent (Angular Material, ng-zorro, ng-bootstrap, etc.)
- Match component variants and configurations

## Common Patterns to Match

### 1. Form Patterns

```typescript
// Match form layout from React
// - Label positioning (top, left, inline)
// - Input sizing and spacing
// - Validation message styling
// - Submit button placement
```

### 2. Table Patterns

```typescript
// Match table design from React
// - Header styling
// - Row hover effects
// - Pagination design
// - Action buttons layout
```

### 3. Card Patterns

```typescript
// Match card design from React
// - Border radius
// - Shadow depth
// - Header/body/footer sections
// - Padding and spacing
```

### 4. Modal/Dialog Patterns

```typescript
// Match dialog design from React
// - Overlay opacity
// - Modal width and positioning
// - Header/footer styling
// - Close button placement
```

## Quality Checklist

Before submitting any frontend work, verify:

- [ ] Component exists or is necessary to create
- [ ] Design matches React reference in `pctsb.syntra`
- [ ] Colors and spacing are consistent
- [ ] Typography matches
- [ ] Interactive elements (buttons, links) have same styling
- [ ] Forms have identical layouts
- [ ] Icons match (type and color)
- [ ] Responsive behavior is similar
- [ ] Backend API integration is complete
- [ ] No console errors or warnings
- [ ] Cross-browser compatibility maintained

## Reference Commands

### Run Both Projects for Comparison

```bash
# Terminal 1: Run Django backend
cd backend
python manage.py runserver

# Terminal 2: Run Angular frontend (tms-app)
cd frontend
npm start

# Terminal 3: Run React project (pctsb.syntra) - for reference
cd pctsb.syntra
npm run dev
```

### Side-by-Side Visual Comparison

Open both applications in different browser windows to compare:
- Angular: `http://localhost:4200`
- React: `http://localhost:3000` (or whatever port pctsb.syntra uses)

## When in Doubt

1. **Always check pctsb.syntra first**
2. **Ask for clarification** if React design is unclear
3. **Preserve existing Angular code** when possible
4. **Document any deviations** from React design with reasons

## Future Considerations

As the project evolves:
- Keep this document updated with new patterns
- Document any approved deviations from React design
- Maintain a changelog of major UI updates
- Consider creating a shared component library for consistency

---

**Remember:** The goal is NOT to recreate the React app in Angular, but to provide a **visually and functionally consistent experience** while leveraging Angular's strengths and integrating with the Django backend.
