"""pytest 設定: プロジェクトルートを sys.path に追加。

`python main.py` で実行する前提のフラット構成のため、
tests から core / utils をインポートできるように解決パスを通す。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
