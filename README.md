# Travel Management System (TMS)

A comprehensive travel management system built with Angular 19 (frontend) and Django 5.1 (backend) to streamline travel request workflows, approvals, bookings, and expense management.

## Project Overview

The TMS application provides a complete solution for managing organizational travel including:
- Travel request forms (TRF) with multi-level approval workflows
- Visa application management
- Accommodation and transport booking
- Flight booking administration
- Expense claim processing
- Real-time notifications and email alerts
- Comprehensive reporting and insights

## Technology Stack

### Frontend
- **Framework:** Angular 19.2
- **Language:** TypeScript 5.7
- **Styling:** Bootstrap 5.3 + Custom SCSS
- **State Management:** RxJS
- **Build Tool:** Angular CLI with webpack

### Backend
- **Framework:** Django 5.1
- **Language:** Python 3.12
- **Database:** PostgreSQL
- **API:** Django REST Framework
- **Authentication:** JWT (djangorestframework-simplejwt)
- **Email:** SMTP with HTML templates

## Project Structure

```
tms-app/
├── frontend/               # Angular 19 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/      # Core services, guards, interceptors
│   │   │   ├── features/  # Feature modules (TRF, visa, bookings, etc.)
│   │   │   ├── shared/    # Shared components and utilities
│   │   │   └── admin/     # Admin panel features
│   │   ├── public/        # Static assets
│   │   └── styles/        # Global styles and design system
│   └── dist/              # Production build output
├── backend/               # Django 5.1 application
│   ├── tms_project/       # Project settings
│   ├── trf/               # Travel request form app
│   ├── visa/              # Visa application app
│   ├── accommodation/     # Accommodation booking app
│   ├── transport/         # Transport booking app
│   ├── workflows/         # Workflow engine
│   ├── notifications/     # Notification system
│   └── tests/             # Test suites
└── docs/                  # Documentation
```

## Getting Started

### Prerequisites

- **Node.js:** v20.x or higher
- **Python:** 3.12 or higher
- **PostgreSQL:** 14 or higher
- **npm:** v10.x or higher

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The application will be available at `http://localhost:4200/`

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API will be available at `http://localhost:8000/`

## Build & Deployment

### Frontend Production Build

```bash
cd frontend
npm run build
```

Build artifacts will be in `frontend/dist/tms-frontend/`

### Bundle Analysis

Analyze bundle size and composition:

```bash
cd frontend
npm run build:stats    # Generate stats.json
npm run analyze        # Open interactive bundle analyzer
```

### Backend Production Setup

```bash
cd backend
export DJANGO_SETTINGS_MODULE=tms_project.settings.production
python manage.py collectstatic
gunicorn tms_project.wsgi:application
```

## Recent Optimizations (Phase 3)

### Performance Improvements
- **Build Time:** 41% faster (20s → 11.7s)
- **Bundle Size:** Stable at 1.48MB / 254KB gzipped
- **Memory Leaks:** Fixed 21+ RxJS subscription leaks
- **Change Detection:** OnPush strategy on 4 components

### Code Quality
- Removed ~300 lines of duplicate code
- Eliminated 168 lines of mock service code
- Consolidated admin module (15→8 directories)
- Standardized subscription cleanup patterns

### Architecture
- Refactored workflow signals with base class pattern
- Split Django settings into modular structure (base, dev, prod)
- Consolidated service organization
- Removed unused SharedModule (standalone components)

### Assets
- Removed 6 unused image files (~140KB)
- Configured webpack bundle analyzer
- Optimized public asset structure

## Testing

### Frontend Tests

```bash
cd frontend
npm test              # Run all tests
npm run test:coverage # Generate coverage report
```

**Test Coverage:** 20 test files covering core functionality

### Backend Tests

```bash
cd backend
python manage.py test
```

**Test Coverage:** 4 test suites for workflows and notifications

## Key Features

### User Features
- Submit and track travel requests (TRF)
- Apply for visas with document uploads
- Book accommodation and transport
- Submit expense claims
- View approval workflow status
- Receive email and in-app notifications

### Admin Features
- Configure multi-level approval workflows
- Manage flights, accommodation, and transport
- Process bookings and approvals
- Generate reports and insights
- Configure notification templates
- Manage user roles and permissions

### Workflow Engine
- Dynamic multi-step approval workflows
- Role-based step assignments
- Email notifications at each step
- Skip, delegate, and parallel approval options
- Comprehensive audit trail

## Documentation

- **Codebase Optimization:** See `Codebase Optimization.md` for detailed optimization roadmap
- **API Documentation:** Available in backend admin panel
- **Frontend Components:** See component-level documentation in source files

## License

Proprietary - All rights reserved

## Support

For issues or questions, please contact the development team.
