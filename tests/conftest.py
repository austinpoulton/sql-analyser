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
