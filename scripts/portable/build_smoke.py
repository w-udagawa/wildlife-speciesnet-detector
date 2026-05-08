"""Build-time smoke check for the portable distribution.

Verifies that the Embeddable Python under build/portable/runtime has all the
binary submodules and APIs needed at runtime. Run from build_portable.bat
after dependencies are installed but before zipping.
"""
import json
import sys
from pathlib import Path


def _check_japanese_names_json() -> int:
    """utils/japanese_names.json が build/portable/app に同梱されているか確認"""
    # build_portable.bat は既にプロジェクトルートに cd 済みで本スクリプトを起動する
    jn_path = Path("build") / "portable" / "app" / "utils" / "japanese_names.json"
    if not jn_path.exists():
        print(f"FAIL: japanese_names.json missing at {jn_path}", file=sys.stderr)
        return 1
    try:
        with open(jn_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: japanese_names.json load error: {e}", file=sys.stderr)
        return 1
    if "species" not in data or "category" not in data:
        print("FAIL: japanese_names.json missing required keys (species/category)",
              file=sys.stderr)
        return 1
    print(f"SMOKE OK: japanese_names.json {len(data.get('species', {}))} species, "
          f"{len(data.get('category', {}))} categories")
    return 0


def main() -> int:
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import cv2  # noqa: F401
    import PySide6  # noqa: F401
    import pkg_resources  # noqa: F401

    import torch
    if torch.zeros(2, 2).sum().item() != 0.0:
        print("FAIL: torch.zeros() returned a non-zero sum", file=sys.stderr)
        return 1

    from torch import _C, jit, linalg  # noqa: F401

    import speciesnet
    from speciesnet import SpeciesNet, DEFAULT_MODEL  # noqa: F401

    sn_version = getattr(speciesnet, "__version__", "?")
    print(f"SMOKE OK: torch {torch.__version__} speciesnet {sn_version}")

    return _check_japanese_names_json()


if __name__ == "__main__":
    sys.exit(main())
