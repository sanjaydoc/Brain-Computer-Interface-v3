# Brain-Computer-Interface v3 — run the API + cockpit from the repo ROOT (Windows PowerShell).
#
#   .\serve.ps1                 # → http://localhost:8000/app/
#   .\serve.ps1 --port 9000     # any bci-serve flag is passed through
#
# No need to cd into backend or activate the venv — this finds the venv for you.

# Look for the venv at the repo root (.venv) first, then backend\.venv — either layout works.
$py = $null
foreach ($cand in @('.venv\Scripts\python.exe', 'backend\.venv\Scripts\python.exe')) {
  $p = Join-Path $PSScriptRoot $cand
  if (Test-Path $p) { $py = $p; break }
}
if (-not $py) {
  Write-Host "venv not found. First-time setup (from the repo root):" -ForegroundColor Yellow
  Write-Host "  python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e `"backend[api,db]`""
  exit 1
}
& $py -m bciv3.cli serve @args
