# Brain-Computer-Interface v3 — run the API + cockpit from the repo ROOT (Windows PowerShell).
#
#   .\serve.ps1                 # → http://localhost:8000/app/
#   .\serve.ps1 --port 9000     # any bci-serve flag is passed through
#
# No need to cd into backend or activate the venv — this finds the venv for you.

$py = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  Write-Host "venv not found. First-time setup:" -ForegroundColor Yellow
  Write-Host "  cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e `".[dev,plot,api,db]`""
  exit 1
}
& $py -m bciv3.cli serve @args
