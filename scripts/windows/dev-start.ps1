# Development Start Script for Windows
# สคริปต์สำหรับเริ่ม development server

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $projectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Development Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ตรวจสอบว่า Docker ทำงาน
Write-Host "Checking Docker..." -ForegroundColor Yellow
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "Docker is running" -ForegroundColor Green

# ตรวจสอบว่า .env มีอยู่
if (-not (Test-Path "backend\.env")) {
    Write-Host ""
    Write-Host "Warning: backend\.env not found!" -ForegroundColor Yellow
    Write-Host "Please create backend\.env file before starting." -ForegroundColor Yellow
    $response = Read-Host "Continue anyway? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

# Pull latest changes (optional)
Write-Host ""
$response = Read-Host "Pull latest changes from GitHub? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "Pulling latest changes..." -ForegroundColor Yellow
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Failed to pull from GitHub" -ForegroundColor Yellow
    }
}

# Start services
Write-Host ""
Write-Host "Starting Docker services..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to start services!" -ForegroundColor Red
    exit 1
}

# รอให้ services เริ่มทำงาน
Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# ตรวจสอบสถานะ
Write-Host ""
Write-Host "Service status:" -ForegroundColor Cyan
docker compose ps

# ตรวจสอบ health
Write-Host ""
Write-Host "Checking service health..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# ตรวจสอบ backend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Backend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Backend health check failed" -ForegroundColor Red
}

# ตรวจสอบ frontend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Frontend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Frontend health check failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Development environment is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  MongoDB: localhost:27017" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  View logs: docker compose logs -f" -ForegroundColor White
Write-Host "  Stop services: docker compose down" -ForegroundColor White
Write-Host "  Restart: docker compose restart" -ForegroundColor White
Write-Host ""

# ถามว่าต้องการดู logs หรือไม่
$response = Read-Host "View logs? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    docker compose logs -f
}
