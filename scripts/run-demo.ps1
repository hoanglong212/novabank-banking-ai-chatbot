param(
    [ValidateSet('configured', 'mock', 'ollama', 'langgraph')][string]$Mode = 'configured',
    [ValidateRange(1024, 65535)][int]$Port = 8080,
    [switch]$Setup,
    [switch]$SkipBuild,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'
$savedEnvironment = @{}
foreach ($name in @('LLM_PROVIDER', 'FRONTEND_DIST')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
Push-Location $projectRoot
try {
    if ($Setup) {
        if (-not (Test-Path $pythonExe)) {
            & python -m venv backend/.venv
            if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required to create backend/.venv.' }
        }
        & $pythonExe -m pip install -r backend/requirements-dev.txt
        if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
        Push-Location frontend
        try {
            & npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        } finally { Pop-Location }
        if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
    }
    if (-not (Test-Path $pythonExe)) { throw 'Run this script with -Setup first (Python and Node.js must be installed).' }
    if ($Mode -ne 'configured') { $env:LLM_PROVIDER = $Mode }
    if (-not $CheckOnly -and -not $SkipBuild) {
        Push-Location frontend
        try {
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed. Run with -Setup to install dependencies.' }
        } finally { Pop-Location }
    }
    $env:FRONTEND_DIST = Join-Path $projectRoot 'frontend/dist'
    Push-Location backend
    try {
        # Import also validates the frontend build. Uses the same .env/config as the API.
        & $pythonExe -c 'import asyncio,json,sys; from app.main import app; from app.readiness import readiness; r=asyncio.run(readiness()); print(r.body.decode()); sys.exit(0 if r.status_code == 200 else 1)'
        if ($LASTEXITCODE -ne 0) { throw 'Demo preflight failed. Resolve the message above, or use -Mode mock for offline mode.' }
        if (-not $CheckOnly) {
            Write-Host "NovaBank: http://127.0.0.1:$Port (Ctrl+C to stop)"
            & $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port $Port
            if ($LASTEXITCODE -ne 0) { throw "Server exited with an error. If port $Port is occupied, choose -Port 8081." }
        }
    } finally { Pop-Location }
} finally {
    Pop-Location
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
}
