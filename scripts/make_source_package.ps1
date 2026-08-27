# Builds ID-SHIELD_Source.zip - the complete development repository
# (frontend source, tests, configs, docs) ready to send to teammates.
#
#   powershell -ExecutionPolicy Bypass -File scripts\make_source_package.ps1
#
# Excludes: node_modules, .venv, runtime data, caches, previous zips.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Stage = Join-Path $env:TEMP ("idshield_src_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$Dest = Join-Path $Root "ID-SHIELD_Source.zip"

Write-Host "=== Building source package ===" -ForegroundColor Cyan

New-Item -ItemType Directory -Path $Stage | Out-Null

$dirs = @(
    @{ src = "backend";        dst = "backend" },
    @{ src = "frontend\src";   dst = "frontend\src" },
    @{ src = "frontend\public"; dst = "frontend\public" },
    @{ src = "frontend\dist";  dst = "frontend\dist" },
    @{ src = "docs";           dst = "docs" },
    @{ src = "scripts";        dst = "scripts" }
)
$files = @(
    "README.md", "README-OFFLINE.txt", ".env.example", ".gitignore",
    "Dockerfile", ".dockerignore", "docker-compose.yml",
    "start_idshield.bat", "run_dev.ps1", "run_dev.sh",
    "frontend\package.json", "frontend\package-lock.json",
    "frontend\vite.config.ts", "frontend\tsconfig.json",
    "frontend\tailwind.config.js", "frontend\postcss.config.js",
    "frontend\index.html"
)

foreach ($d in $dirs) {
    $src = Join-Path $Root $d.src
    if (-not (Test-Path $src)) { continue }
    $dst = Join-Path $Stage $d.dst
    robocopy $src $dst /E /XD __pycache__ .pytest_cache node_modules data `
        /XF "*.pyc" .DS_Store /NFL /NDL /NJH /NJS | Out-Null
}
foreach ($f in $files) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        $dst = Join-Path $Stage $f
        New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null
        Copy-Item $src $dst
    }
}

if (Test-Path $Dest) { Remove-Item $Dest }
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Dest
Remove-Item $Stage -Recurse -Force

$sizeMb = [math]::Round((Get-Item $Dest).Length / 1MB, 1)
Write-Host ""
Write-Host "Source package ready: $Dest ($sizeMb MB)" -ForegroundColor Green
