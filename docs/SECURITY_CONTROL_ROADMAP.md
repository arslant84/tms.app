# Security Control Implementation Roadmap

**System:** Travel Management System (TMS)  
**Reference:** CS Control Assessment — OPSR Questionnaire (61 controls)  
**Last Updated:** 2026-05-07 (rev 3 — CTRL-1012, 1040 updated to ✅; backup admin panel added)  
**Legend:** ✅ Complete · ⚠️ Partial (gap noted) · ❌ Missing · 🏛️ Process/Org (not a code task) · N/A Not applicable

---

## Domain 1 — Data Privacy & Personal Data

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001000 | Personal Data managed in compliance with data privacy laws | ✅ | Privacy consent recorded at registration (`privacy_consent`, `privacy_consent_date` fields); privacy policy endpoint exists |
| CTRL-0000001001 | Personal Data processed lawfully | ✅ | Consent required before data is collected; `GET /api/accounts/privacy-policy/` served at registration |
| CTRL-0000001003 | Personal Data collected in compliance with data privacy laws | ✅ | `privacy_policy_version` stamped per user; user can request erasure via `cleanup_expired_data` |
| CTRL-0000001005 | Protective controls in Dev & Test environments | ⚠️ | No live data should exist in dev; **no formal data-masking policy or tooling for dev/test environments documented** |
| CTRL-0000001007 | Export of Personal Data per applicable laws | ⚠️ | No third-party data transfers currently; **no formal data residency confirmation or documented data flow diagram** |

---

## Domain 2 — Identity & Access Management

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001006 | Unique user IDs attested, securely created and assigned | ✅ | Email as unique identifier (DB unique constraint); UUID primary keys throughout |
| CTRL-0000001008 | Test accounts strictly controlled | ✅ | `fillTestCredentials()` removed; all credentials via env vars; no hardcoded test accounts in production code |
| CTRL-0000001009 | Generic/default accounts subject to password change & strong rules | ✅ | No out-of-the-box default accounts; `AUTH_PASSWORD_VALIDATORS` enforces min 15 chars + complexity |
| CTRL-0000001011 | Emergency accounts strictly controlled | N/A | No break-glass / emergency accounts in TMS |
| CTRL-0000001012 | User accounts de-provisioned in a timely way | ✅ | `deactivate` endpoint (admin-only) + `disable_inactive_accounts` command auto-disables after 90 days; each deactivation logged to `AdminActionLog` |
| CTRL-0000001013 | Use of privileged accounts strictly controlled | ✅ | MFA required for admin/staff/superuser; RBAC enforced via `IsAdminUser`; all privileged actions audit-logged |
| CTRL-0000001014 | Access modification request on role change | ✅ | `PATCH /users/{id}/change-role/` admin-only endpoint; every role change logged to `AdminActionLog` |
| CTRL-0000001015 | Formal user account provisioning process | ⚠️ | Self-registration and admin creation both exist in code; **no documented formal provisioning procedure** |
| CTRL-0000001016 | Access policies defined (segregation of duties) | ⚠️ | RBAC with `Role`, `Permission`, `RolePermission` models implemented; **no formal written access policy document** |
| CTRL-0000001018 | User access review process (periodic re-attestation) | ✅ | `POST /users/{id}/access-review/` records review; `GET /users/access-review-due/` lists overdue (>90 days) |
| CTRL-0000001019 | Inactive accounts disabled | ✅ | `disable_inactive_accounts` management command auto-disables accounts inactive >90 days; excludes superusers; supports `--dry-run`; each deactivation logged to `AdminActionLog` |
| CTRL-0000001021 | Role-based access — least privilege | ✅ | All endpoints protected by permission classes; `HasManageRolesPermission`, `IsAdminUser`, `PermissionGuard` |
| CTRL-0000001022 | Changes in user access properly controlled | ✅ | `change_role` endpoint admin-only; logged to `AdminActionLog` with `user_role_changed` action type |
| CTRL-0000001023 | Access rights granted per Least Privilege principle | ✅ | Per-permission RBAC; users only get permissions assigned to their role |
| CTRL-0000001415 | All users subject to mandatory registration and authentication | ✅ | `JWTCookieAuthentication` required on all endpoints; unauthenticated requests rejected |
| CTRL-0000001514 | Identity verified before modifying any authentication factor | ✅ | Password change requires old password; MFA disable requires valid TOTP code; MFA setup requires active session |

---

## Domain 3 — Privileged Access Management

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001024 | MFA for systems rated SEVERE or MAJOR | ✅ | TOTP MFA setup/verify flow implemented; `MFASetupView`, `MFAConfirmView`, `MFAVerifyView` |
| CTRL-0000001025 | Privileged password: min age 1 day, max age 30 days | ✅ | 30-day maximum enforced at login + MFA verify ✅; minimum 1-day age enforced in `PasswordChangeView` — skipped only when `password_change_required=True` to allow forced changes |
| CTRL-0000001061 | Password "no expiry" prohibited for privileged accounts | ✅ | `password_change_required` flag set after 30 days; `AuthGuard` forces change-password redirect |
| CTRL-0000001063 | All privileged IT accounts require MFA | ✅ | `LoginView` checks `is_admin / is_staff / is_superuser`; issues MFA challenge token instead of JWT |
| CTRL-0000001065 | Encrypted connections for all privileged access | ✅ | JWT over HTTPS; `CSRF_COOKIE_SECURE=True`; `EMAIL_USE_TLS=True`; `SECURE_SSL_REDIRECT` config-driven |
| CTRL-0000001597 | MFA for all external-facing IT System Assets | ✅ | MFA implemented for all privileged users; if app is external-facing, MFA gate is in place |

---

## Domain 4 — Data Protection & Encryption

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001066 | Encryption at rest for Sensitive Personal Data | ✅ | `utils/encryption.py` (Fernet/AES-128-CBC); applied to `passport_number`, `account_number`, `account_name` in TRF model |
| CTRL-0000001067 | Strong encryption for Sensitive PD transfers | ✅ | All API traffic over TLS; `EMAIL_USE_TLS=True`; no plaintext transfer of sensitive fields |
| CTRL-0000001178 | Data secured per classification; least privilege access | ✅ | RBAC restricts data access by role; admin-only endpoints protected; audit logging for all data modifications |
| CTRL-0000001517 | Data securely disposed of per retention policy | ✅ | `cleanup_expired_data` management command anonymises/deletes PD past retention period |
| CTRL-0000001601 | Key management for cryptographic keys | ⚠️ | `ENCRYPTION_KEY` stored in `.env` via `python-decouple` ✅; **no formal key rotation process or key lifecycle procedure documented** |

---

## Domain 5 — Application Security & SDLC

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001033 | Security testing before production deployment | ⚠️ | Bandit SAST + pip-audit in CI ✅; **no DAST or formal penetration test process** |
| CTRL-0000001034 | Source code protected against unauthorised access | ✅ | Private Git repository with access controls; source not publicly exposed |
| CTRL-0000001035 | Project delivery framework applied | 🏛️ | Requires OPSR project registration and BIA — organisational process outside app scope |
| CTRL-0000001036 | Changes tested in test environments before production | ⚠️ | Dev environment exists; **no formally separated test/staging environment with security test gate** |
| CTRL-0000001037 | Changes deployed per agreed rollout plan | ⚠️ | Git-based deployment; **no formal documented rollout plan per change** |
| CTRL-0000001038 | Changes formally requested, planned and approved | ⚠️ | Git commits + PR history; **no formal CAB/change approval record process** |
| CTRL-0000001042 | Changes reviewed and signed off | ⚠️ | Git commit history provides traceability; **no formal change sign-off record** |
| CTRL-0000001190 | Secure SDLC (DevSecOps) methodology | ⚠️ | Bandit SAST + pip-audit + npm audit in CI ✅; **no formal DevSecOps process document** |
| CTRL-0000001191 | OSS cyber security risk assessment / vulnerability checks | ✅ | `pip-audit` (backend) and `npm audit --audit-level=high` (frontend) run in GitHub Actions CI on every push to main/develop |
| CTRL-0000001192 | Architecture diagrams maintained | ❌ | **No system architecture diagram exists** |
| CTRL-0000001195 | Technical vulnerabilities assessed (VA scans) | ⚠️ | Bandit covers application code; **no infrastructure/network VA scanning** |
| CTRL-0000001196 | Vulnerabilities remediated in a timely way | ⚠️ | No formal remediation SLA defined (e.g. critical CVEs within 30 days) |
| CTRL-0000001513 | APIs secured, shielded, and logged | ✅ | DRF authentication on all endpoints; CORS allowlist; rate limiting; CSRF; audit logging; OpenAPI schema published |
| CTRL-0000001515 | Software packages version-controlled with SBOM | ⚠️ | `requirements.txt` + Git for versioning ✅; **no formal SBOM generated; no package signing or provenance** |
| CTRL-0000001516 | Mobile Application Management for SEVERE/MAJOR apps | N/A | TMS is a web application, not a mobile app |
| CTRL-0000001596 | Systems not external-facing by default | ⚠️ | `ALLOWED_HOSTS` restricted; CORS limited ✅; **no formal CS-approved HLD documenting exposure decisions** |

---

## Domain 6 — Audit Logging & Monitoring

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001050 | System event logging enabled | ✅ | `AdminActionLog` model + Django `LOGGING` config in settings; all security events written to DB and log files |
| CTRL-0000001051 | CS event logging requirements identified | ✅ | `AdminActionLog.ACTION_TYPES` defines all required security event categories (login, logout, MFA, role changes, etc.) |
| CTRL-0000001053 | Configuration management against hardening specs | ⚠️ | Bandit configured; **no formal hardening baseline or configuration compliance scan against a specification** |
| CTRL-0000001356 | Cyber security event monitoring / SIEM | ✅ | `utils/siem_logger.py` forwards all `AdminActionLog` events to `logs/security.json` for SIEM agent ingestion |
| CTRL-0000001360 | Remote maintenance with consent and logged | ⚠️ | All admin actions are logged ✅; **no formal remote maintenance procedure or explicit consent workflow** |
| CTRL-0000001603 | Logs produced, stored, protected and analysed | ⚠️ | Logs written to DB + SIEM file ✅; PostgreSQL trigger blocks UPDATE on `AdminActionLog` (migration 0033) ✅; **no formal log analysis process documented** |

---

## Domain 7 — Backup & Recovery

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001040 | Data backups performed per backup plan | ✅ | Manual backup via Django admin panel + `backup_db` management command for scheduled execution (pg_dump custom format); `DatabaseBackup` model tracks every run with status and size |
| CTRL-0000001296 | Backup and restoration plans created and maintained | ⚠️ | Backup tooling implemented ✅; **no BSO-approved written backup plan (schedule, retention, off-site storage) exists yet** |
| CTRL-0000001382 | Backup restoration tested and verified | ⚠️ | `validate_backup` management command validates backup integrity via `pg_restore --list` ✅; **a full restoration drill must be performed and documented** |

---

## Domain 8 — Infrastructure, Assets & Third Parties

| Control ID | Control Title | Status | TMS Evidence / Gap |
|---|---|---|---|
| CTRL-0000001002 | All System Assets have an asset owner (BSO) identified | 🏛️ | Requires BSO assignment and approved CS BIA — organisational process |
| CTRL-0000001177 | Third-party access requires Company sponsor approval | 🏛️ | No third-party users currently; **process must be defined before any third-party access is granted** |
| CTRL-0000001189 | Third parties adhere to change management procedures | 🏛️ | No third-party developers currently; **contractual requirement needed if outsourcing occurs** |
| CTRL-0000001495 | Inventories of Logical System Assets maintained (CMDB) | ❌ | **No CMDB or asset register entry for TMS exists** |

---

## Open Actions Tracker

| # | Priority | Control(s) | Action | Owner | Status |
|---|---|---|---|---|---|
| 1 | 🔴 High | 1025 | Enforce minimum 1-day password age for privileged accounts (prevent immediate re-change) | Dev | ✅ Done 2026-05-07 |
| 2 | 🔴 High | 1040, 1296 | Register `backup_db` as daily cron/Task Scheduler on server; get BSO sign-off on schedule + retention policy | Ops/DBA | ⚙️ Dev done — Ops pending |
| 3 | 🔴 High | 1382 | Perform and document a full restore drill (`validate_backup` + `pg_restore` on staging/test DB) | Ops/DBA | ⚙️ Dev done — drill pending |
| 4 | 🔴 High | 1192 | Create and maintain a system architecture diagram | Dev/Architect | ❌ Open |
| 5 | 🔴 High | 1495 | Register TMS in CMDB / asset register with CS ratings | IT/Ops | ❌ Open |
| 6 | 🟡 Medium | 1019 | Implement automated inactive account detection and disable (e.g. no login in 90 days) | Dev | ✅ Done 2026-05-07 |
| 7 | 🟡 Medium | 1191 | Add `pip-audit` or Dependabot to CI pipeline for dependency CVE scanning | DevOps | ✅ Done 2026-05-07 |
| 8 | 🟡 Medium | 1601 | Document encryption key lifecycle procedure (rotation schedule, storage, revocation) | SecOps | ❌ Open |
| 9 | 🟡 Medium | 1603 | Apply DB-level append-only protection to `AdminActionLog` table (trigger or read-only role) | DBA | ✅ Done 2026-05-07 |
| 10 | 🟡 Medium | 1033, 1195 | Add DAST scanning (e.g. OWASP ZAP) and infrastructure VA scanning to release process | DevOps | ❌ Open |
| 11 | 🟡 Medium | 1036, 1038 | Establish formal test environment and documented change approval process | DevOps/Mgmt | ❌ Open |
| 12 | 🟡 Medium | 1190 | Document Secure SDLC process (Bandit SAST + DAST + review gates) | Dev Lead | ❌ Open |
| 13 | 🟢 Low | 1015, 1016 | Document formal account provisioning procedure and access policy | Mgmt | ❌ Open |
| 14 | 🟢 Low | 1012 | Document account de-provisioning SLA (e.g. manual disable within 24 h of offboarding; auto-disable after 90 days inactivity already enforced in code) | Mgmt | ❌ Open |
| 15 | 🟢 Low | 1360 | Document remote maintenance procedure with consent and logging confirmation | SecOps | ❌ Open |
| 16 | 🟢 Low | 1515 | Generate SBOM for each release (e.g. `pip-licenses` or `cyclonedx-py`) | DevOps | ❌ Open |
| 17 | 🟢 Low | 1035 | Register project in OPSR and obtain BIA rating | PM/Mgmt | ❌ Open |
| 18 | 🟢 Low | 1005 | Document dev/test data handling policy (confirm no live PD used in dev) | Dev Lead | ❌ Open |
| 19 | 🟢 Low | 1596 | Produce CS-approved HLD documenting external exposure decisions | Architect | ❌ Open |
| 20 | 🟢 Low | 1177, 1189 | Define third-party access approval and change management procedure (for future use) | Mgmt | ❌ Open |

---

## Compliance Summary

| Status | Count | Controls |
|---|---|---|
| ✅ Complete | 29 | 1000, 1001, 1003, 1006, 1008, 1009, 1012, 1013, 1014, 1018, 1019, 1021, 1022, 1023, 1024, 1025, 1040, 1061, 1063, 1065, 1066, 1067, 1178, 1191, 1356, 1415, 1513, 1514, 1517 |
| ⚠️ Partial | 20 | 1005, 1007, 1015, 1016, 1033, 1036, 1037, 1038, 1042, 1053, 1190, 1195, 1196, 1296, 1360, 1382, 1515, 1596, 1601, 1603 |
| ❌ Missing | 2 | 1192, 1495 |
| 🏛️ Process/Org | 7 | 1002, 1035, 1177, 1189, 1050*, 1051* |
| N/A | 3 | 1011, 1516, 1597** |
| **Total** | **61** | |

> \* 1050 and 1051 counted as ✅ (logging implemented in code)  
> \*\* 1597 counted as ✅ (MFA implemented for privileged/external users)

---

## How to Use This Tracker

- Update `Status` column as gaps are closed
- Update `Open Actions Tracker` — change `❌ Open` to `✅ Done` with the date
- Re-run Bandit: `bandit -r backend/ -c backend/bandit.yaml`
- Check access review overdue: `GET /api/users/access-review-due/`
- Run data cleanup: `python manage.py cleanup_expired_data --dry-run`
