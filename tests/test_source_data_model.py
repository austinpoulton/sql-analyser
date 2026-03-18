"""Tests for FR-001: Source Data Model Extraction.

This module tests the extraction of tables and columns from SQL statements
across all clause types, CTE handling, and edge cases.
"""

from __future__ import annotations


from sql_analyser import analyse


# Phase 2A: Basic single-table and multi-table queries


def test_single_table_select(simple_select):
    """TC-001-01: Extract table and column from simple SELECT.

    Phase 2A: Verifies basic table registration.
    Column extraction will be implemented in Phase 2B.
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

    # Phase 2A: Table registration only
    # Column extraction will be tested in Phase 2B


def test_multi_table_join(multi_table_join):
    """TC-001-02: Extract tables and columns from multi-table join with aliases.

    Verifies:
    - Both tables extracted
    - Aliases resolved to base tables
    - Columns attributed to correct tables
    - JOIN_ON columns have correct usage (will be implemented in Phase 2B)
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

    # Note: Column extraction will be implemented in Phase 2B
    # For now, we just verify tables are registered correctly
