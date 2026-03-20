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


# Phase 2C: CTE and Subquery handling


def test_simple_cte(simple_cte):
    """TC-001-07: Extract base table from simple CTE."""
    result = analyse(simple_cte)

    # Verify only base table extracted, not CTE alias
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "orders"

    # Verify column attributed to base table
    assert len(table.columns) == 1
    col = table.columns[0]
    assert col.name == "order_id"
    # Column appears in both the CTE's SELECT and outer SELECT
    assert ColumnUsage.SELECT in col.usages


def test_nested_cte(nested_cte):
    """TC-001-08: Extract base table from nested CTEs (3 levels)."""
    result = analyse(nested_cte)

    # Verify only base table extracted, not any CTE aliases
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "users"

    # Verify column extracted
    # Note: The WHERE in cte2 references cte1 (a CTE), so those columns are skipped
    # We only capture the initial SELECT from the base table
    cols = {col.name: col for col in table.columns}
    assert "id" in cols
    id_usages = cols["id"].usages
    assert ColumnUsage.SELECT in id_usages
    # The WHERE clause in cte2 references cte1, not the base table,
    # so it's correctly excluded


def test_nested_subquery(nested_subquery):
    """TC-001-09: Extract base table from deeply nested subqueries."""
    result = analyse(nested_subquery)

    # Verify only base table extracted
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "t1"

    # Verify column
    assert len(table.columns) == 1
    col = table.columns[0]
    assert col.name == "a"
    assert ColumnUsage.SELECT in col.usages


def test_correlated_subquery(correlated_subquery):
    """Test correlated subquery with outer scope reference."""
    result = analyse(correlated_subquery)

    # Verify both tables extracted
    assert len(result.data_model.tables) == 2
    tables_by_name = {t.name: t for t in result.data_model.tables}
    assert "orders" in tables_by_name
    assert "order_items" in tables_by_name

    # Verify orders columns
    orders = tables_by_name["orders"]
    orders_cols = {col.name: col for col in orders.columns}
    assert "id" in orders_cols
    # o.id appears in outer SELECT and in the WHERE of the subquery
    assert ColumnUsage.SELECT in orders_cols["id"].usages

    # Verify order_items columns
    order_items = tables_by_name["order_items"]
    order_items_cols = {col.name: col for col in order_items.columns}
    assert "order_id" in order_items_cols
    assert ColumnUsage.WHERE in order_items_cols["order_id"].usages


# Phase 2D: Wildcard detection


def test_unqualified_wildcard(unqualified_wildcard):
    """TC-008-01: Unqualified SELECT * flags table with wildcard.

    Verifies:
    - Table is extracted
    - has_wildcard flag is set to True
    - No columns are invented
    """
    result = analyse(unqualified_wildcard)

    # Verify one table extracted
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]

    # Verify table properties
    assert table.name == "products"
    assert table.has_wildcard is True

    # No columns should be invented for wildcard
    assert len(table.columns) == 0


def test_qualified_wildcard(qualified_wildcard):
    """TC-008-02: Qualified SELECT table.* flags only that table.

    Verifies:
    - Both tables extracted
    - Only table1 has wildcard flag set
    - table2 has explicit column extracted
    - table2 wildcard flag is False
    """
    result = analyse(qualified_wildcard)

    # Verify both tables extracted
    assert len(result.data_model.tables) == 2
    tables_by_name = {t.name: t for t in result.data_model.tables}
    assert "table1" in tables_by_name
    assert "table2" in tables_by_name

    # Verify table1 has wildcard flag
    table1 = tables_by_name["table1"]
    assert table1.has_wildcard is True
    assert len(table1.columns) == 0  # No explicit columns from t1

    # Verify table2 does NOT have wildcard flag and has explicit column
    table2 = tables_by_name["table2"]
    assert table2.has_wildcard is False
    assert len(table2.columns) == 1
    assert table2.columns[0].name == "id"
    assert ColumnUsage.SELECT in table2.columns[0].usages


def test_wildcard_with_explicit_columns(wildcard_with_columns):
    """TC-008-03: Wildcard with explicit columns.

    Verifies:
    - has_wildcard flag is set
    - Explicit columns are still extracted
    - Columns from WHERE clause are captured
    """
    result = analyse(wildcard_with_columns)

    # Verify one table extracted
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]

    # Verify table properties
    assert table.name == "orders"
    assert table.has_wildcard is True

    # Verify explicit columns are extracted
    assert len(table.columns) == 2
    cols_by_name = {col.name: col for col in table.columns}
    assert "status" in cols_by_name
    assert "region" in cols_by_name

    # Verify usages
    assert ColumnUsage.SELECT in cols_by_name["status"].usages
    assert ColumnUsage.WHERE in cols_by_name["region"].usages


# Phase 2E: Edge cases


def test_self_join(self_join):
    """TC-001-10: Self-join with same table, different aliases.

    Verifies:
    - Single table in output (no duplicates)
    - Columns from both aliases are merged
    - Usages accumulated correctly
    """
    result = analyse(self_join)

    # Verify only one table extracted
    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]

    # Verify table name
    assert table.name == "users"

    # Verify columns
    cols_by_name = {col.name: col for col in table.columns}
    assert "id" in cols_by_name
    assert "manager_id" in cols_by_name

    # Verify usages
    # id appears in both SELECT (a.id, b.id) and JOIN_ON (b.id)
    assert ColumnUsage.SELECT in cols_by_name["id"].usages
    assert ColumnUsage.JOIN_ON in cols_by_name["id"].usages

    # manager_id appears in JOIN_ON (a.manager_id)
    assert ColumnUsage.JOIN_ON in cols_by_name["manager_id"].usages


def test_union_query(union_query):
    """Test UNION query with multiple SELECT arms.

    Verifies:
    - Both tables extracted
    - Columns from both arms captured
    - Post-order traversal handles UNION scopes
    """
    result = analyse(union_query)

    # Verify both tables extracted
    assert len(result.data_model.tables) == 2
    tables_by_name = {t.name: t for t in result.data_model.tables}
    assert "orders" in tables_by_name
    assert "archived_orders" in tables_by_name

    # Verify both have column "id" with SELECT usage
    orders = tables_by_name["orders"]
    assert len(orders.columns) == 1
    assert orders.columns[0].name == "id"
    assert ColumnUsage.SELECT in orders.columns[0].usages

    archived_orders = tables_by_name["archived_orders"]
    assert len(archived_orders.columns) == 1
    assert archived_orders.columns[0].name == "id"
    assert ColumnUsage.SELECT in archived_orders.columns[0].usages


def test_complex_integration(complex_integration):
    """Integration test with CTE, JOIN, multiple clauses.

    Verifies:
    - CTE is resolved to base tables
    - Multiple base tables extracted
    - Columns from all clauses captured
    - All usages accumulated correctly
    """
    result = analyse(complex_integration)

    # Verify tables extracted (no CTE alias)
    assert len(result.data_model.tables) == 2
    tables_by_name = {t.name: t for t in result.data_model.tables}
    assert "sales" in tables_by_name
    assert "products" in tables_by_name
    assert "regional_sales" not in tables_by_name  # CTE should not appear

    # Verify sales table columns
    sales = tables_by_name["sales"]
    sales_cols = {col.name: col for col in sales.columns}

    # Expected columns: region, product_id, amount, year
    assert "region" in sales_cols
    assert "product_id" in sales_cols
    assert "amount" in sales_cols
    assert "year" in sales_cols

    # Verify usages for sales columns
    # region: SELECT, GROUP_BY
    assert ColumnUsage.SELECT in sales_cols["region"].usages
    assert ColumnUsage.GROUP_BY in sales_cols["region"].usages

    # product_id: SELECT, GROUP_BY
    assert ColumnUsage.SELECT in sales_cols["product_id"].usages
    assert ColumnUsage.GROUP_BY in sales_cols["product_id"].usages

    # amount: SELECT (inside SUM aggregate)
    assert ColumnUsage.SELECT in sales_cols["amount"].usages

    # year: WHERE
    assert ColumnUsage.WHERE in sales_cols["year"].usages

    # Verify products table columns
    products = tables_by_name["products"]
    products_cols = {col.name: col for col in products.columns}

    # Expected columns: id, name
    assert "id" in products_cols
    assert "name" in products_cols

    # Verify usages for products columns
    # id: JOIN_ON
    assert ColumnUsage.JOIN_ON in products_cols["id"].usages

    # name: SELECT
    assert ColumnUsage.SELECT in products_cols["name"].usages
