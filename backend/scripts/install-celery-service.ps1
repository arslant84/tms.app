<#
.SYNOPSIS
    One-time, admin-run setup that registers the Celery worker as a real
    Windows service ("TMS-Celery-Worker"), the same way Memurai already
    runs as a service - auto-starts on boot, auto-restarts if it crashes,
    no terminal window to keep open.

.DESCRIPTION
    Root cause this script exists for: this session's dev setup has relied
    on manually starting a Celery worker in a background terminal (or via
    start-dev.ps1's Start-Process call), which dies whenever that terminal/
    session ends and doesn't restart itself after a crash - unlike Memurai,
    which recovers automatically because it's a real Windows service.

    Uses NSSM (Non-Sucking Service Manager, https://nssm.cc) to wrap the
    Celery worker command as a service, since Celery itself doesn't know
    how to register as one. NSSM is not bundled - download nssm.exe once
    from https://nssm.cc/download (get the win64 build) and place it at
    backend\scripts\nssm.exe, or install it via `choco install nssm` if
    Chocolatey is available, before running this script.

    Must be run as Administrator (same requirement as the earlier one-time
    Memurai ACL grant). After this runs once, start-dev.ps1 will find and
    use the service automatically instead of spawning its own process.

.EXAMPLE
    # In an elevated PowerShell:
    powershell -ExecutionPolicy Bypass -File backend\scripts\install-celery-service.ps1
#>

$ErrorActionPreference = 'Stop'

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator (right-click PowerShell -> Run as administrator)."
    exit 1
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$backendDir = Join-Path $repoRoot 'backend'
$venvPython = Join-Path $backendDir 'venv\Scripts\python.exe'
$serviceName = 'TMS-Celery-Worker'

if (-not (Test-Path $venvPython)) {
    Write-Error "Could not find venv Python at $venvPython - is the backend venv set up?"
    exit 1
}

$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    $localNssm = Join-Path $PSScriptRoot 'nssm.exe'
    if (Test-Path $localNssm) {
        $nssm = $localNssm
    }
}
if (-not $nssm) {
    Write-Error @"
nssm.exe not found on PATH or at $PSScriptRoot\nssm.exe

Install it first, either:
  - Chocolatey: choco install nssm
  - Manual: download the win64 build from https://nssm.cc/download
    and place nssm.exe at $PSScriptRoot\nssm.exe

Then re-run this script.
"@
    exit 1
}
$nssmPath = if ($nssm -is [System.Management.Automation.CommandInfo]) { $nssm.Source } else { $nssm }

Write-Host "== Registering $serviceName service ==" -ForegroundColor Cyan

$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service already exists - stopping and removing it first so settings below take effect."
    & $nssmPath stop $serviceName
    & $nssmPath remove $serviceName confirm
}

& $nssmPath install $serviceName $venvPython '-m' 'celery' '-A' 'tms_project' 'worker' '-Q' 'emails,default,pdfs' '--pool=solo' '--loglevel=info'
& $nssmPath set $serviceName AppDirectory $backendDir
& $nssmPath set $serviceName DisplayName 'TMS Celery Worker'
& $nssmPath set $serviceName Description 'Celery worker for the TMS backend (email dispatch, background tasks). Managed by NSSM.'
& $nssmPath set $serviceName Start SERVICE_AUTO_START
& $nssmPath set $serviceName AppExit Default Restart
& $nssmPath set $serviceName AppRestartDelay 5000
& $nssmPath set $serviceName AppStdout (Join-Path $backendDir 'logs\celery-worker.log')
& $nssmPath set $serviceName AppStderr (Join-Path $backendDir 'logs\celery-worker.log')
& $nssmPath set $serviceName AppRotateFiles 1
& $nssmPath set $serviceName AppRotateBytes 10485760

New-Item -ItemType Directory -Force -Path (Join-Path $backendDir 'logs') | Out-Null

# Also grants interactive (non-admin) users start/stop rights, matching the
# ACL grant already applied to Memurai - see start-dev.ps1's own comment.
& sc.exe sdset $serviceName "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWRPWPLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)"

Start-Service $serviceName
Start-Sleep -Seconds 2
$svc = Get-Service -Name $serviceName
Write-Host "Service status: $($svc.Status)" -ForegroundColor $(if ($svc.Status -eq 'Running') { 'Green' } else { 'Yellow' })
Write-Host "Logs: $backendDir\logs\celery-worker.log"
