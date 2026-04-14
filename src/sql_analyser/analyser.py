"""SQL analyser for extracting source data models from SQL statements.

This module provides the core analysis functionality that extracts tables, columns,
and their relationships from a parsed SQL AST using sqlglot's scope analysis.
"""

from __future__ import annotations

import logging
from typing import cast

import sqlglot.expressions as exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from .domain import (
    AnalysisResult,
    ColumnUsage,
    DataModel,
    QueriedColumn,
    QueriedTable,
    Relationship,
)
from .metrics import compute_metrics

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


def _resolve_cte_to_base_tables(
    cte_alias: str, scope: Scope, visited: set[str] | None = None
) -> set[str]:
    """Resolve a CTE alias to its base table(s) recursively.

    Args:
        cte_alias: The CTE alias to resolve.
        scope: The current scope containing source information.
        visited: Set of CTE aliases already visited (for cycle detection).

    Returns:
        A set of qualified base table names that the CTE references.
        Empty set if the CTE cannot be resolved.

    Resolution algorithm:
        1. Look up the CTE alias in scope.sources
        2. If it's not a Scope (CTE), return empty set
        3. Walk the CTE's scope to find all base tables it references
        4. For nested CTEs, recursively resolve them
        5. Return the union of all base tables

    Examples:
        >>> _resolve_cte_to_base_tables("tmp", scope, set())
        {'orders'}
        >>> _resolve_cte_to_base_tables("nested", scope, set())
        {'orders', 'customers'}  # nested CTE referencing multiple tables
    """
    if visited is None:
        visited = set()

    # Cycle detection
    if cte_alias in visited:
        logger.warning(f"Circular CTE reference detected: {cte_alias}")
        return set()

    visited.add(cte_alias)

    # Look up the CTE in scope.sources
    if cte_alias not in scope.sources:
        logger.debug(f"CTE alias not found in scope: {cte_alias}")
        return set()

    source = scope.sources[cte_alias]
    if not isinstance(source, Scope):
        # Not a CTE/subquery, this shouldn't happen in normal flow
        logger.debug(f"{cte_alias} is not a CTE (not a Scope)")
        return set()

    # Traverse the CTE's scope to find base tables
    cte_scope = source
    base_tables: set[str] = set()

    # Build alias map for the CTE's scope
    for alias, cte_source in cte_scope.sources.items():
        if isinstance(cte_source, exp.Table):
            # Direct base table reference
            qn = build_qualified_name(
                cte_source.name, cte_source.db or None, cte_source.catalog or None
            )
            base_tables.add(qn)
            logger.debug(f"CTE {cte_alias} references base table {qn}")
        elif isinstance(cte_source, Scope):
            # Nested CTE - recursively resolve
            nested_tables = _resolve_cte_to_base_tables(alias, scope, visited)
            base_tables.update(nested_tables)
            logger.debug(
                f"CTE {cte_alias} references nested CTE {alias} → {nested_tables}"
            )

    return base_tables


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
    all_relationships: list[Relationship] = []
    logger.debug("Starting relationship extraction")

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
                    # Skip Star expressions (handled separately in wildcard detection)
                    if isinstance(select_expr, exp.Star):
                        continue

                    # Skip Column expressions where this is a Star (qualified wildcards)
                    if isinstance(select_expr, exp.Column) and isinstance(
                        select_expr.this, exp.Star
                    ):
                        continue

                    columns = _walk_in_scope(select_expr, exp.Column)
                    for column in columns:
                        table_alias = str(
                            column.table if hasattr(column, "table") else ""
                        )
                        column_name = str(
                            column.name if hasattr(column, "name") else column
                        )

                        resolved_qn = _resolve_alias(
                            table_alias, scope, alias_to_qualified
                        )
                        if resolved_qn is not None and resolved_qn in table_registry:
                            _add_or_update_column(
                                table_registry[resolved_qn], column_name, usage
                            )
            else:
                # Handle other clauses (single node)
                if not isinstance(clause_node, list):
                    columns = _walk_in_scope(clause_node, exp.Column)
                    for column in columns:
                        table_alias = str(
                            column.table if hasattr(column, "table") else ""
                        )
                        column_name = str(
                            column.name if hasattr(column, "name") else column
                        )

                        resolved_qn = _resolve_alias(
                            table_alias, scope, alias_to_qualified
                        )
                        if resolved_qn is not None and resolved_qn in table_registry:
                            _add_or_update_column(
                                table_registry[resolved_qn], column_name, usage
                            )

        # Handle JOIN ON clauses separately
        joins = _walk_in_scope(cast(exp.Expression, scope.expression), exp.Join)
        for join in joins:
            on_condition = join.args.get("on") if hasattr(join, "args") else None
            if on_condition:
                columns = _walk_in_scope(on_condition, exp.Column)
                for column in columns:
                    table_alias = str(column.table if hasattr(column, "table") else "")
                    column_name = str(
                        column.name if hasattr(column, "name") else column
                    )

                    resolved_qn = _resolve_alias(table_alias, scope, alias_to_qualified)
                    if resolved_qn is not None and resolved_qn in table_registry:
                        _add_or_update_column(
                            table_registry[resolved_qn],
                            column_name,
                            ColumnUsage.JOIN_ON,
                        )

        # Handle wildcard detection (SELECT * or table.*)
        # Check SELECT expressions for Star nodes
        if hasattr(scope.expression, "expressions"):
            for select_expr in scope.expression.expressions:
                # Unqualified SELECT * (bare Star node)
                if isinstance(select_expr, exp.Star):
                    logger.debug(
                        "Found unqualified SELECT * - flagging all base tables"
                    )
                    for qn in alias_to_qualified.values():
                        if qn in table_registry:
                            table_registry[qn].has_wildcard = True
                            logger.debug(f"Flagged {qn} with wildcard")

                # Qualified SELECT table.* (Column with Star as this)
                elif isinstance(select_expr, exp.Column) and isinstance(
                    select_expr.this, exp.Star
                ):
                    star_table = str(
                        select_expr.table if hasattr(select_expr, "table") else ""
                    )
                    resolved_qn = _resolve_alias(star_table, scope, alias_to_qualified)
                    if resolved_qn is not None and resolved_qn in table_registry:
                        table_registry[resolved_qn].has_wildcard = True
                        logger.debug(f"Flagged {resolved_qn} with qualified wildcard")

        # Step 2d: Extract relationships from JOINs
        # Find all JOIN nodes in this scope
        joins = _walk_in_scope(cast(exp.Expression, scope.expression), exp.Join)
        for join in joins:
            on_condition = join.args.get("on") if hasattr(join, "args") else None
            if on_condition:
                # Find all equality predicates in the ON condition
                eq_predicates = _walk_in_scope(on_condition, exp.EQ)

                # Group column pairs by table pair (for multi-column relationships)
                table_pair_map: dict[tuple[str, str], list[tuple[str, str]]] = {}

                for eq in eq_predicates:
                    # Check both operands exist and are Column instances
                    if not (hasattr(eq, "left") and hasattr(eq, "right")):
                        continue
                    if not (
                        isinstance(eq.left, exp.Column)
                        and isinstance(eq.right, exp.Column)
                    ):
                        continue

                    # Extract table aliases and column names
                    left_table_alias = str(
                        eq.left.table if hasattr(eq.left, "table") else ""
                    )
                    right_table_alias = str(
                        eq.right.table if hasattr(eq.right, "table") else ""
                    )

                    # Resolve aliases to qualified table names
                    left_qn = _resolve_alias(
                        left_table_alias, scope, alias_to_qualified
                    )
                    right_qn = _resolve_alias(
                        right_table_alias, scope, alias_to_qualified
                    )

                    # If alias resolution failed, try CTE resolution
                    left_tables: set[str] = set()
                    right_tables: set[str] = set()

                    if left_qn is not None:
                        left_tables.add(left_qn)
                    else:
                        # Try to resolve as CTE
                        left_tables = _resolve_cte_to_base_tables(
                            left_table_alias, scope
                        )

                    if right_qn is not None:
                        right_tables.add(right_qn)
                    else:
                        # Try to resolve as CTE
                        right_tables = _resolve_cte_to_base_tables(
                            right_table_alias, scope
                        )

                    # Accumulate column pairs for all base table combinations
                    for left_base in left_tables:
                        for right_base in right_tables:
                            key = (left_base, right_base)
                            if key not in table_pair_map:
                                table_pair_map[key] = []
                            table_pair_map[key].append(
                                (str(eq.left.name), str(eq.right.name))
                            )

                # Create relationships from grouped data
                for (left_qn, right_qn), col_pairs in table_pair_map.items():
                    left_cols = [pair[0] for pair in col_pairs]
                    right_cols = [pair[1] for pair in col_pairs]
                    all_relationships.append(
                        Relationship(
                            left_table=left_qn,
                            left_columns=left_cols,
                            right_table=right_qn,
                            right_columns=right_cols,
                        )
                    )
                    logger.debug(
                        f"Extracted JOIN relationship: {left_qn} ↔ {right_qn} "
                        f"({len(col_pairs)} column{'s' if len(col_pairs) > 1 else ''})"
                    )

        # Step 2e: Extract relationships from implicit WHERE joins
        where_clause = scope.expression.find(exp.Where)
        if where_clause:
            # Find all equality predicates in WHERE clause
            eq_predicates = _walk_in_scope(where_clause, exp.EQ)

            for eq in eq_predicates:
                # Check both operands exist and are Column instances
                if not (hasattr(eq, "left") and hasattr(eq, "right")):
                    continue
                # Cast eq to access .left and .right attributes safely
                eq_expr = cast(exp.EQ, eq)
                if not (
                    isinstance(eq_expr.left, exp.Column)
                    and isinstance(eq_expr.right, exp.Column)
                ):
                    continue
                # Type narrowing: after isinstance checks, we know these are Columns
                left_col = cast(exp.Column, eq_expr.left)
                right_col = cast(exp.Column, eq_expr.right)

                left_table_alias = str(
                    left_col.table if hasattr(left_col, "table") else ""
                )
                right_table_alias = str(
                    right_col.table if hasattr(right_col, "table") else ""
                )

                # Skip unqualified columns (likely filters, not joins)
                if not left_table_alias or not right_table_alias:
                    continue

                # Resolve aliases to qualified table names
                left_qn = _resolve_alias(left_table_alias, scope, alias_to_qualified)
                right_qn = _resolve_alias(right_table_alias, scope, alias_to_qualified)

                # If alias resolution failed, try CTE resolution
                left_where_tables: set[str] = set()
                right_where_tables: set[str] = set()

                if left_qn is not None:
                    left_where_tables.add(left_qn)
                else:
                    # Try to resolve as CTE
                    left_where_tables = _resolve_cte_to_base_tables(
                        left_table_alias, scope
                    )

                if right_qn is not None:
                    right_where_tables.add(right_qn)
                else:
                    # Try to resolve as CTE
                    right_where_tables = _resolve_cte_to_base_tables(
                        right_table_alias, scope
                    )

                # Create relationships for all base table combinations
                for left_base in left_where_tables:
                    for right_base in right_where_tables:
                        # Skip same-table comparisons (not joins)
                        if left_base != right_base:
                            all_relationships.append(
                                Relationship(
                                    left_table=left_base,
                                    left_columns=[str(left_col.name)],
                                    right_table=right_base,
                                    right_columns=[str(right_col.name)],
                                )
                            )
                            logger.debug(
                                f"Extracted implicit WHERE relationship: {left_base} ↔ {right_base}"
                            )

    # Step 3: Deduplicate relationships
    seen_keys: set[tuple[tuple[str, tuple[str, ...]], ...]] = set()
    unique_relationships: list[Relationship] = []

    for rel in all_relationships:
        if rel.canonical_key not in seen_keys:
            seen_keys.add(rel.canonical_key)
            unique_relationships.append(rel)

    logger.debug(
        f"Deduplicated {len(all_relationships)} relationships to "
        f"{len(unique_relationships)} unique"
    )

    # Step 4: Compose DataModel
    data_model = DataModel(
        tables=list(table_registry.values()),
        relationships=unique_relationships,  # Deduplicated relationships
    )

    # Step 5: Compute complexity metrics
    metrics = compute_metrics(expression)
    logger.debug(
        f"Computed metrics: {metrics.node_count} nodes, {metrics.scope_count} scopes"
    )

    # Step 6: Wrap in AnalysisResult
    result = AnalysisResult(data_model=data_model, metrics=metrics)
    logger.debug(
        f"Analysis complete: {len(data_model.tables)} tables, "
        f"{sum(len(t.columns) for t in data_model.tables)} columns"
    )

    return result
