# TMS Frontend

Angular 19 frontend application for the Travel Management System (TMS).

## Overview

A modern, high-performance Angular application built with standalone components, featuring:
- Modular feature-based architecture
- OnPush change detection optimization
- Lazy-loaded modules for optimal bundle size
- Comprehensive RxJS patterns with proper memory management
- Bootstrap 5 with custom design system
- Real-time notifications and workflow management

## Technology Stack

- **Framework:** Angular 19.2
- **Language:** TypeScript 5.7
- **Styling:** Bootstrap 5.3 + Custom SCSS with design system
- **State Management:** RxJS 7.8
- **HTTP:** Angular HttpClient with interceptors
- **Forms:** Reactive Forms with validation
- **Icons:** Bootstrap Icons
- **Build:** Angular CLI with webpack

## Quick Start

### Installation

```bash
npm install
```

### Development Server

```bash
npm start
```

Navigate to `http://localhost:4200/`. The application will automatically reload on source file changes.

### Production Build

```bash
npm run build
```

Build artifacts will be stored in `dist/tms-frontend/` directory.

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm start` | Start development server on port 4200 |
| `npm run build` | Build for production |
| `npm run build:stats` | Build with bundle statistics generation |
| `npm run analyze` | Analyze bundle size with webpack-bundle-analyzer |
| `npm test` | Run unit tests with Karma |
| `npm run lint` | Run linting (TypeScript + SCSS) |
| `npm run lint:ts` | Run TypeScript linting |
| `npm run lint:scss` | Run SCSS linting |

## Bundle Analysis

The project includes webpack-bundle-analyzer for monitoring bundle size:

```bash
# Generate bundle statistics
npm run build:stats

# Open interactive bundle analyzer
npm run analyze
```

**Current Bundle Metrics:**
- Initial bundle: 1.48 MB raw / 254 KB gzipped
- Main chunk: 715 KB raw / 96.6 KB gzipped
- 12 lazy-loaded feature modules
- Build time: ~11.7 seconds (production)

## Project Structure

```
src/
├── app/
│   ├── core/                   # Core functionality
│   │   ├── guards/            # Route guards (auth, admin)
│   │   ├── interceptors/      # HTTP interceptors (auth, error)
│   │   ├── models/            # TypeScript interfaces and types
│   │   ├── services/          # Global services
│   │   └── utils/             # Utility services (date, status)
│   ├── features/               # Feature modules (lazy-loaded)
│   │   ├── admin/             # Admin panel
│   │   │   ├── accommodation/ # Accommodation management
│   │   │   ├── flights/       # Flight management
│   │   │   ├── settings/      # System settings
│   │   │   ├── transport/     # Transport management
│   │   │   └── visa/          # Visa management
│   │   ├── auth/              # Authentication
│   │   ├── bookings/          # Booking management
│   │   ├── dashboard/         # User dashboard
│   │   ├── notifications/     # Notification center
│   │   ├── trf-management/    # Travel Request Forms
│   │   ├── user-management/   # User profile
│   │   └── visa/              # Visa applications
│   ├── shared/                 # Shared components
│   │   └── components/        # Reusable UI components
│   ├── components/            # Layout components
│   ├── app.component.ts       # Root component
│   ├── app.config.ts          # Application configuration
│   └── app.routes.ts          # Route definitions
├── public/                     # Static assets
│   ├── css/                   # Bootstrap CSS
│   ├── fonts/                 # Custom fonts
│   └── img/                   # Images
├── styles/                     # Global styles
│   ├── _variables.scss        # Design system variables
│   ├── _mixins.scss          # SCSS mixins
│   └── styles.scss           # Global styles entry
└── environments/               # Environment configurations
```

## Architecture Patterns

### Standalone Components

All components use Angular 19's standalone component architecture:

```typescript
@Component({
  selector: 'app-example',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './example.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush  // Optimized
})
export class ExampleComponent { }
```

### RxJS Memory Management

All subscriptions use the `takeUntil` pattern for proper cleanup:

```typescript
export class ExampleComponent implements OnDestroy {
  private destroy$ = new Subject<void>();

  ngOnInit(): void {
    this.service.getData()
      .pipe(takeUntil(this.destroy$))
      .subscribe(data => { /* ... */ });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

### Lazy Loading

Feature modules are lazy-loaded for optimal initial bundle size:

```typescript
{
  path: 'trf',
  loadChildren: () => import('./features/trf-management/trf-management.module')
    .then(m => m.TrfManagementModule)
}
```

## Recent Optimizations

### Performance
- **Build time reduced by 41%** (20s → 11.7s)
- **OnPush change detection** on 4 presentational components
- **21+ RxJS memory leaks fixed** with takeUntil pattern
- **Bundle size stable** despite extensive refactoring

### Code Quality
- **~300 lines duplicate code removed**
- **168 lines mock code eliminated**
- **Admin module consolidated** from 15 to 8 directories
- **Unused assets removed** (~140KB saved)

### Architecture
- Removed unused SharedModule (all components standalone)
- Consolidated TRF service to feature module
- Standardized subscription cleanup patterns
- Reorganized admin module structure

## Design System

The application uses a comprehensive design system with:
- Consistent color palette and spacing
- Reusable SCSS variables and mixins
- Typography scale
- Component-level styling patterns

See `src/styles/_variables.scss` for the complete design system.

## Testing

```bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --code-coverage
```

**Current Test Coverage:**
- 20 `.spec.ts` test files
- Core services covered
- Component unit tests

## Code Scaffolding

Generate new components:

```bash
# Component
ng generate component features/example/components/example

# Service
ng generate service features/example/services/example

# Guard
ng generate guard core/guards/example
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development Guidelines

1. **Components:** Use standalone components with OnPush when possible
2. **Services:** Provide in root or feature module as appropriate
3. **Subscriptions:** Always use `takeUntil` for cleanup
4. **Forms:** Use Reactive Forms with typed form controls
5. **Styling:** Follow the design system variables
6. **Imports:** Import only what you need (tree-shaking)

## Additional Resources

- [Angular Documentation](https://angular.dev)
- [Angular CLI Reference](https://angular.dev/tools/cli)
- [RxJS Documentation](https://rxjs.dev)
- [Bootstrap Documentation](https://getbootstrap.com/docs/5.3)
