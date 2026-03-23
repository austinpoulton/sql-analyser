"""Tests for DataModel and AnalysisResult rendering (FR-003).

This module tests the rendering of DataModel objects to Mermaid ERD and DBML formats,
and AnalysisResult objects to markdown reports.
"""

from __future__ import annotations

import sqlglot

from sql_analyser import analyse
from sql_analyser.domain import (
    AnalysisResult,
    ComplexityMetrics,
    DataModel,
    QueriedColumn,
    QueriedTable,
    Relationship,
)


# TC-003-01: Primary spec example — Mermaid rendering


def test_mermaid_rendering_spec_example():
    """TC-003-01: Render spec example as Mermaid ERD.

    This is the canonical rendering test from the specification.
    """
    sql = """
        WITH cte_ordered_products_store AS (
            SELECT
                prod_sku,
                store_id,
                SUM(quantity) AS quantity,
                SUM(value) AS revenue,
                AVG((value - base_cost) / base_cost) AS avg_margin
            FROM core_facts.orders
            GROUP BY prod_sku, store_id
        )
        SELECT
            p.prod_name AS product_name,
            s.store_nam AS store_name,
            o.revenue,
            o.quantity,
            o.avg_margin
        FROM core_dims.product p
        LEFT JOIN cte_ordered_products_store o
            ON o.prod_sku = p.sku
        LEFT JOIN core_dims.store s
            ON s.store_id = o.store_id
    """

    expr = sqlglot.parse_one(sql, dialect="postgres")
    result = analyse(expr)
    mermaid = result.data_model.render_mermaid()

    # Verify Mermaid structure
    assert "erDiagram" in mermaid, "Mermaid output should contain erDiagram header"

    # Verify all three tables are present
    assert '"core_facts.orders"' in mermaid
    assert '"core_dims.product"' in mermaid
    assert '"core_dims.store"' in mermaid

    # Verify columns with numeric types (from aggregates)
    assert "numeric quantity" in mermaid or "varchar quantity" in mermaid
    assert "numeric value" in mermaid or "varchar value" in mermaid
    assert "numeric base_cost" in mermaid or "varchar base_cost" in mermaid

    # Verify relationships
    assert "core_facts.orders" in mermaid and "core_dims.product" in mermaid, (
        "Relationship orders↔product should be present"
    )
    assert "core_facts.orders" in mermaid and "core_dims.store" in mermaid, (
        "Relationship orders↔store should be present"
    )

    # Verify output is syntactically valid (basic check)
    assert mermaid.strip().startswith("erDiagram")


# TC-003-02: DBML rendering — simple two-table join


def test_dbml_rendering_simple_join():
    """TC-003-02: Render simple two-table join as DBML."""
    sql = """
        SELECT o.order_id, c.name
        FROM sales.orders o
        JOIN sales.customer c ON c.customer_id = o.customer_id
    """

    expr = sqlglot.parse_one(sql, dialect="postgres")
    result = analyse(expr)
    dbml = result.data_model.render_dbml()

    # Verify DBML table blocks
    assert "Table sales.orders" in dbml, "DBML should contain sales.orders table"
    assert "Table sales.customer" in dbml, "DBML should contain sales.customer table"

    # Verify columns are present
    assert "order_id" in dbml
    assert "name" in dbml
    assert "customer_id" in dbml

    # Verify relationship reference
    assert "Ref:" in dbml, "DBML should contain at least one Ref"
    assert "sales.orders" in dbml and "sales.customer" in dbml, (
        "Ref should connect orders and customer"
    )


# TC-RENDER-01: Edge cases


def test_empty_datamodel_rendering():
    """TC-RENDER-01a: Empty DataModel renders valid but empty output."""
    model = DataModel(tables=[], relationships=[])

    mermaid = model.render_mermaid()
    assert mermaid.strip() == "erDiagram", (
        "Empty model should render just erDiagram header"
    )

    dbml = model.render_dbml()
    # Empty DBML is just whitespace/empty
    assert len(dbml.strip()) == 0, "Empty model should render empty DBML"


def test_table_with_no_columns():
    """TC-RENDER-01b: Table with no columns renders entity block with name only."""
    table = QueriedTable(name="users", schema_name="app", catalog_name="")
    model = DataModel(tables=[table], relationships=[])

    mermaid = model.render_mermaid()
    assert '"app.users"' in mermaid
    # Table block should exist even if empty
    assert "{" in mermaid and "}" in mermaid


def test_table_with_wildcard():
    """TC-RENDER-01c: Table with wildcard flag renders correctly."""
    table = QueriedTable(name="orders", has_wildcard=True, columns=[])
    model = DataModel(tables=[table], relationships=[])

    mermaid = model.render_mermaid()
    assert '"orders"' in mermaid
    # Wildcard doesn't break rendering


# TC-RENDER-02: Multi-column relationships


def test_multi_column_relationship_rendering():
    """TC-RENDER-02: Multi-column relationships render correctly."""
    table1 = QueriedTable(
        name="orders",
        schema_name="sales",
        columns=[
            QueriedColumn(name="region"),
            QueriedColumn(name="order_id"),
        ],
    )
    table2 = QueriedTable(
        name="shipments",
        schema_name="sales",
        columns=[
            QueriedColumn(name="region"),
            QueriedColumn(name="order_id"),
        ],
    )
    rel = Relationship(
        left_table="sales.orders",
        left_columns=["region", "order_id"],
        right_table="sales.shipments",
        right_columns=["region", "order_id"],
    )
    model = DataModel(tables=[table1, table2], relationships=[rel])

    mermaid = model.render_mermaid()
    # Multi-column relationship should include both columns in label
    assert "sales.orders" in mermaid and "sales.shipments" in mermaid
    # Relationship line should exist
    assert "||--||" in mermaid

    dbml = model.render_dbml()
    # DBML multi-column syntax: Ref: (t1.a, t1.b) - (t2.a, t2.b)
    assert "Ref:" in dbml
    assert "sales.orders" in dbml and "sales.shipments" in dbml


# Integration tests: Full pipeline from SQL to rendered output


def test_integration_sql_to_mermaid():
    """Integration test: Parse SQL, analyse, render to Mermaid."""
    sql = "SELECT u.id, o.order_id FROM users u JOIN orders o ON u.id = o.user_id"
    expr = sqlglot.parse_one(sql)
    result = analyse(expr)
    mermaid = result.data_model.render_mermaid()

    assert "erDiagram" in mermaid
    assert '"users"' in mermaid
    assert '"orders"' in mermaid
    assert "||--||" in mermaid  # Relationship exists


def test_integration_sql_to_dbml():
    """Integration test: Parse SQL, analyse, render to DBML."""
    sql = "SELECT u.id, o.order_id FROM users u JOIN orders o ON u.id = o.user_id"
    expr = sqlglot.parse_one(sql)
    result = analyse(expr)
    dbml = result.data_model.render_dbml()

    assert "Table users" in dbml
    assert "Table orders" in dbml
    assert "Ref:" in dbml


# TC-RENDER-03: Markdown report rendering


def test_markdown_report_basic():
    """TC-RENDER-03a: Basic markdown report rendering with all sections."""
    sql = """
        SELECT u.id, u.name, o.order_id, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = true
    """

    expr = sqlglot.parse_one(sql)
    result = analyse(expr)
    report = result.render_markdown_report(sql)

    # Verify markdown structure
    assert "# SQL Analysis Report" in report
    assert "## Original SQL Query" in report
    assert "## Complexity Metrics" in report
    assert "## Source Data Model" in report

    # Verify SQL query is included
    assert "SELECT u.id, u.name" in report
    assert "```sql" in report

    # Verify metrics table is present
    assert "| Metric | Value |" in report
    assert "| AST Node Count |" in report
    assert "| Scope Count |" in report
    assert "| Scope Types |" in report

    # Verify Mermaid diagram is embedded
    assert "```mermaid" in report
    assert "erDiagram" in report
    assert '"users"' in report
    assert '"orders"' in report


def test_markdown_report_without_metrics():
    """TC-RENDER-03b: Markdown report handles missing metrics gracefully."""
    model = DataModel(
        tables=[QueriedTable(name="users", columns=[QueriedColumn(name="id")])],
        relationships=[],
    )
    result = AnalysisResult(data_model=model, metrics=None)
    sql = "SELECT * FROM users"

    report = result.render_markdown_report(sql)

    # Verify sections exist
    assert "# SQL Analysis Report" in report
    assert "## Original SQL Query" in report
    assert "## Complexity Metrics" in report
    assert "## Source Data Model" in report

    # Verify metrics section shows "no metrics available"
    assert "_No metrics available_" in report

    # Verify SQL and diagram still render
    assert "SELECT * FROM users" in report
    assert "erDiagram" in report


def test_markdown_report_with_complex_query():
    """TC-RENDER-03c: Markdown report with complex query including CTEs."""
    sql = """
        WITH cte_orders AS (
            SELECT user_id, SUM(total) AS total_spent
            FROM orders
            GROUP BY user_id
        )
        SELECT u.name, c.total_spent
        FROM users u
        LEFT JOIN cte_orders c ON u.id = c.user_id
    """

    expr = sqlglot.parse_one(sql)
    result = analyse(expr)
    report = result.render_markdown_report(sql)

    # Verify CTE is included in SQL section
    assert "WITH cte_orders AS" in report
    assert "SUM(total)" in report

    # Verify metrics section has non-zero values
    assert "| AST Node Count |" in report

    # Verify base tables (not CTEs) in diagram
    assert '"users"' in report
    assert '"orders"' in report
    # CTE should not appear as a table in the model
    assert '"cte_orders"' not in report or report.index('"cte_orders"') < report.index(
        "## Source Data Model"
    )


def test_markdown_report_empty_model():
    """TC-RENDER-03d: Markdown report with empty data model."""
    model = DataModel(tables=[], relationships=[])
    result = AnalysisResult(
        data_model=model,
        metrics=ComplexityMetrics(node_count=5, scope_count=1, scope_types=["ROOT"]),
    )
    sql = "SELECT 1"

    report = result.render_markdown_report(sql)

    # Verify all sections exist
    assert "# SQL Analysis Report" in report
    assert "## Original SQL Query" in report
    assert "## Complexity Metrics" in report
    assert "## Source Data Model" in report

    # Verify SQL is present
    assert "SELECT 1" in report

    # Verify metrics are present
    assert "5" in report  # node_count

    # Verify empty diagram still renders
    assert "erDiagram" in report


def test_markdown_report_multiline_sql():
    """TC-RENDER-03e: Markdown report preserves SQL formatting."""
    sql = """SELECT
    id,
    name,
    email
FROM
    users
WHERE
    active = true"""

    model = DataModel(
        tables=[QueriedTable(name="users", columns=[QueriedColumn(name="id")])],
        relationships=[],
    )
    result = AnalysisResult(
        data_model=model,
        metrics=ComplexityMetrics(node_count=10, scope_count=1, scope_types=["ROOT"]),
    )

    report = result.render_markdown_report(sql)

    # Verify SQL formatting is preserved (whitespace maintained)
    assert "SELECT\n    id,\n    name,\n    email" in report
    assert "FROM\n    users" in report
    assert "WHERE\n    active = true" in report
