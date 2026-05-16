param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 5000,
    [string]$SecretKey = "dev-key",
    [string]$DatabaseUrl = "",
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$env:SECRET_KEY = $SecretKey
if ($DatabaseUrl) {
    $env:DATABASE_URL = $DatabaseUrl
} elseif (-not $env:DATABASE_URL) {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
}

$env:FLASK_APP = "app.py"
$env:FLASK_DEBUG = if ($Debug) { "1" } else { "0" }

Write-Host "Project root: $projectRoot"
Write-Host "Database: " -NoNewline
if ($env:DATABASE_URL) {
    Write-Host $env:DATABASE_URL
} else {
    Write-Host "sqlite:///genealogy_demo.db"
}
Write-Host "Starting server at http://$BindHost`:$Port"

python -m flask run --host $BindHost --port $Port
