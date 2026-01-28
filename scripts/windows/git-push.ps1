# Git Push Script for Windows
# สคริปต์สำหรับ push โค้ดไป GitHub

param(
    [Parameter(Mandatory=$false)]
    [string]$Message = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTest = $false
)

# เปลี่ยนไปที่ root directory ของโปรเจค
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $projectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git Push Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ตรวจสอบว่าเป็น git repository
if (-not (Test-Path ".git")) {
    Write-Host "Error: Not a git repository!" -ForegroundColor Red
    exit 1
}

# ตรวจสอบสถานะ
Write-Host "Checking git status..." -ForegroundColor Yellow
$status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Changes detected:" -ForegroundColor Green
git status --short
Write-Host ""

# ถามว่าต้องการ commit หรือไม่
$response = Read-Host "Do you want to commit and push these changes? (y/n)"
if ($response -ne "y" -and $response -ne "Y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

# ถาม commit message
if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = Read-Host "Enter commit message"
    if ([string]::IsNullOrWhiteSpace($Message)) {
        Write-Host "Error: Commit message cannot be empty!" -ForegroundColor Red
        exit 1
    }
}

# ทดสอบก่อน push (ถ้าไม่ skip)
if (-not $SkipTest) {
    Write-Host ""
    Write-Host "Running tests..." -ForegroundColor Yellow
    
    # ตรวจสอบ Docker
    $dockerRunning = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker is running" -ForegroundColor Green
    } else {
        Write-Host "Warning: Docker might not be running" -ForegroundColor Yellow
    }
}

# Pull ก่อน push
Write-Host ""
Write-Host "Pulling latest changes..." -ForegroundColor Yellow
git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to pull from origin!" -ForegroundColor Red
    Write-Host "Please resolve conflicts manually." -ForegroundColor Red
    exit 1
}

# Add files
Write-Host ""
Write-Host "Adding files..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to add files!" -ForegroundColor Red
    exit 1
}

# Commit
Write-Host ""
Write-Host "Committing changes..." -ForegroundColor Yellow
git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to commit!" -ForegroundColor Red
    exit 1
}

# Push
Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to push to GitHub!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. SSH to Ubuntu Server" -ForegroundColor White
Write-Host "2. Run: cd /path/to/WebAppNMLLM && git pull origin main" -ForegroundColor White
Write-Host "3. Run: docker compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
Write-Host ""
