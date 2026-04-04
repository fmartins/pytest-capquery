"""
SQL query canonicalization and parametric normalization logic.

This module houses utilities designed to strip syntactical variances introduced
during string execution formatting, resulting in a stable deterministic
base allowing precise execution timeline validation.
"""

import functools

import sqlparse

format_query = functools.partial(sqlparse.format, reindent=True, keyword_case="upper")


def reformat_query(query: str) -> str:
    """
    Standardizes whitespace, capitalizes keywords, and explicitly re-indents raw
    SQL execution strings rendering them consistently comparable across permutations.

    Args:
        query (str): The raw SQL string captured during database engine execution.

    Returns:
        str: The fully formatted and canonicalized SQL string safe for deterministic comparison.

    Raises:
        ValueError: If the query contains multiple SQL statements.
    """
    query = query.strip()
    parsed = sqlparse.parse(query)

    statements = [p for p in parsed if str(p).strip()]
    if len(statements) > 1:
        raise ValueError("Only one query is allowed.")

    if not statements:
        return ""

    return format_query(query)


def normalize_params(params: object) -> object:
    """
    Recursively transforms dictionary keyword arguments or nested execution lists
    into immutable, strictly sorted tuples rendering testing assertion logic immune
    to accidental Python implementation detail variances.

    Args:
        params (object): The raw execution parameter structure provided by the dialect driver.

    Returns:
        object: A recursively immutable and normalized tuple representation of the inputs.
    """
    if isinstance(params, dict):
        return tuple(sorted((k, normalize_params(v)) for k, v in params.items()))
    elif isinstance(params, (list, tuple)):
        return tuple(normalize_params(v) for v in params)
    return params
