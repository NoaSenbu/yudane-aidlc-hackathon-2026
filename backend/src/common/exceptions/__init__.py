"""DomainError 体系（ERR-01〜08）。"""

from backend.src.common.exceptions.domain_error import (
    DomainError,
    ErrorCategory,
    ProblemDetailsDict,
    to_problem_details,
)

__all__ = [
    "DomainError",
    "ErrorCategory",
    "ProblemDetailsDict",
    "to_problem_details",
]
