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
    ColumnUsage,
    DataModel,
    QueriedColumn,
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


def _walk_in_scope(
    node: exp.Expression | None, node_type: type[exp.Expression]
) -> list[exp.Expression]:
    """Walk an AST node and find all descendants of a specific type.

    Args:
        node: The root node to search (can be None).
        node_type: The type of expression to find (e.g., exp.Column).

    Returns:
        A list of matching expression nodes.

    Examples:
        >>> where_clause = expression.find(exp.Where)
        >>> columns = _walk_in_scope(where_clause, exp.Column)
    """
    if node is None:
        return []
    return list(node.find_all(node_type))


def _resolve_alias(alias: str, scope: Scope, alias_map: dict[str, str]) -> str | None:
    """Resolve a table alias to its qualified base table name.

    Args:
        alias: The table alias to resolve.
        scope: The current scope containing source information.
        alias_map: Pre-built mapping of alias -> qualified_name for base tables.

    Returns:
        The qualified table name if resolved, None otherwise.

    Resolution rules:
        - If alias is in alias_map, return the qualified name (direct base table).
        - If alias is empty and scope has exactly one base table, return that table.
        - If alias maps to a Scope (CTE/subquery), return None (skip).
        - Otherwise return None (unresolved).

    Examples:
        >>> _resolve_alias("o", scope, {"o": "orders", "c": "customers"})
        'orders'
        >>> _resolve_alias("", scope_with_single_table, {...})
        'users'
        >>> _resolve_alias("cte", scope, {...})  # CTE reference
        None
    """
    # Direct alias lookup
    if alias in alias_map:
        return alias_map[alias]

    # Unqualified column in single-table scope
    if not alias and len(alias_map) == 1:
        return next(iter(alias_map.values()))

    # CTE or subquery reference - check if alias maps to a Scope
    if alias in scope.sources and isinstance(scope.sources[alias], Scope):
        logger.debug(f"Skipping CTE/subquery reference: {alias}")
        return None

    # Unresolved
    if alias:
        logger.warning(f"Unresolved alias: {alias}")
    return None


def _add_or_update_column(
    table: QueriedTable, column_name: str, usage: ColumnUsage
) -> None:
    """Add a column to a table or update its usage if it already exists.

    Args:
        table: The QueriedTable to modify.
        column_name: The name of the column.
        usage: The ColumnUsage to add.

    Side effects:
        - If column doesn't exist, creates a new QueriedColumn and appends it.
        - If column exists, adds the usage to its usages set.

    Examples:
        >>> table = QueriedTable(name="users")
        >>> _add_or_update_column(table, "id", ColumnUsage.SELECT)
        >>> len(table.columns)
        1
        >>> _add_or_update_column(table, "id", ColumnUsage.WHERE)
        >>> len(table.columns)  # Still 1, usage added
        1
        >>> table.columns[0].usages
        {<ColumnUsage.SELECT: 'select'>, <ColumnUsage.WHERE: 'where'>}
    """
    # Search for existing column (case-insensitive match)
    for col in table.columns:
        if col.name.lower() == column_name.lower():
            col.usages.add(usage)
            logger.debug(
                f"Updated column {table.qualified_name}.{column_name} with usage {usage}"
            )
            return

    # Column doesn't exist, create it
    new_col = QueriedColumn(name=column_name, usages={usage})
    table.columns.append(new_col)
    logger.debug(
        f"Added column {table.qualified_name}.{column_name} with usage {usage}"
    )


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

    # Step 1: Enumerate scopes in post-order (innermost first)
    # This ensures CTEs/subqueries are processed before their containing scopes
    scopes = list(traverse_scope(expression))
    logger.debug(f"Found {len(scopes)} scopes")

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
            elif isinstance(source, Scope):
                # This is a CTE or subquery - skip, handled by child scope
                logger.debug(f"Skipping CTE/subquery: {alias}")
                pass

        # Extract columns from all SQL clauses
        clause_map: dict[ColumnUsage, exp.Expression | list[exp.Expression] | None] = {
            ColumnUsage.SELECT: scope.expression.expressions
            if hasattr(scope.expression, "expressions")
            else None,
            ColumnUsage.WHERE: scope.expression.find(exp.Where),
            ColumnUsage.GROUP_BY: scope.expression.find(exp.Group),
            ColumnUsage.HAVING: scope.expression.find(exp.Having),
            ColumnUsage.ORDER_BY: scope.expression.find(exp.Order),
            ColumnUsage.JOIN_ON: None,  # Will handle separately
        }

        # Extract columns from each clause
        for usage, clause_node in clause_map.items():
            if clause_node is None:
                continue

            # Handle SELECT clause (list of expressions)
            if usage == ColumnUsage.SELECT and isinstance(clause_node, list):
                for select_expr in clause_node:
                    columns = _walk_in_scope(select_expr, exp.Column)
                    for column in columns:
                        table_alias = column.table if hasattr(column, "table") else ""
                        column_name = (
                            column.name if hasattr(column, "name") else str(column)
                        )

                        qn = _resolve_alias(table_alias, scope, alias_to_qualified)
                        if qn and qn in table_registry:
                            _add_or_update_column(
                                table_registry[qn], column_name, usage
                            )
            else:
                # Handle other clauses (single node)
                columns = _walk_in_scope(clause_node, exp.Column)
                for column in columns:
                    table_alias = column.table if hasattr(column, "table") else ""
                    column_name = (
                        column.name if hasattr(column, "name") else str(column)
                    )

                    qn = _resolve_alias(table_alias, scope, alias_to_qualified)
                    if qn and qn in table_registry:
                        _add_or_update_column(table_registry[qn], column_name, usage)

        # Handle JOIN ON clauses separately
        joins = _walk_in_scope(scope.expression, exp.Join)
        for join in joins:
            on_condition = join.args.get("on") if hasattr(join, "args") else None
            if on_condition:
                columns = _walk_in_scope(on_condition, exp.Column)
                for column in columns:
                    table_alias = column.table if hasattr(column, "table") else ""
                    column_name = (
                        column.name if hasattr(column, "name") else str(column)
                    )

                    qn = _resolve_alias(table_alias, scope, alias_to_qualified)
                    if qn and qn in table_registry:
                        _add_or_update_column(
                            table_registry[qn], column_name, ColumnUsage.JOIN_ON
                        )

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
