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
            APR["approvals<br/>No models — bulk/read layer over workflows"]
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

This diagram simplifies to 4 abstract role categories for readability — the real system is more granular: `accounts.Role` ↔ `accounts.Permission` via a `RolePermission` join table, 65 named permissions as of 2026-07-23 (`approve_trf`, `manage_bookings`, `view_all_visa`, etc.), checked via helpers in `accounts/utils.py` (`has_permission`, `can_approve`, `can_view_all`, `can_manage`, `is_module_admin`).

**Permission-system audit history (2026-07-23, see `docs/APP_WIDE_GAPS_FIX_ROADMAP.md` Fixes 5-6):**
- ~~5 orphaned `combined_request` permissions~~ — `approve_combined`, `manage_combined_requests`, `process_combined_requests`, `view_admin_combined`, `view_all_combined` had **0 roles assigned**. Fixed (Fix 6, migration `0037`): `approve_combined` now follows the identical pattern used by `approve_trf`/`approve_visa`/`approve_transport`/`approve_accommodation` (`Department Focal`, `Line Manager`, `HOD`, `System Administrator`); the other 4 go to `System Administrator` only, since there's no single existing "combined admin" role the way each other module has one.
- **Still open, by design — ~14 "paper" permissions never enforced anywhere in backend code** — exist in the DB, assigned to roles (some to 11-12 roles), but grepping the entire backend outside migrations/tests finds zero actual `has_permission`/`can_approve`/etc. checks against them. Most notably the whole `create_*` family (`create_trf`, `create_visa`, `create_transport`, `create_accommodation`, `create_combined`) and `manage_own_profile` — none gate their corresponding endpoints, which rely solely on `IsAuthenticated`. Others in this category: `access_debug_endpoints`, `export_data`, `manage_accommodation_bookings`, `manage_document_templates`, `manage_flights`, `manage_transport_requests`, `process_flights`, `process_visa_applications`. **Deliberately not wired into enforcement** — `Registered User` (the self-registration default role) has `create_combined` but not `create_trf`/`create_visa`/`create_transport`/`create_accommodation`, so enforcing those would immediately lock self-registered users out of creating requests. This needs a product decision, not an inferred code fix.

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
        CRON["Task Scheduler / Cron<br/>backup_db — daily<br/>disable_inactive_accounts — weekly<br/>cleanup_expired_data — monthly"]
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

None of the three `CRON` jobs above are scheduled by this repository or the application itself — they're real, tested Django management commands (`backend/accounts/management/commands/`), but installing them on a schedule is an operational step outside what a code commit can do. `backend/scripts/crontab.example` documents the exact schedule shown here so it's versioned and not just tribal knowledge; an operator still has to run `crontab backend/scripts/crontab.example` (with paths adjusted) on the actual deployment host.

---

## 7. Application-Wide Data Flows

This section maps how data moves through **every** domain app, not just the request/approval apps. It's organized as a bird's-eye map first, then a focused drill-down per subsystem. What's already covered elsewhere is not repeated here: authentication/MFA (§2), the API surface (§3), RBAC (§4), the security controls stack (§5), and deployment (§6).

```mermaid
flowchart TD
    subgraph Domain["Domain request apps"]
        direction LR
        TRF2[trf]
        VISA2[visa]
        TRANS2[transport]
        ACC2[accommodation]
        COMB2[combined_request]
    end

    WF["workflows<br/>WorkflowRouter + WorkflowEngine<br/>§7.1"]
    APR["approvals<br/>bulk actions, read-aggregation<br/>§7.1"]
    NOTIF["notifications<br/>NotificationService<br/>§7.3"]
    BOOK["bookings<br/>FlightBooking / HotelBooking<br/>§7.2"]
    ACCTS["accounts<br/>User, Role, AdminActionLog<br/>§7.5 / §7.6"]
    ANALYTICS["reports + insights<br/>read-only aggregation<br/>§7.4"]
    DB[("PostgreSQL")]

    Domain --> WF --> APR --> NOTIF
    TRF2 -.->|"Approved"| BOOK
    Domain --> DB
    WF --> DB
    APR --> DB
    NOTIF --> DB
    BOOK --> DB
    ACCTS --> DB
    ACCTS -.->|"audit entries"| APR
    ANALYTICS -.->|"read-only, never writes"| DB
```

`core/` is not a domain app in its own right — it's a single shared utility (`email_settings_loader.py`) that loads SMTP configuration from the `ApplicationSetting` table into Django settings at runtime, used by the notifications pipeline (§7.3). It has no models, views, or migrations of its own.

### 7.1 Request Submission & Approval

This is the one recurring data flow that spans five separate domain apps: **`trf`, `visa`, `transport`, `accommodation`, and `combined_request` all submit through the identical create → submit → workflow → approve/reject pipeline**, via the same shared `workflows` components (`WorkflowRouter`, `WorkflowEngine`) and the same `approvals`/notification layers. TRF was traced first because it was the app under investigation at the time, but the pattern below is generic and verified against all five apps' `views.py`, not just TRF's.

```mermaid
flowchart TD
    C["Requester creates draft<br/>&lt;app&gt;.models.&lt;Model&gt; (status=Draft)"]
    S["submit()<br/>&lt;app&gt;/views.py — &lt;Model&gt;ViewSet.submit<br/>status: Draft to Pending"]
    WR["WorkflowRouter.start_workflow_for_request<br/>workflows/router.py<br/>entity_type identifies which app's WorkflowTemplate to use"]
    WE1["WorkflowEngine.start_workflow<br/>workflows/engine.py<br/>creates WorkflowInstance + first WorkflowStepExecution"]
    N1["NotificationService.create_notification<br/>notify_workflow_started"]
    LEG["No active WorkflowTemplate?<br/>Fallback: some apps (trf, transport,<br/>combined_request) eagerly create a legacy<br/>&lt;App&gt;ApprovalStep; visa/accommodation just<br/>leave status=Pending and defer to approve()'s<br/>own fallback"]

    A["Approver acts: approve()/reject()<br/>&lt;app&gt;/views.py"]
    AB["Bulk approve UI<br/>approvals.bulk_approve — approvals/views.py"]
    TA["Alternate endpoint<br/>WorkflowStepExecutionViewSet.take_action — workflows/views.py"]
    WE2["WorkflowEngine.process_action<br/>workflows/engine.py<br/>advances/finalizes WorkflowStepExecution<br/>writes WorkflowAuditLog + AdminActionLog"]
    N2["trigger_configured_notifications<br/>workflows/notifications.py"]
    FIN["Entity status: Approved or Rejected"]

    BK["Downstream booking<br/>see §7.2"]

    C --> S --> WR
    WR -->|"template found"| WE1 --> N1
    WR -->|"no template"| LEG
    WE1 -.-> A
    LEG -.-> A
    WE1 -.->|"bulk action UI"| AB
    WE1 -.->|"alternate endpoint"| TA
    A --> WE2
    AB --> WE2
    TA --> WE2
    WE2 --> N2 --> FIN
    FIN -->|"Approved, TRF only"| BK
```

**Per-app reference:**

| App | Model | `entity_type` string | Legacy fallback model |
|---|---|---|---|
| `trf` | `TravelRequest` | `travelrequest` | `TrfApprovalStep` (created eagerly at submit) |
| `visa` | `VisaApplication` | `visaapplication` | `VisaApprovalStep` (created lazily, at approve time) |
| `transport` | `TransportRequest` | `transportrequest` | `TransportApprovalStep` (created eagerly at submit) |
| `accommodation` | `AccommodationRequest` | `accommodation` | none — status just stays `Pending` if no template |
| `combined_request` | `CombinedRequest` | `combinedrequest` | `CombinedRequestApprovalStep` (created eagerly at submit) |

`combined_request` is the multi-modal variant: its `CombinedRequest` model inlines travel/visa/accommodation/transport fields directly (with per-module inclusion flags and per-module status fields) rather than creating child records in the other four apps — but it runs through this exact same `WorkflowRouter`/`WorkflowEngine` pipeline as its own independent workflow.

All three approval entry points (single-item `approve`/`reject`, `bulk_approve`, `take_action`) converge on `WorkflowEngine.process_action` as of 2026-07-22 — see `docs/APPROVAL_WORKFLOW_FIX_ROADMAP.md` for the fix history — and this applies uniformly across all five apps, since `bulk_approve`'s `type_model_map` already covers `trf`, `transport`, `visa`, `accommodation`, and `combined`. `bulk_approve` additionally writes its own bulk-specific `AdminActionLog` entry (`workflow_bulk_approve`/`workflow_bulk_reject`) alongside the per-step entry `process_action` writes, to record that the action came from the bulk UI. `take_action`'s `delegate` branch is the one remaining exception — it's intentionally *not* routed through `WorkflowEngine.delegate_step`, because that method requires the acting user to be the step's current assignee, whereas `take_action` allows a workflow admin to delegate on someone else's behalf; consolidating it would have silently removed that admin capability.

**Resolved (2026-07-22):**

- ~~Three divergent "approve a step" code paths~~ — consolidated onto `WorkflowEngine.process_action`, application-wide (see diagram above).
- ~~Audit logging gap~~ — `WorkflowEngine.process_action` now writes an `AdminActionLog` entry for every approval path, not just bulk.
- ~~Dead signal handler~~ — deleted across all four apps that had it: `trf`, `accommodation`, `transport`, `visa` (`combined_request` never had this dead pattern).
- `approvals` app having no models is now called out directly in its module docstring and in the `APR` node label in §1 — not a bug, just previously under-documented.
- ~~Legacy-fallback authorization gap~~ (found 2026-07-22 while auditing the "no template" branch above) — when no active `WorkflowTemplate` exists for an entity type, all five apps' `approve()`/`reject()` fell back to legacy status-mutation logic gated only by `IsAuthenticated`, with no role/permission check — any authenticated user could approve or reject, regardless of role. `combined_request`'s fallback was the worst: no status-transition check either. Fixed by adding an `accounts.utils.can_approve(user, module)` check (the same permission model backing `WorkflowEngine._is_user_authorized`) to all 10 fallback branches, and wiring `'combined'` → `approve_combined` into `can_approve()`, which existed as a real permission but wasn't in that helper's module map. See `docs/APP_WIDE_GAPS_FIX_ROADMAP.md` Fix 4.

**Still open, by design:**

- **Downstream requests are not auto-created on approval** — bookings, visa, accommodation, and transport records are still submitted independently by the traveller/admin after TRF approval; the only system-linked exception is the manual `book_flight` admin action. This wasn't fixed because it's a product decision (what should get prefilled, who owns the resulting draft, does the traveller review before submit), not a bug — see Fix 4 in `docs/APPROVAL_WORKFLOW_FIX_ROADMAP.md`.

### 7.2 Downstream Bookings (Flight & Hotel)

```mermaid
flowchart TD
    TRF3["TravelRequest<br/>status in Approved / Flight Booked / Hotel Booked / Processing / Ready for Booking"]
    BF["Admin: book_flight action<br/>trf/views.py:985 — admin/book-flight<br/>gated on TRF status<br/>upserts FlightBooking(trf=trf)<br/>force-sets trf.status = 'Flight Booked'"]
    DIRECT["FlightBookingViewSet / HotelBookingViewSet<br/>bookings/views.py<br/>independent create — gated on TRF status<br/>and booking/TRF or booking/accommodation admin"]
    FB[("FlightBooking<br/>PENDING to REQUESTED to CONFIRMED to TICKETED / CANCELLED / REFUNDED / NO_SHOW")]
    HB[("HotelBooking<br/>PENDING to CONFIRMED / CANCELLED")]
    ADMIN3["confirm_booking / issue_ticket / cancel_booking<br/>bookings/models.py instance methods<br/>gated on is_module_admin(user, 'booking'/'trf'/'accommodation')"]

    TRF3 -->|"book_flight"| BF --> FB
    DIRECT --> FB
    DIRECT --> HB
    FB --> ADMIN3
    HB --> ADMIN3
```

Two things worth knowing that aren't obvious from the model layer alone:

- **No `book_hotel` action exists.** `trf/views.py` has a permission check referencing a `book_hotel` action name (line 270), but grep confirms no `@action def book_hotel` was ever implemented — hotel bookings can only be created through `bookings`' own endpoint, with no TRF-approval linkage at all.
- ~~Gap: `bookings`' own create endpoints weren't gated on TRF status or caller identity~~ — **fixed 2026-07-23** (`docs/APP_WIDE_GAPS_FIX_ROADMAP.md` Fix 1 for the status check, Fix 8 for the authorization check). `FlightBookingCreateSerializer.validate_trf`/`HotelBookingCreateSerializer.validate_trf` now check `BOOKABLE_STATUSES`, and `FlightBookingViewSet.perform_create`/`HotelBookingViewSet.perform_create` now reject anyone who isn't a superuser or booking/TRF (flights) or booking/accommodation (hotels) admin — booking is an admin/travel-desk function throughout this app (matching `book_flight`'s own `admin/book-flight` naming), confirmed via the frontend: every real caller of booking creation lives under `features/admin/flights/`, no self-service booking UI exists anywhere.

### 7.3 Notifications Delivery Pipeline

```mermaid
flowchart TD
    CALLER["Caller<br/>WorkflowNotifications.trigger_configured_notifications /<br/>notify_workflow_started / notify_workflow_completed<br/>workflows/notifications.py"]
    NS["NotificationService.create_notification<br/>notifications/services.py:24"]
    PREF{"UserNotificationPreference<br/>in_app_notifications_enabled?"}
    ROW[("UserNotification row<br/>created synchronously, in-request")]
    THREAD["send_email_async<br/>bounded ThreadPoolExecutor (max 8 workers)<br/>+ BoundedSemaphore(200) backpressure<br/>— no Celery anywhere in this codebase"]
    EMAIL["send_email_notification<br/>renders NotificationTemplate (markdown to HTML)<br/>Django send_mail()"]
    KILL["ApplicationSetting: enable_email_notifications<br/>global kill switch"]
    CFG["core.email_settings_loader<br/>loads SMTP config from ApplicationSetting into settings at runtime"]
    API["UserNotificationViewSet<br/>list / mark_as_read / mark_all_as_read / unread_count"]

    CALLER --> NS --> PREF
    PREF -->|"disabled"| STOP1["no row created, returns None"]
    PREF -->|"enabled"| ROW --> API
    NS -->|"send_email=True and allowed by prefs/subscription"| THREAD --> EMAIL
    EMAIL --> KILL
    CFG --> EMAIL
```

Key facts:

- The `UserNotification` DB write is synchronous, inline in the request/response cycle.
- Email is asynchronous, via a **bounded, in-process `ThreadPoolExecutor`** (`notifications/services.py` — `EMAIL_EXECUTOR_MAX_WORKERS = 8`, `EMAIL_QUEUE_MAX_SIZE = 200`), not a task queue — there is no Celery anywhere in this codebase, and this is a deliberate choice, not an oversight (see the "Notification concurrency" note below). Each pool thread closes its own DB connection in a `finally` block afterward, since it falls outside Django's `request_finished` signal.
- Submission is gated by a `threading.BoundedSemaphore(200)`: if 200 email sends are already in flight or queued, a new submission is **rejected immediately** (never blocks the calling HTTP request) and the notification is marked with `email_error = 'Email queue saturated - send dropped'` instead of silently spawning another thread.
- SMTP configuration is DB-backed (`core.email_settings_loader`), not static `settings.py` — editable via admin without an app restart.
- `WorkflowNotifications` (used throughout §7.1) is just a caller into this same `NotificationService` API — there's no separate delivery mechanism for workflow notifications specifically.

**Notification concurrency (fixed 2026-07-23, see `docs/APP_WIDE_GAPS_FIX_ROADMAP.md` Fix 7):** `send_email_async` used to spawn one raw, uncapped `threading.Thread` per email. `NotificationService.notify_role`/`notify_users` loop over recipients and call this per-user — `notify_role('HOD', ...)` with N HODs fired N concurrent unbounded threads all opening SMTP connections at once, with no backpressure and no bound. Replaced with the bounded executor + semaphore described above. This is a lighter-weight fix than adopting a full task queue (Celery/RQ/Django-Q) — deliberately, since this deployment has no broker or worker-process infrastructure today (§6), and adding one is a real infrastructure investment that should be a deliberate choice, not an inferred one. If email volume grows enough that a 200-item bounded queue starts rejecting sends regularly, that's the signal to revisit and adopt a real task queue instead of raising the constants further.

### 7.4 Reports & Insights (Read-Only Analytics)

Both apps are almost entirely **live, read-only aggregation** — no ETL, no scheduled job, no cache or materialized-view layer:

| App | Backing data | Notes |
|---|---|---|
| `reports` | `TravelRequest`, `FlightBooking`/`HotelBooking`, `TransportRequest`, `VisaApplication`, `AccommodationRequest`, `WorkflowInstance`/`WorkflowStepExecution`, `User`/`Department` | No `models.py` at all — every endpoint computes stats on the fly per-request. `ReportExportView` re-runs the same query and serializes to CSV / Excel (`openpyxl`) / PDF (`reportlab`) synchronously in the request. |
| `insights` | Same models as `reports` — nothing else | `dashboard_summary`, `travel_spend_analytics`, `booking_analytics`, etc. are live queries, same pattern as `reports`. `insights/models.py` is now empty (see note below) — this app has no models of its own at all, same as `approvals` (§1). |

`reports`' 5 endpoints previously required only `IsAuthenticated` despite a `generate_admin_reports` permission existing specifically for them — any authenticated user could hit every reports endpoint. Fixed 2026-07-23 (see `docs/APP_WIDE_GAPS_FIX_ROADMAP.md` Fix 5) with a shared permission gate; `insights`' live-query endpoints were not part of that audit and remain `IsAuthenticated`-only.

~~`insights`' `TravelInsight`/`DestinationStat`/`CategorySpend`/`MonthlyTrend`/`TravelAnalytics` models had no population pipeline~~ — **removed entirely 2026-07-22** (see `docs/APP_WIDE_GAPS_FIX_ROADMAP.md` Fix 2), not left as dead schema. Confirmed zero rows in the DB and zero frontend callers before deleting — this wasn't "population pipeline missing," it was genuinely dead code end-to-end (backend models + viewsets + serializers, frontend service methods that were never invoked from any component). Dropped via migration rather than converted to database views or left for a future ETL, since nothing was reading or writing them.

### 7.5 Account Lifecycle

```mermaid
flowchart TD
    REG["Self-registration<br/>POST /register/ — AllowAny, rate-limited 3/hr/IP<br/>accounts/views.py:559"]
    ROLE["Auto-assigned Role = 'Registered User'<br/>is_active=True immediately — no approval step"]
    ADMINC["Admin-created account<br/>POST /users/ — UserViewSet.perform_create<br/>admin sets role/department/is_active directly"]
    LOG1[("AdminActionLog<br/>action_type=user_created")]

    PWRESET["PasswordResetRequestView<br/>token + 1hr expiry on the User row<br/>always generic response — no account enumeration"]
    PWCONFIRM["PasswordResetConfirmView<br/>validates token+expiry, clears token, sets new password"]

    INACTIVE["manage.py disable_inactive_accounts<br/>default 90 days since last login<br/>sets is_active=False, status=Inactive"]
    CLEANUP["manage.py cleanup_expired_data<br/>default 7yr retention<br/>blanks passport/bank fields, deletes long-inactive Users<br/>never touches AdminActionLog (compliance-retained)"]
    DBX[("PostgreSQL")]

    REG --> ROLE --> LOG1
    ADMINC --> LOG1
    PWRESET --> PWCONFIRM
    INACTIVE -.->|"external cron / Task Scheduler — not configured in this repo"| LOG1
    CLEANUP -.->|"external cron / Task Scheduler — not configured in this repo"| DBX
```

Notable: **self-registration has no approval gate at all** — a new account is active immediately, distinguished only by an auto-assigned low-privilege "Registered User" role (users cannot set their own role — it's forced server-side). `disable_inactive_accounts` and `cleanup_expired_data` are both real, tested management commands; their intended schedule is now documented and versioned at `backend/scripts/crontab.example` (§6), though an operator still has to install it on the actual deployment host — no code commit can do that step.

### 7.6 Audit Trail Signals

`accounts/signals.py` (registered in `AccountsConfig.ready()`) is the one remaining signal module in the codebase — it's a pure observability side-channel that writes to `AdminActionLog`, with no functional/business-logic side effects on other apps:

- `pre_save`/`post_save` on `User` → diffs role/active-status changes, logs `user_activated`/`user_deactivated`/`user_role_changed`.
- `post_delete` on `User` → logs `user_deleted` (guarded against double-logging when `UserViewSet.perform_destroy` already logged it explicitly).
- `post_save`/`post_delete` on `Role` → logs `role_created`/`role_deleted`.
- `m2m_changed` on `RolePermission` → logs `role_permissions_modified`.

The four dead signal modules that used to exist in `trf`, `accommodation`, `transport`, and `visa` (§7.1) were removed as part of the approval-workflow fixes — this one is legitimate and still in use.

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
