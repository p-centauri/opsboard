# Windows equivalent of the Makefile. Usage: ./make.ps1 <task>   (e.g. ./make.ps1 dev)
param([string]$Task = "help")
$ErrorActionPreference = "Stop"

function Invoke-Checked([string[]]$Cmd) {
    & $Cmd[0] $Cmd[1..($Cmd.Length - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $($Cmd -join ' ')" }
}

function Ensure-Env {
    if (-not (Test-Path .env)) { Copy-Item .env.example .env }
}

$compose = @("docker", "compose")                           # dev (loads the override file)
$prod = @("docker", "compose", "-f", "docker-compose.yml")  # production-like
$api = $compose + @("run", "--rm", "api")
$apiNoDeps = $compose + @("run", "--rm", "--no-deps", "api")
$web = $compose + @("run", "--rm", "--no-deps", "web")
$playwright = $compose + @("--profile", "e2e", "run", "--rm", "--no-deps", "e2e")

switch ($Task) {
    "setup"       { Ensure-Env; Invoke-Checked ($compose + @("build")); Invoke-Checked ($web + @("npm", "ci", "--no-audit", "--no-fund")) }
    "web-install" { Ensure-Env; Invoke-Checked ($web + @("npm", "ci", "--no-audit", "--no-fund")) }
    "dev"         { Ensure-Env; Invoke-Checked ($compose + @("up", "--build")) }
    "run"         { Ensure-Env; Invoke-Checked ($prod + @("up", "--build", "-d")) }
    "stop"        { Invoke-Checked ($compose + @("down")) }
    "logs"        { Invoke-Checked ($compose + @("logs", "-f")) }
    "migrate"     { Ensure-Env; Invoke-Checked ($api + @("alembic", "upgrade", "head")) }
    "seed"        { Ensure-Env; Invoke-Checked ($api + @("alembic", "upgrade", "head")); Invoke-Checked ($api + @("python", "-m", "app.seed")) }
    "reseed"      { Ensure-Env; Invoke-Checked ($api + @("alembic", "upgrade", "head")); Invoke-Checked ($api + @("python", "-m", "app.seed", "--reset")) }
    "test"        { Ensure-Env; Invoke-Checked ($api + @("pytest")); Invoke-Checked ($web + @("npm", "test")) }
    "test-api"    { Ensure-Env; Invoke-Checked ($api + @("pytest")) }
    "test-web"    { Ensure-Env; Invoke-Checked ($web + @("npm", "test")) }
    "e2e"         { Ensure-Env; Invoke-Checked ($prod + @("up", "-d", "--build", "--wait")); Invoke-Checked $playwright }
    "screenshots" { Ensure-Env; Invoke-Checked ($compose + @("--profile", "e2e", "run", "--rm", "--no-deps", "-v", "${PWD}/docs/screenshots:/out", "e2e", "node", "scripts/screenshots.mjs")) }
    "lint"        { Ensure-Env; Invoke-Checked ($apiNoDeps + @("sh", "-c", "ruff check . && ruff format --check . && mypy app tests")); Invoke-Checked ($web + @("npm", "run", "lint")) }
    "format"      { Ensure-Env; Invoke-Checked ($apiNoDeps + @("sh", "-c", "ruff format . && ruff check --fix .")) }
    "gen-api"     { Ensure-Env; Invoke-Checked ($compose + @("run", "--rm", "web", "npm", "run", "gen:api")) }
    "clean"       { Invoke-Checked ($compose + @("down", "-v")) }
    default {
        Write-Host "Tasks: setup web-install dev run stop logs migrate seed reseed test test-api test-web e2e screenshots lint format gen-api clean"
        if ($Task -ne "help") { exit 1 }
    }
}
