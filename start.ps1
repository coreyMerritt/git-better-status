$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
  $scriptDir = (Get-Location).Path
}

$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$mainPy    = Join-Path $scriptDir "src\main.py"

& $pythonExe $mainPy @args
