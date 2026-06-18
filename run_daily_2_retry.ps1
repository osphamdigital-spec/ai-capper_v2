#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Exponential-backoff retry wrapper for run_daily_2.py.

.DESCRIPTION
    Runs the post-game pipeline and retries indefinitely on failure.
    Completed post-mortems are never re-sent — run_postmortem_all.py
    has a skip guard (model_already_done) that detects per-model files
    and skips them automatically on re-run.

    Exit codes from run_daily_2.py:
        0  = all complete
        1  = hard pipeline error (fetch_results failed, no picks files, etc.)
             -- still retries, but prints a warning so you can investigate
        2  = post-mortems incomplete (transient API failure) -- normal retry path

    Backoff schedule (seconds):
        Attempt 1 fails -> wait  90s  (90 * 2^0)
        Attempt 2 fails -> wait 180s  (90 * 2^1)
        Attempt 3 fails -> wait 360s  (90 * 2^2)
        Attempt 4 fails -> wait 720s  (90 * 2^3)
        ...doubles each time, capped at 3600s (1 hour)

.PARAMETER Sport
    Sport code passed to run_daily_2.py (default: mlb).

.PARAMETER Date
    Slate date as YYYY-MM-DD (default: today in US Eastern Time, resolved
    by run_daily_2.py itself).

.PARAMETER MaxWait
    Cap on the sleep interval in seconds (default: 3600). Set lower for
    testing (e.g. -MaxWait 10).

.EXAMPLE
    .\run_daily_2_retry.ps1
    .\run_daily_2_retry.ps1 mlb
    .\run_daily_2_retry.ps1 mlb --Date 2026-06-17
    .\run_daily_2_retry.ps1 mlb --Date 2026-06-17 --MaxWait 600
#>

param(
    [string]$Sport   = "mlb",
    [string]$Date    = "",
    [int]   $MaxWait = 3600
)

# Python 3.12 with openai/anthropic packages installed
$PYTHON = "py"
$PYTHON_ARGS = @("-3.12", "scripts/run_daily_2.py", $Sport)
if ($Date) { $PYTHON_ARGS += @("--date", $Date) }

$attempt  = 0
$waitSecs = 90

while ($true) {
    $attempt++
    $timestamp = Get-Date -Format "HH:mm:ss"

    Write-Host ""
    Write-Host ("=" * 55) -ForegroundColor Cyan
    Write-Host "  RETRY WRAPPER — Attempt $attempt   $timestamp" -ForegroundColor Cyan
    Write-Host ("=" * 55) -ForegroundColor Cyan
    Write-Host ""

    # Run the pipeline — streams all output to the terminal in real time
    & $PYTHON @PYTHON_ARGS
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host ("=" * 55) -ForegroundColor Green
        Write-Host "  ALL COMPLETE on attempt $attempt   $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
        Write-Host ("=" * 55) -ForegroundColor Green
        Write-Host ""
        exit 0
    }

    # Classify the failure so the user can tell if it is a hard error or a transient one
    if ($exitCode -eq 1) {
        Write-Host ""
        Write-Host "  WARNING: exit 1 — hard pipeline error (check output above)." -ForegroundColor Yellow
        Write-Host "  Common causes: fetch_results failed, no picks files found." -ForegroundColor Yellow
        Write-Host "  Retrying anyway — completed post-mortems will be skipped." -ForegroundColor Yellow
    } elseif ($exitCode -eq 2) {
        Write-Host ""
        Write-Host "  INFO: exit 2 — post-mortems incomplete (transient API failure)." -ForegroundColor Yellow
        Write-Host "  Completed models will be skipped on retry." -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "  WARNING: unexpected exit code $exitCode." -ForegroundColor Yellow
    }

    # Enforce cap before sleeping
    $sleepFor = [Math]::Min($waitSecs, $MaxWait)
    $nextWait = $waitSecs * 2  # pre-calculate so we can print it

    Write-Host ""
    Write-Host "  Waiting ${sleepFor}s before attempt $($attempt + 1)..." -ForegroundColor Yellow
    Write-Host "  (next wait after that: $([Math]::Min($nextWait, $MaxWait))s)" -ForegroundColor DarkGray
    Write-Host ""

    Start-Sleep -Seconds $sleepFor

    # Double for next round, capped at MaxWait
    $waitSecs = [Math]::Min($nextWait, $MaxWait)
}
