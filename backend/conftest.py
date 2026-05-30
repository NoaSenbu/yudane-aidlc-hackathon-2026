"""pytest 共通設定。

`backend.src.*` の絶対 import を解決するためリポジトリルートを sys.path に追加し、
shared/ の Python 実装（safeguard_policy / asin_extractor、Lambda バンドルで同梱される
共有モジュール）をトップレベル import で解決できるようにする。
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# shared/ の Python 共有モジュール（クロス言語一致の正本）を import 可能にする
_SHARED_PYTHON_DIRS = (
    _REPO_ROOT / "shared" / "safeguard-policy" / "python",
    _REPO_ROOT / "shared" / "asin-extractor" / "python",
)
for _shared_dir in _SHARED_PYTHON_DIRS:
    if _shared_dir.is_dir() and str(_shared_dir) not in sys.path:
        sys.path.insert(0, str(_shared_dir))
