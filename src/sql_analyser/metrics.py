"""Complexity metrics computation for SQL expressions."""

from __future__ import annotations

from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from .domain import ComplexityMetrics


def compute_metrics(expression: exp.Expression) -> ComplexityMetrics:
    """Compute complexity metrics for a SQL expression.

    Analyzes the AST to count total nodes and enumerate all semantic scopes
    (root, CTEs, subqueries, unions) with their types.

    Args:
        expression: Parsed sqlglot expression.

    Returns:
        ComplexityMetrics with node_count, scope_count, and scope_types.

    Example:
        >>> import sqlglot
        >>> expr = sqlglot.parse_one("SELECT id FROM users")
        >>> metrics = compute_metrics(expr)
        >>> metrics.node_count > 0
        True
        >>> metrics.scope_count
        1
    """
    node_count = _count_nodes(expression)
    scopes = list(traverse_scope(expression))
    scope_count = len(scopes)
    scope_types = _extract_scope_types(scopes)

    return ComplexityMetrics(
        node_count=node_count,
        scope_count=scope_count,
        scope_types=scope_types,
    )


def _count_nodes(expression: exp.Expression) -> int:
    """Count total AST nodes in expression.

    Uses sqlglot's walk() generator to traverse all nodes in the tree,
    including nested expressions and leaf nodes.

    Args:
        expression: The sqlglot expression to analyze.

    Returns:
        Total number of nodes in the AST.

    Example:
        >>> import sqlglot
        >>> expr = sqlglot.parse_one("SELECT 1")
        >>> _count_nodes(expr) > 0
        True
    """
    return sum(1 for _ in expression.walk())


def _extract_scope_types(scopes: list) -> list[str]:
    """Extract scope type names from scope list.

    Each scope's type is derived from its root expression class name
    (e.g., "Select", "CTE", "Union", "Subquery").

    Args:
        scopes: List of sqlglot Scope objects from traverse_scope().

    Returns:
        List of scope type strings in traversal order (may contain duplicates).

    Example:
        >>> # scopes is a list of Scope objects
        >>> # Each has a .expression attribute
        >>> scope_types = _extract_scope_types(scopes)
        >>> isinstance(scope_types, list)
        True
    """
    scope_types = []
    for scope in scopes:
        # Scope.expression is the root node for that scope
        expr_type = type(scope.expression).__name__
        scope_types.append(expr_type)
    return scope_types
