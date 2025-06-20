@echo off
echo ========================================
echo Wildlife Detector Git Setup
echo ========================================
echo.

cd /d "C:\Users\AU3009\Claudeworks\wildlife_detector"

echo Step 1: Initializing Git repository...
git init

echo.
echo Step 2: Adding remote repository...
git remote add origin https://github.com/w-udagawa/wildlife-speciesnet-detector.git

echo.
echo Step 3: Adding all files...
git add .

echo.
echo Step 4: Creating initial commit...
git commit -m "Initial commit: Wildlife Detector application with SpeciesNet integration"

echo.
echo Step 5: Renaming branch to main...
git branch -M main

echo.
echo Step 6: Pushing to GitHub...
echo NOTE: You will need to enter your GitHub credentials or Personal Access Token
git push -u origin main

echo.
echo ========================================
echo Git setup complete!
echo ========================================
echo.
echo Repository URL: https://github.com/w-udagawa/wildlife-speciesnet-detector
echo.
pause
