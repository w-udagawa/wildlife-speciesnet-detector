@echo off
echo ========================================
echo Git Branch Fix and Push
echo ========================================
echo.

cd /d "C:\Users\AU3009\Claudeworks\wildlife_detector"

echo Current branch status:
git branch
echo.

echo Step 1: Renaming branch from master to main...
git branch -M main

echo.
echo Step 2: Setting upstream and pushing...
git push -u origin main --force

echo.
echo ========================================
echo Push complete!
echo ========================================
echo.
echo Check your repository at:
echo https://github.com/w-udagawa/wildlife-speciesnet-detector
echo.
pause
