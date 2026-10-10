param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$projectPython = Join-Path $projectRoot "venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $projectPython)) {
    throw "Project virtual environment not found at $projectPython."
}

Set-Location -LiteralPath $projectRoot

if ($Check) {
    & $projectPython manage.py check
    exit $LASTEXITCODE
}

Write-Host "Starting Online Shop at http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor DarkGray
& $projectPython manage.py runserver 127.0.0.1:8000
exit $LASTEXITCODE
