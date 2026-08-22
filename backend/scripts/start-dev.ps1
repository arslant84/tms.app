<#
.SYNOPSIS
    Starts everything the backend needs for local development in one go:
    Memurai (the Redis-compatible service Celery depends on), a Celery
    worker, and the Django dev server.

.DESCRIPTION
    Root cause this script exists for: Memurai is a Windows service, but
    starting/stopping a service normally requires an elevated (Run as
    Administrator) session. Running this script standalone would hit that
    same permission wall on `Start-Service Memurai` unless the service's
    security descriptor has been updated once to let interactive users
    control it - see the one-time admin command in the PR/commit that
    added this script. After that one-time grant, this script (run as
    your normal user) can start Memurai itself with no prompts.

    Run from anywhere; paths below are relative to this script's own
    location so it doesn't matter what directory you're in when you run it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File backend\scripts\start-dev.ps1
#>

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$backendDir = Join-Path $repoRoot 'backend'
$venvPython = Join-Path $backendDir 'venv\Scripts\python.exe'

Write-Host "== Starting Memurai (Redis) ==" -ForegroundColor Cyan
$memurai = Get-Service -Name Memurai -ErrorAction SilentlyContinue
if (-not $memurai) {
    Write-Warning "Memurai service not found on this machine - skipping. Celery will fail to connect until Redis is available."
} elseif ($memurai.Status -eq 'Running') {
    Write-Host "Memurai already running."
} else {
    Start-Service Memurai
    Start-Sleep -Seconds 1
    $memurai.Refresh()
    if ($memurai.Status -eq 'Running') {
        Write-Host "Memurai started." -ForegroundColor Green
    } else {
        Write-Warning "Memurai did not report Running after Start-Service - check its Windows Event Log if Celery still can't connect."
    }
}

Write-Host "== Starting Celery worker ==" -ForegroundColor Cyan
$celeryService = Get-Service -Name 'TMS-Celery-Worker' -ErrorAction SilentlyContinue
if ($celeryService) {
    if ($celeryService.Status -eq 'Running') {
        Write-Host "TMS-Celery-Worker service already running."
    } else {
        Start-Service 'TMS-Celery-Worker'
        Write-Host "TMS-Celery-Worker service started." -ForegroundColor Green
    }
} else {
    Write-Warning "TMS-Celery-Worker service not installed - falling back to a plain background process (won't survive a reboot or auto-restart on crash). Run backend\scripts\install-celery-service.ps1 as Administrator once to fix this."
    Start-Process -FilePath $venvPython `
        -ArgumentList '-m', 'celery', '-A', 'tms_project', 'worker', '-Q', 'emails,celery', '--pool=solo', '--loglevel=info' `
        -WorkingDirectory $backendDir `
        -WindowStyle Normal
}

Write-Host "== Starting Django dev server ==" -ForegroundColor Cyan
Set-Location $backendDir
& $venvPython manage.py runserver
