# TMS Application Architecture

Travel Management System — architecture reference for CTRL-1192.

---

## 1. System Overview

```mermaid
graph TD
    subgraph Client["Client Browser"]
        SPA["Angular 19 SPA<br/>(TypeScript + Angular Material)"]
    end

    subgraph Backend["Backend — Django 5 + DRF"]
        WN["WhiteNoise<br/>(serves SPA + static assets)"]
        MW["Middleware Stack<br/>CSP · CORS · CSRF · Session<br/>Maintenance · FileSizeValidation<br/>DynamicSettings · SessionTimeout"]
        API["Django REST Framework<br/>JWT Auth · drf-spectacular"]
        ADMIN["Django Admin Panel<br/>Backup · Audit · User Mgmt"]

        subgraph Apps["Domain Apps"]
            ACC["accounts<br/>Users · RBAC · MFA · Audit"]
            TRF["trf<br/>Travel Request Forms"]
            BK["bookings<br/>Flight & Hotel Bookings"]
            VISA["visa<br/>Visa Applications"]
            ACC2["accommodation<br/>Hotel/Housing"]
            TRANS["transport<br/>Ground Transport"]
            COMB["combined_request<br/>Multi-modal Requests"]
            WF["workflows<br/>Approval Workflows"]
            NOTIF["notifications<br/>Email & In-app Alerts"]
            REP["reports<br/>Analytics & Exports"]
            INS["insights<br/>Dashboard Metrics"]
            APR["approvals<br/>Unified Approval Engine"]
        end
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL 15<br/>Primary Database")]
        BACKUP["pg_dump backups<br/>backend/backups/"]
        LOGS["SIEM Log Files<br/>backend/logs/security.json"]
    end

    subgraph Security["Security Controls"]
        TOTP["TOTP / MFA<br/>(django-otp)"]
        JWT["JWT Tokens<br/>(simplejwt + blacklist)"]
        ENC["Field Encryption<br/>(Fernet — PII at rest)"]
        AUDIT["Immutable Audit Log<br/>(AdminActionLog — DB trigger)"]
    end

    SPA -->|"HTTPS + CSRF token"| WN
    WN --> MW
    MW --> API
    MW --> ADMIN
    API --> Apps
    Apps --> PG
    ADMIN --> PG
    PG --> BACKUP
    Apps --> LOGS
    ACC --> TOTP
    ACC --> JWT
    ACC --> ENC
    ACC --> AUDIT
```

---

## 2. Authentication & MFA Flow

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant SPA as Angular SPA
    participant API as /api/auth/*
    participant DB as PostgreSQL
    participant OTP as TOTP Service

    U->>SPA: Enter username + password
    SPA->>API: POST /api/auth/login/
    API->>DB: Validate credentials
    DB-->>API: User record

    alt Account inactive / locked
        API-->>SPA: 403 Forbidden
        SPA-->>U: Account disabled
    end

    alt MFA enrolled
        API-->>SPA: 200 { mfa_required: true, temp_token }
        SPA-->>U: Show TOTP prompt
        U->>SPA: Enter 6-digit TOTP code
        SPA->>API: POST /api/auth/mfa/verify/ { temp_token, code }
        API->>OTP: Validate TOTP code
        OTP-->>API: Valid / Invalid
    end

    API->>DB: Create JWT (access + refresh)
    API-->>SPA: 200 { access_token, refresh_token }
    SPA->>SPA: Store tokens (memory / httpOnly cookie)

    Note over SPA,API: All subsequent requests: Authorization: Bearer <access_token>

    SPA->>API: POST /api/auth/token/refresh/
    API->>DB: Check refresh token not blacklisted
    API-->>SPA: 200 { access_token }

    U->>SPA: Logout
    SPA->>API: POST /api/auth/logout/
    API->>DB: Blacklist refresh token
    API-->>SPA: 200 OK
```

---

## 3. API Module Structure

```mermaid
graph LR
    subgraph Public["Unauthenticated"]
        L["/api/auth/login/"]
        R["/api/auth/register/"]
        CS["/api/csrf/"]
        MV["/api/auth/mfa/verify/"]
    end

    subgraph Authenticated["JWT Required"]
        subgraph Core["Core"]
            U["/api/users/"]
            P["/api/profile/"]
            PW["/api/auth/password-change/"]
        end
        subgraph Travel["Travel"]
            TR["/api/trf/"]
            BK["/api/bookings/"]
            VI["/api/visa/"]
            AC["/api/accommodation/"]
            TP["/api/transport/"]
            CB["/api/combined/"]
        end
        subgraph Ops["Operations"]
            WF["/api/workflows/"]
            NF["/api/notifications/"]
            RP["/api/reports/"]
            IN["/api/insights/"]
        end
        subgraph Admin["Admin-Only"]
            AP["/api/admin/approvals/"]
            AB["/api/admin/approvals/bulk/"]
            AH["/api/admin/approvals/history/"]
        end
    end

    subgraph AdminPanel["Django Admin"]
        DA["/django-admin/"]
        BU["/django-admin/accounts/databasebackup/"]
    end
```

---

## 4. RBAC Model

```mermaid
graph TD
    subgraph Roles["User Roles (accounts.User)"]
        SU["Superuser<br/>Full system access<br/>DB restore capability"]
        ADM["Admin / Staff<br/>User management<br/>Backup create & download<br/>Audit log read"]
        APR["Approver<br/>Approve/reject requests<br/>View approval history"]
        TRV["Traveller<br/>Submit travel requests<br/>View own records only"]
    end

    subgraph Resources["Protected Resources"]
        MNGMT["Management Commands<br/>backup_db · validate_backup<br/>cleanup_expired_data"]
        AUDIT2["Audit Logs<br/>AdminActionLog (read-only)<br/>DB trigger blocks UPDATE/DELETE"]
        DATA["Sensitive PII<br/>Fernet-encrypted fields<br/>passport · visa · personal data"]
        BKUP["Backup Files<br/>backend/backups/*.dump<br/>Served via admin only"]
    end

    SU --> MNGMT
    SU --> AUDIT2
    SU --> DATA
    SU --> BKUP
    ADM --> AUDIT2
    ADM --> DATA
    ADM --> BKUP
    APR --> DATA
    TRV --> DATA
```

---

## 5. Security Controls Stack

```mermaid
graph TD
    subgraph Network["Network Layer"]
        HTTPS["HTTPS / TLS (server config)"]
        CORS["CORS Whitelist<br/>(corsheaders)"]
        CSP["Content-Security-Policy<br/>(django-csp middleware)"]
        CSRF["CSRF Protection<br/>(Django CSRF middleware)"]
    end

    subgraph Application["Application Layer"]
        JWT2["JWT + Token Blacklist<br/>(simplejwt)"]
        MFA2["TOTP MFA<br/>(django-otp)"]
        SESS["Session Timeout<br/>(SessionTimeoutMiddleware)"]
        INACT["Inactive Account Disable<br/>(90-day inactivity check)"]
        PWD["Password Policy<br/>min 15 chars · min age · complexity"]
        LOCK["Account Lockout<br/>(failed login throttle)"]
    end

    subgraph Data2["Data Layer"]
        ENC2["Field Encryption<br/>(Fernet — PII columns)"]
        AUDIT3["Immutable Audit Log<br/>(PostgreSQL UPDATE trigger)"]
        BACKUP2["Encrypted pg_dump Backups<br/>(pg_dump -Fc format)"]
        RET["Data Retention<br/>(cleanup_expired_data command)"]
    end

    subgraph SDLC["SDLC / DevSecOps"]
        PC["Pre-commit Hooks<br/>black · isort · flake8 · bandit"]
        LS["lint-staged<br/>ESLint · Prettier · Stylelint"]
        CI["GitHub Actions CI<br/>bandit · safety · semgrep"]
        SCAN["Dependency Scanning<br/>(safety check)"]
    end

    HTTPS --> CORS --> CSP --> CSRF
    CSRF --> JWT2 --> MFA2 --> SESS
    SESS --> INACT --> PWD --> LOCK
    LOCK --> ENC2 --> AUDIT3 --> BACKUP2 --> RET
    PC --> LS --> CI --> SCAN
```

---

## 6. Deployment Topology

```mermaid
graph LR
    subgraph Prod["Production Server"]
        NG["Nginx (reverse proxy)<br/>TLS termination<br/>rate limiting"]
        GN["Gunicorn WSGI<br/>Django application"]
        PG2[("PostgreSQL 15")]
        FS["File System<br/>backend/backups/<br/>backend/logs/"]
        CRON["Task Scheduler / Cron<br/>backup_db — daily<br/>cleanup_expired_data — monthly"]
    end

    subgraph Build["Build / CI"]
        GHA["GitHub Actions<br/>lint · security scan · test"]
        ANG["ng build<br/>(Angular SPA)"]
    end

    Browser -->|HTTPS 443| NG
    NG -->|proxy_pass| GN
    GN --> PG2
    GN --> FS
    CRON --> GN
    GHA --> ANG
    ANG -->|deploy| FS
```

---

## 7. Travel Request Data Flow

Traces how a single `TravelRequest` (TRF) moves through the system from creation to a booked outcome. `combined_request` runs the same pattern independently for multi-modal requests (its own `CombinedRequest` model inlines travel/visa/accommodation/transport fields rather than creating child records).

```mermaid
flowchart TD
    C["Traveller creates TRF<br/>trf.TravelRequest (status=Draft)<br/>trf/models.py"]
    S["submit()<br/>trf/views.py — TravelRequestViewSet.submit<br/>status → Pending"]
    WR["WorkflowRouter.start_workflow_for_request<br/>workflows/router.py"]
    WE1["WorkflowEngine.start_workflow<br/>workflows/engine.py<br/>creates WorkflowInstance + first WorkflowStepExecution"]
    N1["NotificationService.create_notification<br/>notifications/services.py<br/>notify_workflow_started"]

    A["Approver acts: approve()/reject()<br/>trf/views.py — TravelRequestViewSet"]
    WE2["WorkflowEngine.process_action<br/>workflows/engine.py<br/>advances/finalizes WorkflowStepExecution<br/>writes WorkflowAuditLog"]
    N2["trigger_configured_notifications<br/>workflows/notifications.py"]
    FIN["Entity status → Approved / Rejected<br/>engine.py"]

    BK["Admin: book_flight action<br/>trf/views.py<br/>creates bookings.FlightBooking(trf=trf)"]

    C --> S --> WR --> WE1 --> N1
    WE1 -.-> A
    A --> WE2 --> N2 --> FIN
    FIN -->|"Approved"| BK

    subgraph Alt["Alternate approval paths (not fully consolidated)"]
        AB["approvals.bulk_approve<br/>approvals/views.py<br/>writes AdminActionLog"]
        TA["WorkflowStepExecutionViewSet.take_action<br/>workflows/views.py"]
    end

    A -.->|"bulk action UI"| AB
    A -.->|"alternate endpoint"| TA
```

**Known gaps / risks surfaced by this trace (not yet resolved in code):**

- **Three divergent "approve a step" code paths** — `WorkflowEngine.process_action`, `approvals.bulk_approve`, and `WorkflowStepExecutionViewSet.take_action` implement overlapping but not identical logic. Which path the frontend calls for a single-item approval vs. a bulk approval is not consistently documented in backend code.
- **`approvals` app has no models** — it is a read-aggregator/bulk-action layer over `workflows.WorkflowInstance` / `WorkflowStepExecution`, not an independent approval store, despite appearing as a peer domain app in §1.
- **Audit logging gap** — `AdminActionLog` is only written from `approvals.bulk_approve`. The single-item `approve`/`reject` actions in `trf/views.py` (the main `WorkflowEngine.process_action` path) do not write an audit log entry.
- **Downstream requests are not auto-created on approval** — bookings, visa, accommodation, and transport records are submitted independently by the traveller/admin after TRF approval; the only system-linked exception is the manual `book_flight` admin action.
- **Dead signal handler** — `trf/signals.py` has a `post_save` receiver keyed off `status == 'Submitted'`, a value the code never actually sets (the real status is `'Pending'`); the signal appears vestigial and the actual trigger is the explicit `WorkflowRouter` call in `submit()`.

---

## 8. Key Dependencies

| Layer | Package | Purpose |
|---|---|---|
| Frontend | Angular 19 | SPA framework |
| Frontend | Angular Material 19 | UI components |
| Frontend | ng-bootstrap 18 | Bootstrap integration |
| Backend | Django 5 | Web framework |
| Backend | djangorestframework | REST API |
| Backend | simplejwt | JWT auth + blacklist |
| Backend | django-otp | TOTP MFA |
| Backend | cryptography (Fernet) | Field-level encryption |
| Backend | corsheaders | CORS |
| Backend | django-csp | Content-Security-Policy |
| Backend | drf-spectacular | OpenAPI schema |
| Backend | whitenoise | Static file serving |
| Backend | psycopg2 | PostgreSQL driver |
| Database | PostgreSQL 15 | Primary datastore |
| DevSecOps | black + isort | Python formatting |
| DevSecOps | flake8 | Python linting |
| DevSecOps | bandit | Python security scan |
| DevSecOps | ESLint + Prettier | TypeScript/HTML quality |
| DevSecOps | pre-commit | Git hook runner |
| DevSecOps | Husky + lint-staged | Frontend git hooks |
