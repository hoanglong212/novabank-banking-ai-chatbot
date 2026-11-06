$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime = Join-Path $projectRoot '.local/week7-deploy'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$env:ENV = 'demo'
$env:LLM_PROVIDER = 'ollama'
$env:OLLAMA_MODEL = 'qwen2.5:7b'
$env:GUARD_MODEL = 'qwen2.5:7b'
$env:OLLAMA_URL = 'http://127.0.0.1:11435'
$env:GATEWAY_MODE = 'local'

# Reuse the dedicated local model server; never change the user's port 11434.
try { $tags = Invoke-RestMethod "$env:OLLAMA_URL/api/tags" -TimeoutSec 3 }
catch {
    $env:OLLAMA_HOST = '127.0.0.1:11435'
    $env:OLLAMA_NOPRUNE = 'true'
    if ($env:NOVABANK_OLLAMA_MODELS) {
        $env:OLLAMA_MODELS = $env:NOVABANK_OLLAMA_MODELS
    } elseif (Test-Path -LiteralPath 'D:\Ollama\models') {
        $env:OLLAMA_MODELS = 'D:\Ollama\models'
    }
    $ollama = (Get-Command ollama -ErrorAction Stop).Source
    $process = Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtime 'ollama.log') `
        -RedirectStandardError (Join-Path $runtime 'ollama-error.log')
    $process.Id | Set-Content -LiteralPath (Join-Path $runtime 'ollama.pid')
    $tags = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try { $tags = Invoke-RestMethod "$env:OLLAMA_URL/api/tags" -TimeoutSec 2; break } catch {}
    }
    if (-not $tags) { throw 'Ollama did not start. Inspect .local/week7-deploy/ollama-error.log.' }
}
if ($tags.models.name -notcontains $env:OLLAMA_MODEL) {
    throw 'qwen2.5:7b is unavailable in this model directory. No automatic download was performed.'
}
Push-Location $projectRoot
try {
    & ./backend/.venv/Scripts/python.exe scripts/serve.py --port 8081 --agent-port 8094 --db .local/week7-deploy/novabank-v2.sqlite3
    if ($LASTEXITCODE -ne 0) { throw "Local application exited with code $LASTEXITCODE" }
} finally { Pop-Location }
