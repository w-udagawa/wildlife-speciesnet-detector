@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM ============================================================
REM  Wildlife Detector - ポータブル版ビルドスクリプト
REM
REM  Windows Embeddable Python + 依存ライブラリ同梱の zip を生成します。
REM  Windows ネイティブの PowerShell / cmd で実行してください (WSL 不可)。
REM
REM  使い方:
REM    scripts\build_portable.bat
REM
REM  出力:
REM    dist\WildlifeDetector_v2.1.0_portable.zip
REM
REM  必要なツール: Windows 10/11 標準の curl, tar, powershell
REM ============================================================

REM --- プロジェクトルートへ移動 (このスクリプトは scripts\ の 1 階層下) ---
cd /d "%~dp0\.."

REM --- 設定 ---
set "PY_VER=3.12.8"
set "ARCH=amd64"
set "BUILD_DIR=build\portable"
set "CACHE_DIR=build\cache"
set "DIST_NAME=WildlifeDetector_v2.1.0_portable"
set "EMBED_ZIP=%CACHE_DIR%\python-%PY_VER%-embed-%ARCH%.zip"
set "GET_PIP=%CACHE_DIR%\get-pip.py"
set "EMBED_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-embed-%ARCH%.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

echo.
echo ============================================================
echo   Wildlife Detector - Portable build
echo   Python %PY_VER% %ARCH% embeddable
echo ============================================================
echo.

REM --- キャッシュディレクトリ準備 ---
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"

REM --- Embeddable Python の取得 (キャッシュ利用) ---
if exist "%EMBED_ZIP%" (
    echo [1/15] Embeddable Python: cached
) else (
    echo [1/15] Embeddable Python をダウンロード中...
    curl -L --fail -o "%EMBED_ZIP%" "%EMBED_URL%"
    if errorlevel 1 (
        echo [ERROR] Embeddable Python のダウンロードに失敗しました: %EMBED_URL%
        exit /b 1
    )
)

REM --- get-pip.py の取得 (キャッシュ利用) ---
if exist "%GET_PIP%" (
    echo [2/15] get-pip.py: cached
) else (
    echo [2/15] get-pip.py をダウンロード中...
    curl -L --fail -o "%GET_PIP%" "%GET_PIP_URL%"
    if errorlevel 1 (
        echo [ERROR] get-pip.py のダウンロードに失敗しました
        exit /b 1
    )
)

REM --- 既存の build\portable\ をクリア ---
echo [3/15] 既存のビルドディレクトリをクリーンアップ...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%\runtime"
mkdir "%BUILD_DIR%\app"

REM --- Embeddable Python を runtime\ に展開 ---
echo [4/15] Embeddable Python を展開中...
tar -xf "%EMBED_ZIP%" -C "%BUILD_DIR%\runtime"
if errorlevel 1 (
    echo [ERROR] Embeddable Python の展開に失敗しました
    exit /b 1
)

REM --- python3XX._pth を書き換え (import site 有効化 + site-packages 追加) ---
echo [5/15] python312._pth を書き換え (import site 有効化)...
powershell -NoProfile -Command ^
  "$p = '%BUILD_DIR%\runtime\python312._pth';" ^
  "$c = Get-Content -Raw $p;" ^
  "$c = $c -replace '#import site', 'import site';" ^
  "if ($c -notmatch 'Lib\\site-packages') { $c = $c.TrimEnd() + \"`r`nLib\\site-packages`r`n\" };" ^
  "Set-Content -NoNewline -Path $p -Value $c -Encoding Ascii"
if errorlevel 1 (
    echo [ERROR] python312._pth の書き換えに失敗しました
    exit /b 1
)

REM --- pip を導入 ---
echo [6/15] pip を導入中...
"%BUILD_DIR%\runtime\python.exe" "%GET_PIP%" --no-warn-script-location
if errorlevel 1 (
    echo [ERROR] pip の導入に失敗しました
    exit /b 1
)

REM --- setuptools<81 と wheel を先に pin (speciesnet が pkg_resources に依存) ---
echo [7/15] setuptools^<81 と wheel を導入中...
"%BUILD_DIR%\runtime\python.exe" -m pip install --no-warn-script-location --cache-dir "%CACHE_DIR%\pip" "setuptools<81" wheel
if errorlevel 1 (
    echo [ERROR] setuptools^<81 の導入に失敗しました
    exit /b 1
)

REM --- requirements.txt から pyinstaller 行を除外した一時ファイルを生成 ---
echo [8/15] requirements (pyinstaller 除外) を生成中...
findstr /v /i "pyinstaller" requirements.txt > "%BUILD_DIR%\requirements.trimmed.txt"

REM --- アプリ依存ライブラリを導入 ---
echo [9/15] アプリ依存ライブラリを導入中 (数分かかります)...
"%BUILD_DIR%\runtime\python.exe" -m pip install --no-warn-script-location --cache-dir "%CACHE_DIR%\pip" -r "%BUILD_DIR%\requirements.trimmed.txt"
if errorlevel 1 (
    echo [ERROR] requirements の導入に失敗しました
    exit /b 1
)

REM --- 以前のビルドで tensorflow-cpu を入れていた場合に備え、部分インストール残骸を除去 ---
REM speciesnet >= 1.0 は PyTorch 系で tensorflow を必要としないため明示導入は行わない。
echo [10/15] stale tensorflow files cleanup...
if exist "%BUILD_DIR%\runtime\Lib\site-packages\tensorflow" rmdir /s /q "%BUILD_DIR%\runtime\Lib\site-packages\tensorflow"
if exist "%BUILD_DIR%\runtime\Lib\site-packages\tensorflow_cpu" rmdir /s /q "%BUILD_DIR%\runtime\Lib\site-packages\tensorflow_cpu"

REM --- アプリソースをコピー ---
echo [11/15] アプリソースを app\ にコピー中...
xcopy main.py         "%BUILD_DIR%\app\" /Y > nul
xcopy __init__.py     "%BUILD_DIR%\app\" /Y > nul
xcopy LICENSE         "%BUILD_DIR%\app\" /Y > nul
xcopy README.md       "%BUILD_DIR%\app\" /Y > nul
xcopy requirements.txt "%BUILD_DIR%\app\" /Y > nul
xcopy core\*          "%BUILD_DIR%\app\core\"  /E /I /Y /EXCLUDE:scripts\portable\xcopy_exclude.txt > nul
xcopy gui\*           "%BUILD_DIR%\app\gui\"   /E /I /Y /EXCLUDE:scripts\portable\xcopy_exclude.txt > nul
xcopy utils\*         "%BUILD_DIR%\app\utils\" /E /I /Y /EXCLUDE:scripts\portable\xcopy_exclude.txt > nul

REM --- 起動 bat と配布用 README をルートへ配置 ---
echo [12/15] 起動ランチャーと README を配置中...
copy /Y scripts\portable\WildlifeDetector.bat       "%BUILD_DIR%\" > nul
copy /Y scripts\portable\WildlifeDetector-debug.bat "%BUILD_DIR%\" > nul
copy /Y scripts\portable\README_ja.txt              "%BUILD_DIR%\" > nul

REM --- ビルド用の中間ファイルをクリーンアップ (zip に含めない) ---
if exist "%BUILD_DIR%\requirements.trimmed.txt" del /q "%BUILD_DIR%\requirements.trimmed.txt"

REM --- サイズ削減: site-packages 配下の __pycache__ と tests を削除 ---
echo [13/15] サイズ削減 (__pycache__ / *.pyc / サブディレクトリの tests を削除)...
powershell -NoProfile -Command ^
  "Get-ChildItem -Path '%BUILD_DIR%\runtime\Lib\site-packages' -Recurse -Directory -Include '__pycache__','tests','test' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue;" ^
  "Get-ChildItem -Path '%BUILD_DIR%\runtime\Lib\site-packages' -Recurse -Include '*.pyc','*.pyo' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue"

REM --- スモークチェック: 必須 import が通るか ---
echo [14/15] スモークチェック (必須パッケージの import 確認)...
"%BUILD_DIR%\runtime\python.exe" -c "import speciesnet, PySide6, cv2, pandas, numpy, pkg_resources; print('SMOKE OK')"
if errorlevel 1 (
    echo [ERROR] スモークチェック失敗: 必須パッケージの import に失敗しました
    echo         上記メッセージを確認して requirements や _pth の設定を見直してください。
    exit /b 1
)

REM --- zip 化 (System.IO.Compression.ZipFile で UTF-8 ファイル名を保持) ---
REM  Compress-Archive (PS 5.1) は ZIP 内ファイル名を UTF-8 フラグなしで書くため、
REM  日本語ファイル名が Expand-Archive 展開時に CP932 化してしまう。
REM  .NET の ZipFile.CreateFromDirectory は第4引数 includeBaseDirectory=$false、
REM  第5引数 entryNameEncoding=UTF-8 を指定すれば、ZIP 仕様の UTF-8 ビット (0x800) を立てて書ける。
echo [15/15] zip を生成中 (UTF-8 ファイル名対応)...
if not exist "dist" mkdir "dist"
if exist "dist\%DIST_NAME%.zip" del /q "dist\%DIST_NAME%.zip"
powershell -NoProfile -Command ^
  "try {" ^
  "  Add-Type -AssemblyName System.IO.Compression;" ^
  "  Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
  "  $src = (Resolve-Path '%BUILD_DIR%').Path;" ^
  "  $dst = (Join-Path (Resolve-Path 'dist').Path '%DIST_NAME%.zip');" ^
  "  [System.IO.Compression.ZipFile]::CreateFromDirectory($src, $dst, [System.IO.Compression.CompressionLevel]::Optimal, $false, [System.Text.Encoding]::UTF8);" ^
  "} catch { Write-Host '[ERROR]' $_.Exception.Message; exit 1 }"
if errorlevel 1 (
    echo.
    echo [ERROR] zip の生成に失敗しました。
    echo         2GB 超 または 65535 ファイル超の場合は、7-Zip を導入して
    echo         以下を手動実行してください:
    echo           7z a -mx=9 dist\%DIST_NAME%.zip %BUILD_DIR%\*
    exit /b 1
)

REM --- サイズ表示 ---
for %%F in ("dist\%DIST_NAME%.zip") do set "ZIPSIZE=%%~zF"
set /a "ZIPSIZE_MB=%ZIPSIZE% / 1048576"

echo.
echo ============================================================
echo   ビルド完了
echo ============================================================
echo   出力: dist\%DIST_NAME%.zip  (%ZIPSIZE_MB% MB)
echo.
echo   配布手順:
echo     1) 上記 zip を受け取り手に渡す
echo     2) 任意のフォルダに解凍
echo     3) WildlifeDetector.bat をダブルクリック
echo        (初回のみ SpeciesNet モデルを自動ダウンロード)
echo ============================================================

endlocal
