"""
Formatter.
"""
import functools
from typing import Any

import sqlparse

format_query = functools.partial(sqlparse.format, reindent=True, keyword_case="upper")


def reformat_query(query: str) -> str:
    query = query.strip()
    parsed = sqlparse.parse(query)

    statements = [p for p in parsed if str(p).strip()]
    if len(statements) > 1:
        raise ValueError("Only one query is allowed.")

    if not statements:
        return ""

    return format_query(query)


def normalize_params(params: Any) -> Any:
    if isinstance(params, dict):
        return tuple(sorted((k, normalize_params(v)) for k, v in params.items()))
    elif isinstance(params, (list, tuple)):
        return tuple(normalize_params(v) for v in params)
    return params
