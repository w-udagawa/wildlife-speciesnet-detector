@echo off
chcp 65001 > nul
setlocal
REM Wildlife Detector - portable launcher (DEBUG, with console)
REM 通常は WildlifeDetector.bat を使ってください。
REM このファイルは起動トラブル時に Python のエラーメッセージを目視するためのものです。

set "ROOT=%~dp0"
set "PYTHONHOME=%ROOT%runtime"
set "PYTHONPATH=%ROOT%app;%ROOT%runtime\Lib\site-packages"
set "PYTHONIOENCODING=utf-8"
set "QT_PLUGIN_PATH=%ROOT%runtime\Lib\site-packages\PySide6\plugins"
set "QT_QPA_PLATFORM_PLUGIN_PATH=%QT_PLUGIN_PATH%\platforms"

if not exist "%ROOT%runtime\python.exe" (
    echo [ERROR] runtime\python.exe が見つかりません。
    echo         zip を正しく解凍したフォルダから起動しているか確認してください。
    pause
    exit /b 1
)

cd /d "%ROOT%app"
echo === Wildlife Detector (debug mode) ===
echo PYTHONHOME = %PYTHONHOME%
echo PYTHONPATH = %PYTHONPATH%
echo.
"%ROOT%runtime\python.exe" "%ROOT%app\main.py"
set "EXITCODE=%ERRORLEVEL%"
echo.
echo === 終了コード: %EXITCODE% ===
echo ログファイル: %USERPROFILE%\WildlifeDetector\logs\wildlife_detector.log
pause
endlocal
