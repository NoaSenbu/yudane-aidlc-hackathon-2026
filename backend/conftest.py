"""pytest 共通設定。

`backend.src.*` の絶対 import を解決するため、リポジトリルートを sys.path に追加する。
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
