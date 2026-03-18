"""SQL analyser for extracting source data models from SQL statements.

This module provides the core analysis functionality that extracts tables, columns,
and their relationships from a parsed SQL AST using sqlglot's scope analysis.
"""

from __future__ import annotations

import logging

import sqlglot.expressions as exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from .domain import (
    AnalysisResult,
    DataModel,
    QueriedTable,
)

logger = logging.getLogger(__name__)


def build_qualified_name(
    name: str, schema: str | None = None, catalog: str | None = None
) -> str:
    """Build a qualified table name from its components.

    Joins non-empty parts with dots to create a fully qualified name.

    Args:
        name: The table name (required).
        schema: The schema/database name (optional).
        catalog: The catalog name (optional).

    Returns:
        A qualified name string (e.g., "catalog.schema.table" or just "table").

    Examples:
        >>> build_qualified_name("orders")
        'orders'
        >>> build_qualified_name("orders", "core_facts")
        'core_facts.orders'
        >>> build_qualified_name("orders", "core_facts", "my_catalog")
        'my_catalog.core_facts.orders'
    """
    parts = []
    if catalog:
        parts.append(catalog)
    if schema:
        parts.append(schema)
    parts.append(name)
    return ".".join(parts)


def _enumerate_scopes(expression: exp.Expression) -> list[Scope]:
    """Enumerate all scopes in the expression in post-order.

    Post-order traversal ensures that inner scopes (CTEs, subqueries) are
    processed before their containing scopes. This is critical for correctly
    resolving CTE references and attributing columns to base tables.

    Args:
        expression: The parsed SQL expression to analyze.

    Returns:
        A list of Scope objects in post-order (innermost first, root last).

    Examples:
        For "WITH cte AS (SELECT * FROM t1) SELECT * FROM cte",
        the CTE scope is returned before the outer SELECT scope.
    """
    scopes = list(traverse_scope(expression))
    logger.debug(f"Found {len(scopes)} scopes")
    return scopes


def analyse(expression: exp.Expression) -> AnalysisResult:
    """Analyse a SQL expression and extract its source data model.

    This is the main entry point for SQL analysis. It performs scope traversal,
    base table resolution, column extraction, and constructs a complete DataModel.

    Args:
        expression: A parsed sqlglot Expression (use sqlglot.parse_one()).

    Returns:
        An AnalysisResult containing the extracted DataModel with tables and columns.
        Relationships, output columns, and metrics are populated by later phases.

    Examples:
        >>> import sqlglot
        >>> expr = sqlglot.parse_one("SELECT id FROM users", dialect="postgres")
        >>> result = analyse(expr)
        >>> len(result.data_model.tables)
        1
        >>> result.data_model.tables[0].name
        'users'
    """
    logger.debug("Starting analysis")

    # Initialize data structures
    table_registry: dict[str, QueriedTable] = {}

    # Step 1: Enumerate scopes in post-order
    scopes = _enumerate_scopes(expression)

    # Step 2: Process each scope
    for scope in scopes:
        # Build alias map for this scope
        alias_to_qualified: dict[str, str] = {}

        # Register base tables (skip CTE/subquery sources)
        for alias, source in scope.sources.items():
            if isinstance(source, exp.Table):
                # This is a base table reference
                qn = build_qualified_name(
                    source.name, source.db or None, source.catalog or None
                )
                alias_to_qualified[alias] = qn

                if qn not in table_registry:
                    table_registry[qn] = QueriedTable(
                        name=source.name,
                        schema_name=source.db or "",
                        catalog_name=source.catalog or "",
                    )
                    logger.debug(f"Registered table {qn}")
            # elif isinstance(source, Scope):
            #     # This is a CTE or subquery - skip, handled by child scope
            #     pass

    # Step 3: Compose DataModel
    data_model = DataModel(
        tables=list(table_registry.values()),
        relationships=[],  # Phase 3 will populate this
    )

    # Step 4: Wrap in AnalysisResult
    result = AnalysisResult(data_model=data_model)
    logger.debug(
        f"Analysis complete: {len(data_model.tables)} tables, "
        f"{sum(len(t.columns) for t in data_model.tables)} columns"
    )

    return result
