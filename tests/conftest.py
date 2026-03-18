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
