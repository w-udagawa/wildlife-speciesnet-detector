@echo off
chcp 65001 > nul
setlocal
REM Wildlife Detector - portable launcher (GUI, no console)
REM Place this file at the root of the extracted distribution folder.

set "ROOT=%~dp0"
set "PYTHONHOME=%ROOT%runtime"
set "PYTHONPATH=%ROOT%app;%ROOT%runtime\Lib\site-packages"
set "PYTHONIOENCODING=utf-8"
set "QT_PLUGIN_PATH=%ROOT%runtime\Lib\site-packages\PySide6\plugins"
set "QT_QPA_PLATFORM_PLUGIN_PATH=%QT_PLUGIN_PATH%\platforms"

if not exist "%ROOT%runtime\pythonw.exe" (
    echo [ERROR] runtime\pythonw.exe が見つかりません。
    echo         zip を正しく解凍したフォルダから起動しているか確認してください。
    pause
    exit /b 1
)

cd /d "%ROOT%app"
start "" "%ROOT%runtime\pythonw.exe" "%ROOT%app\main.py"
if errorlevel 1 (
    echo [ERROR] 起動に失敗しました。
    echo         WildlifeDetector-debug.bat を実行して詳細メッセージを確認してください。
    pause
)

endlocal
