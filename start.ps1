# Quick Start Script
# สคริปต์สำหรับเริ่มใช้งานระบบทันที

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WebAppNMLLM - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# เปลี่ยนไปที่ root directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# ตรวจสอบ Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop" -ForegroundColor White
    Write-Host "2. Wait for Docker to start" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "✓ Docker is running" -ForegroundColor Green

# ตรวจสอบ .env
Write-Host ""
Write-Host "Checking configuration..." -ForegroundColor Yellow
if (-not (Test-Path "backend\.env")) {
    Write-Host "⚠️  backend\.env not found!" -ForegroundColor Yellow
    Write-Host "Creating from template..." -ForegroundColor Yellow
    
    if (Test-Path "backend\.env.example") {
        Copy-Item "backend\.env.example" "backend\.env" -Force
        
        # สร้าง JWT_SECRET
        $jwtSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
        (Get-Content "backend\.env") -replace 'JWT_SECRET=your-very-secure-random-secret-key-minimum-32-characters', "JWT_SECRET=$jwtSecret" | Set-Content "backend\.env"
        
        Write-Host "✓ Created backend\.env with secure JWT_SECRET" -ForegroundColor Green
    } else {
        Write-Host "❌ backend\.env.example not found!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Configuration file exists" -ForegroundColor Green
}

# สร้าง storage directory
if (-not (Test-Path "storage")) {
    New-Item -ItemType Directory -Force -Path "storage" | Out-Null
    Write-Host "✓ Created storage directory" -ForegroundColor Green
}

# เริ่ม services
Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start services!" -ForegroundColor Red
    exit 1
}

# รอให้ services เริ่มทำงาน
Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# ตรวจสอบสถานะ
Write-Host ""
Write-Host "Service status:" -ForegroundColor Cyan
docker compose ps

# ตรวจสอบ health
Write-Host ""
Write-Host "Checking service health..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$backendHealthy = $false
$frontendHealthy = $false

# ตรวจสอบ backend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $backendHealthy = $true
        Write-Host "✓ Backend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Backend is starting... (may take a few more seconds)" -ForegroundColor Yellow
}

# ตรวจสอบ frontend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $frontendHealthy = $true
        Write-Host "✓ Frontend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Frontend is starting... (may take a few more seconds)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  System is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "🌐 Access URLs:" -ForegroundColor Cyan
Write-Host "  Frontend:    http://localhost:5173" -ForegroundColor White
Write-Host "  Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  MongoDB:     localhost:27017" -ForegroundColor White
Write-Host ""

Write-Host "🔐 Login Credentials:" -ForegroundColor Cyan
Write-Host "  Username: admin" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
Write-Host "  ⚠️  Change password after first login!" -ForegroundColor Yellow
Write-Host ""

Write-Host "📝 Useful Commands:" -ForegroundColor Cyan
Write-Host "  View logs:    docker compose logs -f" -ForegroundColor White
Write-Host "  Stop:         docker compose down" -ForegroundColor White
Write-Host "  Restart:      docker compose restart" -ForegroundColor White
Write-Host ""

if (-not $backendHealthy -or -not $frontendHealthy) {
    Write-Host "💡 Tip: Services may need a few more seconds to fully start." -ForegroundColor Yellow
    Write-Host "   Run 'docker compose logs -f' to monitor startup progress." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Happy Coding! 🚀" -ForegroundColor Green
Write-Host ""
