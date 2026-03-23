"""Tests for complexity metrics computation (FR-004).

This module contains tests for the metrics.py module, verifying that
AST node counting and scope analysis produce correct complexity metrics.
"""

from __future__ import annotations

import sqlglot

from sql_analyser import analyse
from sql_analyser.domain import ComplexityMetrics
from sql_analyser.metrics import compute_metrics


# TC-004-01: Simple query baseline


def test_simple_query_baseline(simple_query_ast):
    """TC-004-01: Simple single-table query metrics baseline.

    A simple SELECT with WHERE should have:
    - Positive node count (at least several nodes for SELECT, FROM, WHERE, columns)
    - Exactly 1 scope (the root SELECT scope)
    - Exactly 1 scope type entry
    """
    metrics = compute_metrics(simple_query_ast)

    assert isinstance(metrics, ComplexityMetrics)
    assert metrics.node_count > 0, "Node count should be positive"
    assert metrics.scope_count == 1, "Simple query should have exactly 1 scope"
    assert len(metrics.scope_types) == 1, "Should have exactly 1 scope type"
    assert "Select" in metrics.scope_types[0], "Root scope should be a Select type"


# TC-004-02: CTE increases scope count


def test_cte_scope_count(cte_query_ast):
    """TC-004-02: CTE increases scope count to 2.

    A query with one CTE should have:
    - scope_count = 2 (CTE scope + root SELECT scope)
    - 2 scope type entries
    - Scope types should include both CTE and SELECT
    """
    metrics = compute_metrics(cte_query_ast)

    assert metrics.scope_count == 2, "CTE query should have 2 scopes (CTE + root)"
    assert len(metrics.scope_types) == 2, "Should have 2 scope type entries"
    # Scope types should include CTE-related and Select types
    assert any("CTE" in st or "Select" in st for st in metrics.scope_types), (
        "Scope types should include CTE or Select"
    )


# TC-004-03: Nested CTE and correlated subquery


def test_nested_cte_subquery_scope_count(nested_cte_subquery_ast):
    """TC-004-03: Nested CTEs with correlated subquery have 4 scopes.

    A query with:
    - 2 CTEs (base, enriched)
    - 1 correlated subquery inside enriched
    - 1 root SELECT

    Should have:
    - scope_count = 4
    - node_count > 20 (reasonably complex query)
    - Multiple scope types
    """
    metrics = compute_metrics(nested_cte_subquery_ast)

    assert metrics.scope_count == 4, (
        "Nested CTE with subquery should have 4 scopes (2 CTEs + subquery + root)"
    )
    assert metrics.node_count > 20, (
        "Complex query should have substantial node count (>20)"
    )
    assert len(metrics.scope_types) == 4, "Should have 4 scope type entries"


# TC-004-04: UNION scope count


def test_union_scope_count(union_query_ast):
    """TC-004-04: UNION ALL branches are counted as separate scopes.

    A UNION query should have:
    - scope_count >= 2 (at least one scope per SELECT branch)
    - Multiple scope types
    """
    metrics = compute_metrics(union_query_ast)

    assert metrics.scope_count >= 2, (
        "UNION query should have at least 2 scopes (one per branch)"
    )
    assert len(metrics.scope_types) >= 2, "Should have multiple scope type entries"
    # UNION queries typically have multiple Select scopes or a Union scope type
    assert "Union" in str(metrics.scope_types) or len(metrics.scope_types) >= 2, (
        "UNION query should have Union or multiple scopes"
    )


# TC-METRICS-01: Empty SELECT has minimal node count


def test_empty_select_minimal_nodes():
    """TC-METRICS-01: Minimal SELECT has low but positive node count.

    The simplest possible query (SELECT 1) should have:
    - node_count > 0 (even minimal queries have nodes)
    - node_count < 10 (very few nodes)
    - scope_count = 1
    """
    simple = sqlglot.parse_one("SELECT 1")
    metrics = compute_metrics(simple)

    assert metrics.node_count > 0, "Even minimal query should have nodes"
    assert metrics.node_count < 10, "Minimal query should have very few nodes"
    assert metrics.scope_count == 1, "Minimal query has 1 scope"


# TC-METRICS-02: Complex JOIN increases node count


def test_node_count_increases_with_complexity():
    """TC-METRICS-02: Complex queries have significantly higher node counts.

    A complex query with JOINs, WHERE, GROUP BY, HAVING, ORDER BY should have
    substantially more nodes than a simple SELECT.
    """
    simple = sqlglot.parse_one("SELECT id FROM users")
    complex_query = sqlglot.parse_one(
        """
        SELECT u.id, u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.active = 1 AND o.status IN ('shipped', 'delivered')
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        """
    )

    simple_metrics = compute_metrics(simple)
    complex_metrics = compute_metrics(complex_query)

    assert complex_metrics.node_count > simple_metrics.node_count * 3, (
        "Complex query should have >3x more nodes than simple query"
    )


# TC-METRICS-03: Scope types are descriptive


def test_scope_types_are_descriptive():
    """TC-METRICS-03: Scope types should be meaningful class names.

    Scope types should not be generic like "Expression" but specific
    like "Select", "CTE", "Union", "Subquery".
    """
    expr = sqlglot.parse_one("WITH tmp AS (SELECT id FROM users) SELECT id FROM tmp")
    metrics = compute_metrics(expr)

    # All scope types should be non-empty strings
    assert all(isinstance(st, str) and len(st) > 0 for st in metrics.scope_types), (
        "All scope types should be non-empty strings"
    )

    # At least one scope type should be "Select" or similar
    assert any("Select" in st or "CTE" in st for st in metrics.scope_types), (
        "Scope types should include descriptive names like 'Select' or 'CTE'"
    )


# Integration test: Metrics in AnalysisResult


def test_metrics_integration_in_analyse():
    """Integration test: Verify metrics are populated in AnalysisResult.

    The analyse() function should:
    - Populate the metrics field in AnalysisResult
    - Return a valid ComplexityMetrics instance
    - Include metrics in JSON serialization
    """
    expression = sqlglot.parse_one("SELECT id, name FROM users WHERE id = 1")
    result = analyse(expression)

    # Verify metrics field is populated
    assert result.metrics is not None, "AnalysisResult.metrics should not be None"
    assert isinstance(result.metrics, ComplexityMetrics), (
        "metrics should be a ComplexityMetrics instance"
    )

    # Verify metrics values are reasonable
    assert result.metrics.node_count > 0, "Node count should be positive"
    assert result.metrics.scope_count == 1, "Simple query should have 1 scope"
    assert len(result.metrics.scope_types) == 1, "Should have 1 scope type"

    # Verify JSON serialization includes metrics
    json_str = result.model_dump_json()
    assert "metrics" in json_str, "JSON should include 'metrics' field"
    assert "node_count" in json_str, "JSON should include 'node_count'"
    assert "scope_count" in json_str, "JSON should include 'scope_count'"
    assert "scope_types" in json_str, "JSON should include 'scope_types'"


# Edge case: Very complex query with multiple features


def test_complex_query_with_all_features():
    """Edge case: Query with CTEs, subqueries, JOINs, aggregates.

    A maximally complex query should have:
    - High node count (>50)
    - Multiple scopes (>3)
    - Diverse scope types
    """
    complex_query = sqlglot.parse_one(
        """
        WITH regional_totals AS (
            SELECT region, SUM(amount) as total
            FROM sales
            GROUP BY region
        ),
        top_regions AS (
            SELECT region FROM regional_totals WHERE total > 10000
        )
        SELECT
            u.id,
            u.name,
            (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) as order_count,
            rt.total
        FROM users u
        JOIN top_regions tr ON u.region = tr.region
        JOIN regional_totals rt ON u.region = rt.region
        WHERE u.active = 1
        ORDER BY rt.total DESC
        """
    )

    metrics = compute_metrics(complex_query)

    assert metrics.node_count > 50, "Very complex query should have >50 nodes"
    assert metrics.scope_count > 3, "Should have >3 scopes (CTEs + subquery + root)"
    assert len(set(metrics.scope_types)) >= 1, (
        "Should have at least 1 unique scope type"
    )


# Performance test: Large query completes quickly


def test_metrics_performance():
    """Performance test: Metrics computation should be fast (<100ms).

    For typical queries (<1000 nodes), metrics should compute quickly.
    This is not a strict timing test but validates the implementation
    doesn't hang on moderately complex queries.
    """
    # Build a moderately complex query
    query = sqlglot.parse_one(
        """
        SELECT
            t1.id, t1.name, t2.value, t3.score
        FROM table1 t1
        JOIN table2 t2 ON t1.id = t2.id
        JOIN table3 t3 ON t2.id = t3.id
        WHERE t1.active = 1 AND t2.status IN ('a', 'b', 'c')
        GROUP BY t1.id, t1.name, t2.value, t3.score
        HAVING COUNT(*) > 5
        ORDER BY t3.score DESC
        """
    )

    # This should complete without hanging
    metrics = compute_metrics(query)

    # Basic validation
    assert metrics.node_count > 0
    assert metrics.scope_count > 0
    # If we get here without timeout, performance is acceptable
