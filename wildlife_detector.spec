# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Wildlife Detector (Windows .exe build).

Build:
    pyinstaller wildlife_detector.spec --clean --noconfirm

Output:
    dist/WildlifeDetector/WildlifeDetector.exe (+ 同梱フォルダ一式)

配布する際は dist/WildlifeDetector/ フォルダごと zip 圧縮して配布してください。
"""
from PyInstaller.utils.hooks import collect_all, copy_metadata


def _safe_collect(pkg_name: str):
    """指定パッケージ未導入でも spec を読み込めるよう例外を握りつぶす。"""
    try:
        return collect_all(pkg_name)
    except Exception:
        return ([], [], [])


def _safe_metadata(pkg_name: str):
    """importlib.metadata.version() から参照される dist-info のみ同梱する。"""
    try:
        return copy_metadata(pkg_name)
    except Exception:
        return []


datas = []
binaries = []
hiddenimports = []

# ランタイム必須の大物パッケージ。speciesnet の依存（TensorFlow 等）も
# collect_all で自動的に拾わせる。
for _pkg in (
    "speciesnet",
    "PySide6",
    "cv2",
    "PIL",
    "pandas",
    "numpy",
    "tqdm",
    "tensorflow",
    "matplotlib",
    "huggingface_hub",
    "kagglehub",
    "reverse_geocoder",
):
    _d, _b, _h = _safe_collect(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# speciesnet が importlib.metadata.version() で参照する推移的依存の dist-info。
# 同梱しないと PackageNotFoundError('cloudpathlib') などで初期化が失敗する。
for _meta_pkg in (
    "cloudpathlib",
    "absl-py",
    "humanfriendly",
    "PyYAML",
    "tensorflow",
    "protobuf",
    "matplotlib",
    "huggingface_hub",
    "kagglehub",
    "reverse_geocoder",
    "torch",
    "torchvision",
):
    datas += _safe_metadata(_meta_pkg)


a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WildlifeDetector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="WildlifeDetector",
)
