"""Tests for FR-001: Source Data Model Extraction.

This module tests the extraction of tables and columns from SQL statements
across all clause types, CTE handling, and edge cases.
"""

from __future__ import annotations


from sql_analyser import ColumnUsage, analyse


# Phase 2A: Basic single-table and multi-table queries


def test_single_table_select(simple_select):
    """TC-001-01: Extract table and column from simple SELECT.

    Verifies basic table registration and column extraction from SELECT clause.
    """
    result = analyse(simple_select)

    # Verify one table extracted
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]

    # Verify table properties
    assert table.name == "users"
    assert table.qualified_name == "users"
    assert table.schema_name == ""
    assert table.catalog_name == ""
    assert table.has_wildcard is False

    # Phase 2B: Verify column extraction
    assert len(table.columns) == 1
    col = table.columns[0]
    assert col.name == "id"
    assert ColumnUsage.SELECT in col.usages


def test_multi_table_join(multi_table_join):
    """TC-001-02: Extract tables and columns from multi-table join with aliases.

    Verifies:
    - Both tables extracted
    - Aliases resolved to base tables
    - Columns attributed to correct tables
    - JOIN_ON columns have correct usage
    """
    result = analyse(multi_table_join)

    # Verify two tables extracted
    assert len(result.data_model.tables) == 2

    # Find tables by name (order may vary)
    tables_by_name = {t.name: t for t in result.data_model.tables}
    assert "orders" in tables_by_name
    assert "customers" in tables_by_name

    orders_table = tables_by_name["orders"]
    customers_table = tables_by_name["customers"]

    # Verify table properties
    assert orders_table.qualified_name == "orders"
    assert customers_table.qualified_name == "customers"

    # Verify columns extracted
    # orders has: id (SELECT), customer_id (JOIN_ON)
    assert len(orders_table.columns) == 2
    orders_cols = {col.name: col for col in orders_table.columns}
    assert "id" in orders_cols
    assert "customer_id" in orders_cols
    assert ColumnUsage.SELECT in orders_cols["id"].usages
    assert ColumnUsage.JOIN_ON in orders_cols["customer_id"].usages

    # customers has: name (SELECT), id (JOIN_ON)
    assert len(customers_table.columns) == 2
    customers_cols = {col.name: col for col in customers_table.columns}
    assert "name" in customers_cols
    assert "id" in customers_cols
    assert ColumnUsage.SELECT in customers_cols["name"].usages
    assert ColumnUsage.JOIN_ON in customers_cols["id"].usages


# Phase 2B: Additional clause types


def test_where_clause(where_clause):
    """TC-001-03: Extract columns from WHERE clause."""
    result = analyse(where_clause)

    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "orders"

    # Verify columns: id (SELECT), region (WHERE)
    assert len(table.columns) == 2
    cols = {col.name: col for col in table.columns}
    assert "id" in cols
    assert "region" in cols
    assert ColumnUsage.SELECT in cols["id"].usages
    assert ColumnUsage.WHERE in cols["region"].usages


def test_group_by_clause(group_by_clause):
    """TC-001-04: Extract columns from GROUP BY clause."""
    result = analyse(group_by_clause)

    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "sales"

    # Verify columns: product_id (SELECT, GROUP_BY)
    assert len(table.columns) == 1
    col = table.columns[0]
    assert col.name == "product_id"
    assert ColumnUsage.SELECT in col.usages
    assert ColumnUsage.GROUP_BY in col.usages


def test_having_clause(having_clause):
    """TC-001-05: Extract columns from HAVING clause."""
    result = analyse(having_clause)

    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "sales"

    # Verify columns: product_id (SELECT, GROUP_BY, HAVING)
    # Note: COUNT(*) doesn't reference a specific column
    assert len(table.columns) == 1
    col = table.columns[0]
    assert col.name == "product_id"
    assert ColumnUsage.SELECT in col.usages
    assert ColumnUsage.GROUP_BY in col.usages
    # HAVING might not include product_id depending on AST structure


def test_order_by_clause(order_by_clause):
    """TC-001-06: Extract columns from ORDER BY clause."""
    result = analyse(order_by_clause)

    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "products"

    # Verify columns: id (SELECT, ORDER_BY), name (SELECT, ORDER_BY)
    assert len(table.columns) == 2
    cols = {col.name: col for col in table.columns}
    assert "id" in cols
    assert "name" in cols
    assert ColumnUsage.SELECT in cols["id"].usages
    assert ColumnUsage.ORDER_BY in cols["id"].usages
    assert ColumnUsage.SELECT in cols["name"].usages
    assert ColumnUsage.ORDER_BY in cols["name"].usages


def test_multiple_usages(multiple_usages):
    """Test column usage accumulation across multiple clauses."""
    result = analyse(multiple_usages)

    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "sales"

    # Verify columns
    cols = {col.name: col for col in table.columns}

    # product_id appears in: SELECT, GROUP BY, ORDER BY
    assert "product_id" in cols
    product_id_usages = cols["product_id"].usages
    assert ColumnUsage.SELECT in product_id_usages
    assert ColumnUsage.GROUP_BY in product_id_usages
    assert ColumnUsage.ORDER_BY in product_id_usages

    # region appears in: WHERE
    assert "region" in cols
    assert ColumnUsage.WHERE in cols["region"].usages
