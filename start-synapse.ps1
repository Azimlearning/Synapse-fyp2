# Starts the whole Synapse demo on this machine, each server in its own window:
#   GraphRAG API          http://localhost:8000   (this repo, api/)
#   Synapse web app       http://localhost:3000   (this repo, web/)  <- open this one
#   Simulation API        http://localhost:8001   (generative UI engine, genui/ in this repo)
#   Simulation web        http://localhost:3001   (shown inside the app under "Simulations")
#
# Usage:  powershell -ExecutionPolicy Bypass -File .\start-synapse.ps1            (builds once, then reuses the builds)
#         powershell -ExecutionPolicy Bypass -File .\start-synapse.ps1 -Rebuild   (after a code change)
#         ... -SimMode live                                                        (simulations on free models only: a new question can take many minutes)
#         ... -SimMode live -SimCapUsd 3                                           (the viva setting: Claude via OpenRouter credits for the slow steps, capped
#                                                                                   at $3 this month in genui's ledger; stored questions still cost nothing)
# Stop:   powershell -ExecutionPolicy Bypass -File .\stop-synapse.ps1   (or close the four windows)
#
# Both web apps run as production builds: no dev overlay, no reload when a file changes, faster pages.
# The GraphRAG side reads this repo's .env (ARCANA_LLM_MODE live = real model calls, booked against LLM_MONTHLY_CAP_USD).
# The simulation side runs on its verified library by default. With -SimMode live it runs as Synapse v5 (V5-D22): free OpenRouter
# models write the note, the plan and the Free-lane page, the browser verifier checks them, and the library answers repeated questions.
# With no -SimCapUsd the paid Anthropic fallback is off, so it cannot spend anything. Its OpenRouter key comes from this repo's .env (genui/.env's when this
# one has none); it is passed through the process environment, never on a command line.

param(
  [string]$SimRepo = "",
  # fake (default for the viva): verified library simulations, always available, no model call. live: free OpenRouter models build new
  # ones too (2026-11-23 evening: the free models were rate limited, HTTP 429, so live was not dependable; see the notes above).
  [ValidateSet("fake", "live")][string]$SimMode = "fake",
  [string]$SimCapUsd = "",
  # The corpus the GraphRAG side answers from: the 16 research papers with their notes (claims, vault) built.
  [string]$DataDir = "data/viva-demo",
  [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }
if (-not $SimRepo) { $SimRepo = Join-Path $here "genui" }

if (-not (Test-Path $SimRepo)) { throw "Simulation repo not found at $SimRepo. Pass -SimRepo <path>." }
function Read-EnvValue([string]$file, [string]$name) {
  if (-not (Test-Path $file)) { return "" }
  foreach ($line in Get-Content $file) {
    if ($line -match "^\s*$name\s*=\s*(.+?)\s*$") { return $Matches[1].Trim('"').Trim("'") }
  }
  return ""
}
if ($SimMode -eq "live") {
  # This repo's key first: it is the one checked live (2026-11-23); genui/.env's was refused by OpenRouter (genui STATUS, HTTP 401).
  $orKey = Read-EnvValue (Join-Path $here ".env") "OPENROUTER_API_KEY"
  if (-not $orKey.StartsWith("sk-or-")) { $orKey = Read-EnvValue (Join-Path $SimRepo ".env") "OPENROUTER_API_KEY" }
  if (-not $orKey.StartsWith("sk-or-")) { throw "No OpenRouter key (sk-or-...) in genui/.env or .env: live simulations need one. Or pass -SimMode fake." }
  # The Claude route needs the OpenRouter key above; the Anthropic keys in both .env files were refused (HTTP 401, 2026-11-24).
  $env:OPENROUTER_API_KEY = $orKey   # inherited by the simulation API window; never printed or put on a command line
  # The free models that answer (NVIDIA's) are hosted where prompts may be kept for training: with "deny" OpenRouter has only rate-limited
  # models left and every request gets HTTP 429 (found 2026-11-24). The prompts are general science questions, never personal data.
  $env:OPENROUTER_ALLOW_TRAINING_PROVIDERS = "true"
  if ($SimCapUsd) {
    # genui V5-D26: Claude through the OpenRouter credits (genui/api/llm/chains-paid.json), behind the ledger and this cap. The slow steps go to
    # Claude first (a Plan took 193 s on the best free model, 14 s on Claude Haiku); routing and the short explanation stay free first.
    $env:ALLOW_PAID_FALLBACK = "true"
    $env:OPENROUTER_PAID_CHAINS_PATH = (Join-Path $SimRepo "api\llm\chains-paid.json")
    $env:PAID_FIRST_PURPOSES = "plan,free,blueprint,build_script,fill,patch,wording,wording_free"
  } else {
    $env:ALLOW_PAID_FALLBACK = "false"
  }
  Remove-Variable orKey
}

foreach ($port in 8000, 3000, 8001, 3001) {
  if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $port is already in use. Run stop-synapse.ps1 first."
  }
}

# --- Builds (only when missing, or with -Rebuild) ---
$webBuild = Join-Path $here "web\.next\BUILD_ID"
if ($Rebuild -or -not (Test-Path $webBuild)) {
  Write-Host "Building the Synapse web app..."
  Push-Location $here
  try { pnpm --filter web build; if ($LASTEXITCODE -ne 0) { throw "web build failed" } } finally { Pop-Location }
}

# The simulation web app is built into its own folder (.next-embed) pointed at port 8001, beside its default build. It uses
# webpack: Next 16.4's Turbopack cannot load its Google font on this machine. Next rewrites two source files while building;
# they are put back afterwards so the source stays as written.
$simBuild = Join-Path $SimRepo "web\.next-embed\BUILD_ID"
if ($Rebuild -or -not (Test-Path $simBuild)) {
  Write-Host "Building the simulation web app..."
  $keep = @{}
  foreach ($f in "web\tsconfig.json", "web\next-env.d.ts") { $p = Join-Path $SimRepo $f; if (Test-Path $p) { $keep[$p] = [IO.File]::ReadAllBytes($p) } }
  Push-Location $SimRepo
  try {
    $env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8001"; $env:NEXT_DIST_DIR = ".next-embed"
    pnpm --filter web exec next build --webpack
    # Next 16.4.2 stops the first build once to show a security-upgrade notice; the same command then runs. Retry once.
    if ($LASTEXITCODE -ne 0) { Write-Host "Retrying the build once..."; pnpm --filter web exec next build --webpack }
    if ($LASTEXITCODE -ne 0) { throw "simulation web build failed" }
  } finally {
    foreach ($p in $keep.Keys) { [IO.File]::WriteAllBytes($p, $keep[$p]) }
    Remove-Item Env:NEXT_PUBLIC_API_BASE_URL, Env:NEXT_DIST_DIR -ErrorAction SilentlyContinue
    Pop-Location
  }
}

function Start-Server([string]$title, [string]$dir, [string]$cmd) {
  $full = "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location -LiteralPath '$dir'; $cmd"
  Start-Process $shell -ArgumentList "-NoExit", "-Command", $full | Out-Null
  Write-Host "started  $title"
}

$ledger = (Join-Path $SimRepo "data\ledger.db").Replace("\", "/")
$simEnv = "`$env:SYNAPSE_LLM_MODE='$SimMode'; `$env:PUBLIC_ORIGIN='http://localhost:3001'; `$env:NEXT_PUBLIC_API_BASE_URL='http://localhost:8001'; `$env:LEDGER_PATH='$ledger';"
if ($SimMode -eq "live" -and $SimCapUsd) { $simEnv += " `$env:LLM_MONTHLY_CAP_USD='$SimCapUsd'; `$env:LLM_TOTAL_CAP_USD='$SimCapUsd';" }

if (-not (Test-Path (Join-Path $here $DataDir))) { throw "Corpus folder $DataDir not found. Pass -DataDir <folder>." }
Start-Server "Synapse GraphRAG API :8000" $here "`$env:ARCANA_DATA_DIR='$DataDir'; uv run uvicorn api.main:app --port 8000"
Start-Server "Synapse web :3000" $here "pnpm --filter web start"
Start-Server "Synapse simulation API :8001" $SimRepo "$simEnv uv run uvicorn api.main:app --port 8001"
Start-Server "Synapse simulation web :3001" $SimRepo "`$env:NEXT_DIST_DIR='.next-embed'; pnpm --filter web exec next start --port 3001"

Write-Host ""
Write-Host "Waiting for the servers (the APIs take about 30 s)..."
$targets = [ordered]@{
  "GraphRAG API"   = "http://localhost:8000/health"
  "Simulation API" = "http://localhost:8001/health"
  "GraphRAG notes" = "http://localhost:8000/vault/notes"
  "Web app"        = "http://localhost:3000/"
  "Simulation web" = "http://localhost:3001/"
}
foreach ($name in $targets.Keys) {
  $deadline = (Get-Date).AddMinutes(3)
  $ok = $false
  while (-not $ok -and (Get-Date) -lt $deadline) {
    try { Invoke-WebRequest $targets[$name] -UseBasicParsing -TimeoutSec 30 | Out-Null; $ok = $true } catch { Start-Sleep -Seconds 2 }
  }
  Write-Host ("{0,-15} {1}" -f $name, $(if ($ok) { "ready" } else { "NOT READY, check its window" }))
}
Write-Host ""
Write-Host "Open http://localhost:3000  (Chat, Notes, Labs, Simulations)"
Start-Process "http://localhost:3000"
