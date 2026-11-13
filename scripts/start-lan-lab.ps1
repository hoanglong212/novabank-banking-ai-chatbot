# Lab only: serve NovaBank (UI + API on one port) on 0.0.0.0 with ENV=demo, so a VM running Caido/Burp can reach it
# over the LAN IP. ENV=demo enables the simulated inbox and gateway measurement sessions. Never use on an untrusted
# network: demo credentials are public. Usage:
#   .\scripts\start-lan-lab.ps1                       # Qwen on the dedicated local Ollama (127.0.0.1:11435)
#   .\scripts\start-lan-lab.ps1 -Mode mock            # no model needed
#   .\scripts\start-lan-lab.ps1 -Proxy http://<vm-ip>:8080   # also send bank->agent->model traffic through Caido
param(
    [ValidateSet('ollama', 'mock')][string]$Mode = 'ollama',
    [ValidateRange(1024, 65535)][int]$Port = 8080,
    [string]$OllamaUrl = 'http://127.0.0.1:11435',
    [string]$Proxy = '',
    [switch]$SkipBuild,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$env:ENV = 'demo'
if ($Mode -eq 'ollama') {
    $env:OLLAMA_URL = $OllamaUrl
    $env:OLLAMA_MODEL = 'qwen2.5:7b'
    $env:GUARD_MODEL = 'qwen2.5:7b'
}
$addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object IPAddress
Write-Host "LAN lab (ENV=demo). From the VM open: $((@($addresses) | ForEach-Object { "http://${_}:$Port" }) -join '  ')"
Write-Host "If the VM cannot connect, allow inbound TCP $Port on this host's firewall for the lab network only."
$launch = @{ Mode = $Mode; Port = $Port; Lan = $true }
if ($Proxy) { $launch.Proxy = $Proxy }
if ($SkipBuild) { $launch.SkipBuild = $true }
if ($CheckOnly) { $launch.CheckOnly = $true }
& (Join-Path $PSScriptRoot 'run-demo.ps1') @launch
