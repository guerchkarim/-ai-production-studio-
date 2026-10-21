$ErrorActionPreference = 'Stop'
$StudioRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $StudioRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Installez Python 3.12 puis relancez.' }
& python scripts/start_studio.py
if ($LASTEXITCODE) { throw 'Le lancement a echoue. Consultez le message precedent.' }
