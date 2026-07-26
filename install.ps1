# This is just some Claude garbage, but it gets the job done I guess.
# Heck windows.

<#
.SYNOPSIS
    Installs the "giti" PowerShell function so git-informed can be run from any directory.
.DESCRIPTION
    Place this script in the ROOT of the git-informed repo (next to src\, .venv\, and
    start.ps1) and run it from there. It resolves its own location via $PSScriptRoot, so
    the absolute path it bakes in is correct regardless of what your current directory
    happens to be when you invoke it.

    It adds a "giti" function to your PowerShell profile ($PROFILE) that calls this repo's
    start.ps1 by absolute path, forwarding through whatever arguments you pass (e.g.
    `giti ..`). start.ps1 is responsible for knowing which Python and entrypoint to use;
    this script doesn't duplicate that logic.

    If the venv doesn't exist yet, this script creates it (python -m venv .venv) and
    installs the package in editable mode with dev extras (pip install -e .[dev]).

    Safe to re-run: it replaces its own previously-installed block instead of duplicating it.
#>

$ErrorActionPreference = "Stop"

# --- Resolve the absolute path of this repo from the script's own location ---
$repoRoot = $PSScriptRoot
if (-not $repoRoot) {
    # Fallback for edge cases where $PSScriptRoot is blank (e.g. pasted into a console)
    $repoRoot = (Get-Location).Path
    Write-Warning "Could not resolve script location via `$PSScriptRoot; falling back to current directory ($repoRoot). Run install.ps1 directly (not pasted) from the repo root for a reliable path."
}

$venvDir   = Join-Path $repoRoot ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$pipExe    = Join-Path $venvDir "Scripts\pip.exe"
$startPs1  = Join-Path $repoRoot "start.ps1"

Write-Host "Repo root:  $repoRoot"
Write-Host "start.ps1:  $startPs1"
Write-Host ""

# --- Create the venv and install the package if it's missing ---
if (-not (Test-Path $pythonExe)) {
    Write-Host "Virtual environment not found. Creating it now..."

    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $systemPython) {
        $systemPython = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $systemPython) {
        Write-Warning "Could not find a 'python' or 'python3' executable on PATH. Install Python first, then re-run this script."
    } else {
        & $systemPython.Source -m venv $venvDir

        if (Test-Path $pipExe) {
            Write-Host "Installing package in editable mode with dev extras (pip install -e .[dev])..."
            Push-Location $repoRoot
            try {
                & $pipExe install -e ".[dev]"
            } finally {
                Pop-Location
            }
        } else {
            Write-Warning "venv was created but '$pipExe' still wasn't found; skipping package install."
        }
    }
    Write-Host ""
}

if (-not (Test-Path $pythonExe)) {
    Write-Warning "Could not find '$pythonExe'. Make sure the venv is created (e.g. 'python -m venv .venv' + install requirements) before using 'giti'."
}
if (-not (Test-Path $startPs1)) {
    Write-Warning "Could not find '$startPs1'. Is install.ps1 sitting at the root of git-informed, alongside start.ps1?"
}

# --- Build the function block ---
$marker = "giti-function"
$functionBlock = @"
# >>> $marker >>>
function giti {
    & "$startPs1" @args
}
# <<< $marker <
"@

# --- Make sure the profile file exists ---
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "Created new PowerShell profile at $PROFILE"
}

$existingContent = Get-Content -Path $PROFILE -Raw -ErrorAction SilentlyContinue
if ($null -eq $existingContent) { $existingContent = "" }

# --- Strip any previously-installed block (idempotent re-run), then append fresh block ---
$pattern = "(?ms)\r?\n?# >>> $marker >>>.*?# <<< $marker <<<\r?\n?"
$cleaned = [regex]::Replace($existingContent, $pattern, "")
$newContent = $cleaned.TrimEnd() + "`r`n`r`n$functionBlock`r`n"

Set-Content -Path $PROFILE -Value $newContent

Write-Host "Installed 'giti' function into $PROFILE"
Write-Host ""
Write-Host "Restart your terminal, or run:  . `$PROFILE"
Write-Host "Then use it from anywhere, e.g.:  giti .."
