"""認可（SECURITY-08 / PAT-SEC-01）。"""

from backend.src.common.authz.require_owner import extract_sub, require_owner

__all__ = ["extract_sub", "require_owner"]
