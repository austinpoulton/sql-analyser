"""Tests for FR-002: Relationship Extraction.

This module tests the extraction of relationships from SQL statements
across explicit JOINs, implicit WHERE joins, multi-column keys, self-joins,
and CTE resolution.
"""

from __future__ import annotations

from sql_analyser import analyse


# Phase 3A: Basic relationship extraction


def test_single_column_join(single_column_join):
    """TC-002-01: Extract relationship from single-column JOIN.

    Verifies basic JOIN relationship extraction with alias resolution.
    """
    result = analyse(single_column_join)

    # Verify one relationship extracted
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify relationship properties (order-independent)
    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "customers" in tables

    # Verify columns (determine which side is which)
    if rel.left_table == "orders":
        assert rel.left_columns == ["customer_id"]
        assert rel.right_columns == ["id"]
    else:
        assert rel.left_columns == ["id"]
        assert rel.right_columns == ["customer_id"]


def test_multi_column_join(multi_column_join):
    """TC-002-02: Extract multi-column relationship.

    Verifies composite key relationships are grouped correctly.
    """
    result = analyse(multi_column_join)

    # Verify one relationship extracted
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify tables
    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "shipments" in tables

    # Verify both columns present (order may vary)
    assert len(rel.left_columns) == 2
    assert len(rel.right_columns) == 2
    assert set(rel.left_columns) == {"region", "order_id"}
    assert set(rel.right_columns) == {"region", "order_id"}


def test_implicit_where_join(implicit_where_join):
    """TC-002-03: Extract relationship from implicit WHERE join.

    Verifies implicit joins produce same relationships as explicit JOINs.
    """
    result = analyse(implicit_where_join)

    # Should produce same relationship as explicit JOIN
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify tables
    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "customers" in tables

    # Verify columns (order-independent)
    all_cols = set(rel.left_columns + rel.right_columns)
    assert "customer_id" in all_cols
    assert "id" in all_cols


def test_multiple_joins(multiple_joins):
    """TC-002-04: Extract relationships from multiple JOINs.

    Verifies chain of JOINs produces multiple relationships.
    """
    result = analyse(multiple_joins)

    # Verify two relationships extracted
    assert len(result.data_model.relationships) == 2

    # Find relationships by table pairs
    rel_by_tables = {}
    for rel in result.data_model.relationships:
        key = tuple(sorted([rel.left_table, rel.right_table]))
        rel_by_tables[key] = rel

    # Verify orders ↔ customers relationship
    orders_customers_key = tuple(sorted(["orders", "customers"]))
    assert orders_customers_key in rel_by_tables
    oc_rel = rel_by_tables[orders_customers_key]
    if oc_rel.left_table == "orders":
        assert "customer_id" in oc_rel.left_columns
        assert "id" in oc_rel.right_columns
    else:
        assert "id" in oc_rel.left_columns
        assert "customer_id" in oc_rel.right_columns

    # Verify orders ↔ products relationship
    orders_products_key = tuple(sorted(["orders", "products"]))
    assert orders_products_key in rel_by_tables
    op_rel = rel_by_tables[orders_products_key]
    if op_rel.left_table == "orders":
        assert "product_id" in op_rel.left_columns
        assert "id" in op_rel.right_columns
    else:
        assert "id" in op_rel.left_columns
        assert "product_id" in op_rel.right_columns


def test_self_join(self_join):
    """TC-002-06: Extract relationship from self-join.

    Verifies self-joins create valid relationships with same table on both sides.
    """
    result = analyse(self_join)

    # Verify one relationship extracted
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify both sides reference the same table
    assert rel.left_table == "users"
    assert rel.right_table == "users"

    # Verify columns (order-independent, but both columns should be present)
    all_cols = set(rel.left_columns + rel.right_columns)
    assert "manager_id" in all_cols
    assert "id" in all_cols


def test_relationship_deduplication(union_with_duplicate_join):
    """TC-002-07: Deduplicate relationships from UNION.

    Verifies symmetric relationships are deduplicated via canonical_key.
    """
    result = analyse(union_with_duplicate_join)

    # Should have only 1 relationship despite two identical JOINs
    assert len(result.data_model.relationships) == 1

    rel = result.data_model.relationships[0]
    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "customers" in tables


# Phase 3B: CTE resolution


def test_cte_join(cte_join):
    """TC-002-05: Resolve CTE in JOIN to base table.

    Verifies CTE aliases are resolved to base tables in relationships.
    """
    result = analyse(cte_join)

    # Should resolve tmp → orders
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify tables (CTE should be resolved to base table)
    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "products" in tables
    assert "tmp" not in tables  # CTE should not appear

    # Verify columns
    all_cols = set(rel.left_columns + rel.right_columns)
    assert "order_id" in all_cols
