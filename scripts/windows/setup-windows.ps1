# Windows Setup Script
# สคริปต์สำหรับติดตั้งและตั้งค่าโปรเจคบน Windows PC

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Windows Development Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    Write-Host "✓ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Compose is available
Write-Host "Checking Docker Compose..." -ForegroundColor Yellow
try {
    docker compose version | Out-Null
    Write-Host "✓ Docker Compose is available" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose is not available" -ForegroundColor Red
    exit 1
}

# Setup backend .env file
Write-Host ""
Write-Host "Setting up backend environment..." -ForegroundColor Yellow
$backendEnvPath = "backend\.env"
$backendEnvExample = "backend\.env.example"

if (-not (Test-Path $backendEnvPath)) {
    if (Test-Path $backendEnvExample) {
        Copy-Item $backendEnvExample $backendEnvPath
        Write-Host "✓ Created backend\.env from .env.example" -ForegroundColor Green
        Write-Host "⚠ Please review and update backend\.env if needed" -ForegroundColor Yellow
    } else {
        Write-Host "⚠ .env.example not found, skipping..." -ForegroundColor Yellow
    }
} else {
    Write-Host "✓ backend\.env already exists" -ForegroundColor Green
}

# Create required directories
Write-Host ""
Write-Host "Creating required directories..." -ForegroundColor Yellow
$dirs = @("storage", "mongo-data", "mongo-backup", "backups")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "✓ Created $dir" -ForegroundColor Green
    } else {
        Write-Host "✓ $dir already exists" -ForegroundColor Green
    }
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Review backend\.env and update if needed" -ForegroundColor White
Write-Host "2. Start development:" -ForegroundColor White
Write-Host "   docker compose up -d" -ForegroundColor Blue
Write-Host ""
Write-Host "3. Access application:" -ForegroundColor White
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Blue
Write-Host "   Backend API: http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "4. Default login:" -ForegroundColor White
Write-Host "   Username: admin" -ForegroundColor Blue
Write-Host "   Password: admin123" -ForegroundColor Blue
Write-Host ""
