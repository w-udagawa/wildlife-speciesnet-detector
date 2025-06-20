# Wildlife Detector Git Setup Script
# PowerShell script with error handling

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Wildlife Detector Git Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location -Path "C:\Users\AU3009\Claudeworks\wildlife_detector"
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Check if Git is installed
try {
    $gitVersion = git --version
    Write-Host "Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/" -ForegroundColor Yellow
    pause
    exit 1
}

# Initialize repository
Write-Host "Step 1: Initializing Git repository..." -ForegroundColor Yellow
git init
if ($?) {
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to initialize repository" -ForegroundColor Red
}
Write-Host ""

# Check if remote already exists
$remotes = git remote
if ($remotes -contains "origin") {
    Write-Host "Remote 'origin' already exists. Updating URL..." -ForegroundColor Yellow
    git remote set-url origin https://github.com/w-udagawa/wildlife-speciesnet-detector.git
} else {
    Write-Host "Step 2: Adding remote repository..." -ForegroundColor Yellow
    git remote add origin https://github.com/w-udagawa/wildlife-speciesnet-detector.git
}
Write-Host "✓ Remote repository configured" -ForegroundColor Green
Write-Host ""

# Add files
Write-Host "Step 3: Adding all files..." -ForegroundColor Yellow
git add .
$status = git status --porcelain
if ($status) {
    Write-Host "✓ Files staged for commit" -ForegroundColor Green
    Write-Host "Files to be committed:" -ForegroundColor Cyan
    git status --short
} else {
    Write-Host "No changes to commit" -ForegroundColor Yellow
}
Write-Host ""

# Create commit
Write-Host "Step 4: Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: Wildlife Detector application with SpeciesNet integration"
if ($?) {
    Write-Host "✓ Initial commit created" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create commit (possibly no changes)" -ForegroundColor Red
}
Write-Host ""

# Rename branch
Write-Host "Step 5: Ensuring main branch..." -ForegroundColor Yellow
git branch -M main
Write-Host "✓ Branch set to 'main'" -ForegroundColor Green
Write-Host ""

# Push to GitHub
Write-Host "Step 6: Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "NOTE: You will need to authenticate with GitHub" -ForegroundColor Cyan
Write-Host "Options:" -ForegroundColor Cyan
Write-Host "  1. Use Personal Access Token (recommended)" -ForegroundColor White
Write-Host "  2. Use GitHub CLI (gh auth login)" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Ready to push to GitHub? (Y/N)"
if ($confirm -eq 'Y' -or $confirm -eq 'y') {
    git push -u origin main
    if ($?) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "✓ Git setup complete!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Repository URL: https://github.com/w-udagawa/wildlife-speciesnet-detector" -ForegroundColor Cyan
        Write-Host ""
        
        # Open in browser
        $openBrowser = Read-Host "Open repository in browser? (Y/N)"
        if ($openBrowser -eq 'Y' -or $openBrowser -eq 'y') {
            Start-Process "https://github.com/w-udagawa/wildlife-speciesnet-detector"
        }
    } else {
        Write-Host ""
        Write-Host "✗ Push failed. Please check your credentials." -ForegroundColor Red
        Write-Host "To set up authentication:" -ForegroundColor Yellow
        Write-Host "  1. Create a Personal Access Token at: https://github.com/settings/tokens" -ForegroundColor White
        Write-Host "  2. Use the token as password when prompted" -ForegroundColor White
    }
} else {
    Write-Host "Push cancelled. You can run 'git push -u origin main' later." -ForegroundColor Yellow
}

Write-Host ""
pause
