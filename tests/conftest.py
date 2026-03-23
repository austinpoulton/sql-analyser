"""Shared test fixtures for SQL Analyser tests.

This module provides pytest fixtures with pre-parsed SQL expressions for use
across all test modules. Fixtures are organized by test case and SQL complexity.
"""

from __future__ import annotations

import pytest
import sqlglot


# Phase 2A: Basic single-table and multi-table queries


@pytest.fixture
def simple_select():
    """TC-001-01: Single table SELECT.

    SQL: SELECT id FROM users
    """
    return sqlglot.parse_one("SELECT id FROM users", dialect="postgres")


@pytest.fixture
def multi_table_join():
    """TC-001-02: Multi-table join with aliases.

    SQL: SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id
    """
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
        dialect="postgres",
    )


# Phase 2B: Additional clause types


@pytest.fixture
def where_clause():
    """TC-001-03: WHERE clause column extraction.

    SQL: SELECT id FROM orders WHERE region = 'EMEA'
    """
    return sqlglot.parse_one(
        "SELECT id FROM orders WHERE region = 'EMEA'", dialect="postgres"
    )


@pytest.fixture
def group_by_clause():
    """TC-001-04: GROUP BY clause column extraction.

    SQL: SELECT product_id, COUNT(*) FROM sales GROUP BY product_id
    """
    return sqlglot.parse_one(
        "SELECT product_id, COUNT(*) FROM sales GROUP BY product_id",
        dialect="postgres",
    )


@pytest.fixture
def having_clause():
    """TC-001-05: HAVING clause column extraction.

    SQL: SELECT product_id, COUNT(*) FROM sales GROUP BY product_id HAVING COUNT(*) > 100
    """
    return sqlglot.parse_one(
        "SELECT product_id, COUNT(*) FROM sales GROUP BY product_id HAVING COUNT(*) > 100",
        dialect="postgres",
    )


@pytest.fixture
def order_by_clause():
    """TC-001-06: ORDER BY clause column extraction.

    SQL: SELECT id, name FROM products ORDER BY name, id
    """
    return sqlglot.parse_one(
        "SELECT id, name FROM products ORDER BY name, id", dialect="postgres"
    )


@pytest.fixture
def multiple_usages():
    """Multiple usages: Column appears in multiple clauses.

    SQL: SELECT product_id, COUNT(*) FROM sales WHERE region = 'EMEA'
         GROUP BY product_id HAVING COUNT(*) > 100 ORDER BY product_id
    """
    return sqlglot.parse_one(
        "SELECT product_id, COUNT(*) FROM sales WHERE region = 'EMEA' "
        "GROUP BY product_id HAVING COUNT(*) > 100 ORDER BY product_id",
        dialect="postgres",
    )


# Phase 2C: CTE and Subquery handling


@pytest.fixture
def simple_cte():
    """TC-001-07: Simple CTE.

    SQL: WITH tmp AS (SELECT order_id FROM orders) SELECT order_id FROM tmp
    """
    return sqlglot.parse_one(
        "WITH tmp AS (SELECT order_id FROM orders) SELECT order_id FROM tmp",
        dialect="postgres",
    )


@pytest.fixture
def nested_cte():
    """TC-001-08: Nested CTEs (3 levels).

    SQL: WITH cte1 AS (SELECT id FROM users),
              cte2 AS (SELECT id FROM cte1 WHERE id > 10),
              cte3 AS (SELECT id FROM cte2)
         SELECT id FROM cte3
    """
    return sqlglot.parse_one(
        "WITH cte1 AS (SELECT id FROM users), "
        "cte2 AS (SELECT id FROM cte1 WHERE id > 10), "
        "cte3 AS (SELECT id FROM cte2) "
        "SELECT id FROM cte3",
        dialect="postgres",
    )


@pytest.fixture
def nested_subquery():
    """TC-001-09: Nested subquery in FROM clause.

    SQL: SELECT a FROM (SELECT a FROM (SELECT a FROM t1) x) y
    """
    return sqlglot.parse_one(
        "SELECT a FROM (SELECT a FROM (SELECT a FROM t1) x) y", dialect="postgres"
    )


@pytest.fixture
def correlated_subquery():
    """Correlated subquery: Subquery referencing outer scope column.

    SQL: SELECT o.id FROM orders o
         WHERE EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id)
    """
    return sqlglot.parse_one(
        "SELECT o.id FROM orders o "
        "WHERE EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id)",
        dialect="postgres",
    )


# Phase 2D: Wildcard detection


@pytest.fixture
def unqualified_wildcard():
    """TC-008-01: Unqualified SELECT *.

    SQL: SELECT * FROM products
    """
    return sqlglot.parse_one("SELECT * FROM products", dialect="postgres")


@pytest.fixture
def qualified_wildcard():
    """TC-008-02: Qualified SELECT table.*.

    SQL: SELECT t1.*, t2.id FROM table1 t1, table2 t2
    """
    return sqlglot.parse_one(
        "SELECT t1.*, t2.id FROM table1 t1, table2 t2", dialect="postgres"
    )


@pytest.fixture
def wildcard_with_columns():
    """TC-008-03: Wildcard with explicit columns.

    SQL: SELECT *, status FROM orders WHERE region = 'US'
    """
    return sqlglot.parse_one(
        "SELECT *, status FROM orders WHERE region = 'US'", dialect="postgres"
    )


# Phase 2E: Edge cases


@pytest.fixture
def self_join():
    """TC-001-10: Self-join with same table, different aliases.

    SQL: SELECT a.id, b.id FROM users a JOIN users b ON a.manager_id = b.id
    """
    return sqlglot.parse_one(
        "SELECT a.id, b.id FROM users a JOIN users b ON a.manager_id = b.id",
        dialect="postgres",
    )


@pytest.fixture
def union_query():
    """UNION query with multiple SELECT arms.

    SQL: SELECT id FROM orders UNION SELECT id FROM archived_orders
    """
    return sqlglot.parse_one(
        "SELECT id FROM orders UNION SELECT id FROM archived_orders",
        dialect="postgres",
    )


@pytest.fixture
def complex_integration():
    """Complex integration test combining multiple features.

    SQL: WITH regional_sales AS (
           SELECT region, product_id, SUM(amount) as total
           FROM sales
           WHERE year = 2023
           GROUP BY region, product_id
         )
         SELECT rs.region, p.name, rs.total
         FROM regional_sales rs
         JOIN products p ON rs.product_id = p.id
         WHERE rs.total > 1000
         ORDER BY rs.total DESC
    """
    return sqlglot.parse_one(
        """
        WITH regional_sales AS (
          SELECT region, product_id, SUM(amount) as total
          FROM sales
          WHERE year = 2023
          GROUP BY region, product_id
        )
        SELECT rs.region, p.name, rs.total
        FROM regional_sales rs
        JOIN products p ON rs.product_id = p.id
        WHERE rs.total > 1000
        ORDER BY rs.total DESC
        """,
        dialect="postgres",
    )


# Phase 3: Relationship extraction fixtures


@pytest.fixture
def single_column_join():
    """TC-002-01: Single-column explicit JOIN.

    SQL: SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id
    """
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
        dialect="postgres",
    )


@pytest.fixture
def multi_column_join():
    """TC-002-02: Multi-column JOIN.

    SQL: SELECT * FROM orders o
         JOIN shipments s ON o.region = s.region AND o.order_id = s.order_id
    """
    return sqlglot.parse_one(
        "SELECT * FROM orders o "
        "JOIN shipments s ON o.region = s.region AND o.order_id = s.order_id",
        dialect="postgres",
    )


@pytest.fixture
def implicit_where_join():
    """TC-002-03: Implicit WHERE join.

    SQL: SELECT o.id, c.name FROM orders o, customers c WHERE o.customer_id = c.id
    """
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o, customers c WHERE o.customer_id = c.id",
        dialect="postgres",
    )


@pytest.fixture
def multiple_joins():
    """TC-002-04: Multiple JOINs (chain).

    SQL: SELECT o.id, c.name, p.name FROM orders o
         JOIN customers c ON o.customer_id = c.id
         JOIN products p ON o.product_id = p.id
    """
    return sqlglot.parse_one(
        "SELECT o.id, c.name, p.name FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN products p ON o.product_id = p.id",
        dialect="postgres",
    )


@pytest.fixture
def union_with_duplicate_join():
    """TC-002-07: Relationship deduplication.

    SQL: SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id
         UNION
         SELECT * FROM orders o2 JOIN customers c2 ON o2.customer_id = c2.id
    """
    return sqlglot.parse_one(
        "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id "
        "UNION "
        "SELECT * FROM orders o2 JOIN customers c2 ON o2.customer_id = c2.id",
        dialect="postgres",
    )


@pytest.fixture
def cte_join():
    """TC-002-05: CTE JOIN with resolution to base table.

    SQL: WITH tmp AS (SELECT order_id, total FROM orders)
         SELECT t.order_id, p.name
         FROM tmp t
         JOIN products p ON t.order_id = p.order_id
    """
    return sqlglot.parse_one(
        """
        WITH tmp AS (SELECT order_id, total FROM orders)
        SELECT t.order_id, p.name
        FROM tmp t
        JOIN products p ON t.order_id = p.order_id
        """,
        dialect="postgres",
    )


# Phase 4: Complexity metrics fixtures


@pytest.fixture
def simple_query_ast():
    """TC-004-01: Simple query AST for baseline metrics.

    SQL: SELECT id, name FROM app.users WHERE active = 1
    """
    return sqlglot.parse_one(
        "SELECT id, name FROM app.users WHERE active = 1", dialect="postgres"
    )


@pytest.fixture
def cte_query_ast():
    """TC-004-02: CTE query AST for scope count validation.

    SQL: WITH cte AS (SELECT id FROM app.users) SELECT id FROM cte
    """
    return sqlglot.parse_one(
        "WITH cte AS (SELECT id FROM app.users) SELECT id FROM cte",
        dialect="postgres",
    )


@pytest.fixture
def nested_cte_subquery_ast():
    """TC-004-03: Nested CTEs with correlated subquery.

    SQL: WITH base AS (SELECT id FROM app.users),
              enriched AS (
                  SELECT b.id,
                         (SELECT MAX(score) FROM app.scores s WHERE s.user_id = b.id) AS top_score
                  FROM base b
              )
         SELECT id, top_score FROM enriched
    """
    return sqlglot.parse_one(
        """
        WITH base AS (
            SELECT id FROM app.users
        ),
        enriched AS (
            SELECT b.id, (SELECT MAX(score) FROM app.scores s WHERE s.user_id = b.id) AS top_score
            FROM base b
        )
        SELECT id, top_score FROM enriched
        """,
        dialect="postgres",
    )


@pytest.fixture
def union_query_ast():
    """TC-004-04: UNION ALL query for scope count validation.

    SQL: SELECT id FROM app.table_a UNION ALL SELECT id FROM app.table_b
    """
    return sqlglot.parse_one(
        "SELECT id FROM app.table_a UNION ALL SELECT id FROM app.table_b",
        dialect="postgres",
    )
