@echo off
REM Wildlife Detector - Windows .exe �r���h�X�N���v�g
REM Windows PowerShell or cmd ��Ŏ��s���Ă��������iWSL �ł͓����܂���j�B
REM
REM �O��:
REM   - README �ɏ]�� wildlife_env ���쐬�ς݂ňˑ��𓱓��ς݂ł��邱��
REM   - Python 3.12 �ȏ�
REM
REM �g����:
REM   scripts\build_exe.bat
REM
REM �o��:
REM   dist\WildlifeDetector\WildlifeDetector.exe (+ ����DLL/�f�[�^)
REM   �z�z����ۂ� dist\WildlifeDetector\ �t�H���_�S�̂� zip ���k���Ă��������B

setlocal enabledelayedexpansion

REM �v���W�F�N�g���[�g�Ɉړ� (���̃X�N���v�g�� 1 �K�w��)
cd /d "%~dp0\.."

if not exist wildlife_env\Scripts\activate.bat (
    echo [ERROR] wildlife_env ��������܂���B
    echo         ��� README �̎菇�� venv ���쐬���Ă�������:
    echo           python -m venv wildlife_env
    echo           wildlife_env\Scripts\activate.bat
    echo           pip install "setuptools^<81" wheel
    echo           pip install -r requirements.txt
    exit /b 1
)

echo === venv �L���� ===
call wildlife_env\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] venv �̗L�����Ɏ��s���܂���
    exit /b 1
)

echo === PyInstaller �𓱓� ===
pip install --quiet --upgrade pip
pip install --quiet "pyinstaller>=6.0"
if errorlevel 1 (
    echo [ERROR] PyInstaller �̓����Ɏ��s���܂���
    exit /b 1
)

echo === ������ build / dist ���폜 ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo === PyInstaller ���s (�����`�\����������܂�) ===
pyinstaller wildlife_detector.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller �r���h�Ɏ��s���܂���
    exit /b 1
)

echo.
echo ===========================================
echo  �r���h����
echo ===========================================
echo  �o��: dist\WildlifeDetector\WildlifeDetector.exe
echo.
echo  �z�z�菇:
echo    1) dist\WildlifeDetector\ �t�H���_�S�̂� zip ���k
echo    2) GitHub Releases �� zip ��Y�t���ăA�b�v���[�h
echo    3) �󂯎�����l�� zip �� �� WildlifeDetector.exe ���_�u���N���b�N
echo.
echo  ����: ����N������ SpeciesNet ���f�� (���SMB) ������DL���܂��B
echo        �l�b�g���[�N�ڑ����K�v�ł��B
echo ===========================================

endlocal
