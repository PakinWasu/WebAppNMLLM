# Update and Push Script for Windows
# Pull latest changes, commit, and push to GitHub

param(
    [Parameter(Mandatory=$true)]
    [string]$CommitMessage
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Update and Push to GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is available
try {
    git --version | Out-Null
} catch {
    Write-Host "✗ Git is not installed" -ForegroundColor Red
    exit 1
}

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "✗ Not a git repository" -ForegroundColor Red
    exit 1
}

# Step 1: Pull latest changes
Write-Host "Step 1: Pulling latest changes..." -ForegroundColor Yellow
try {
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Warning: Pull may have conflicts" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Pulled latest changes" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Failed to pull" -ForegroundColor Red
    exit 1
}

# Step 2: Check status
Write-Host ""
Write-Host "Step 2: Checking status..." -ForegroundColor Yellow
git status

# Step 3: Add changes
Write-Host ""
Write-Host "Step 3: Adding changes..." -ForegroundColor Yellow
git add .
Write-Host "✓ Changes added" -ForegroundColor Green

# Step 4: Commit
Write-Host ""
Write-Host "Step 4: Committing..." -ForegroundColor Yellow
git commit -m $CommitMessage
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Committed: $CommitMessage" -ForegroundColor Green
} else {
    Write-Host "⚠ No changes to commit" -ForegroundColor Yellow
}

# Step 5: Push
Write-Host ""
Write-Host "Step 5: Pushing to GitHub..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Pushed to GitHub" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to push" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Changes have been pushed to GitHub" -ForegroundColor Cyan
Write-Host "You can now pull and deploy on Ubuntu Server" -ForegroundColor Cyan
Write-Host ""
