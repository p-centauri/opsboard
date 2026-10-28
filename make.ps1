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

$api = @("docker", "compose", "run", "--rm", "api")

switch ($Task) {
    "setup"   { Ensure-Env; Invoke-Checked @("docker", "compose", "build") }
    "dev"     { Ensure-Env; Invoke-Checked @("docker", "compose", "up", "--build") }
    "run"     { Ensure-Env; $env:API_TARGET = "prod"; Invoke-Checked @("docker", "compose", "up", "--build", "-d") }
    "stop"    { Invoke-Checked @("docker", "compose", "down") }
    "logs"    { Invoke-Checked @("docker", "compose", "logs", "-f") }
    "migrate" { Ensure-Env; Invoke-Checked ($api + @("alembic", "upgrade", "head")) }
    "seed"    { Ensure-Env; Invoke-Checked ($api + @("alembic", "upgrade", "head")); Invoke-Checked ($api + @("python", "-m", "app.seed")) }
    "reseed"  { Ensure-Env; Invoke-Checked ($api + @("alembic", "upgrade", "head")); Invoke-Checked ($api + @("python", "-m", "app.seed", "--reset")) }
    "test"    { Ensure-Env; Invoke-Checked ($api + @("pytest")) }
    "lint"    { Ensure-Env; Invoke-Checked ($api + @("sh", "-c", "ruff check . && ruff format --check . && mypy app tests")) }
    "format"  { Ensure-Env; Invoke-Checked ($api + @("sh", "-c", "ruff format . && ruff check --fix .")) }
    "clean"   { Invoke-Checked @("docker", "compose", "down", "-v") }
    default {
        Write-Host "Tasks: setup dev run stop logs migrate seed reseed test lint format clean"
        if ($Task -ne "help") { exit 1 }
    }
}
