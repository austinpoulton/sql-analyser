# SQL Analyser

> **Status: Early Development** — domain model and core analysis features are being implemented. The API below shows the target interface.

Deterministic source data model extraction from SQL queries.

SQL Analyser parses a SQL statement via [sqlglot](https://github.com/tobymao/sqlglot) and reverse-engineers a structured specification of the query: **source tables and columns**, **relationships**, **output column lineage**, **complexity metrics**, and **measure/dimension classification** — without executing or validating the SQL.

## Key Features

- **Source data model** — base tables and columns resolved from all clauses (`SELECT`, `JOIN`, `WHERE`, `HAVING`, `ORDER BY`, `GROUP BY`); CTEs and subqueries flattened to base tables.
- **Relationships** — extracted from explicit `JOIN` conditions and implicit joins in `WHERE` clauses.
- **Column lineage** — maps each output alias back to its source `table.column` with transformations.
- **Measure / dimension classification** — columns inside aggregates → measure; `GROUP BY` columns → dimension.
- **Complexity metrics** — AST node count, scope count, scope types.
- **Rendering** — Mermaid ERD and DBML output via Jinja2 templates.
- **Model merging** — union multiple `DataModel` instances with type-specificity resolution.

## Example

Given this SQL with a CTE, aggregations, and joins:

```sql
WITH cte_ordered_products_store AS (
    SELECT prod_sku, store_id,
           SUM(quantity) AS quantity, SUM(value) AS revenue,
           AVG((value - base_cost) / base_cost) AS avg_margin
    FROM core_facts.orders
    GROUP BY prod_sku, store_id
)
SELECT p.prod_name AS product_name, s.store_nam AS store_name,
       o.revenue, o.quantity, o.avg_margin
FROM core_dims.product p
LEFT JOIN cte_ordered_products_store o ON o.prod_sku = p.sku
LEFT JOIN core_dims.store s ON s.store_id = o.store_id
```

The SQL Analyser resolves through the CTE to extract the base tables and produces:

```mermaid
erDiagram
    "core_facts.orders" {
        varchar prod_sku
        varchar store_id
        numeric quantity
        numeric value
        numeric base_cost
    }
    "core_dims.product" {
        varchar sku
        varchar prod_name
    }
    "core_dims.store" {
        varchar store_id
        varchar store_nam
    }
    "core_facts.orders" ||--|| "core_dims.product" : "orders.prod_sku = product.sku"
    "core_facts.orders" ||--|| "core_dims.store" : "orders.store_id = store.store_id"
```

## Requirements

- Python ≥ 3.12
- [uv](https://github.com/astral-sh/uv) for dependency management

## Quickstart

```bash
# install dependencies
uv sync

# run tests
uv run pytest
```

## Target API

> This is the planned interface. It may change as features are implemented.

```python
import sqlglot
from sql_analyser import analyse

ast = sqlglot.parse_one(sql, dialect="ansi")
model = analyse(ast)

# Render as Mermaid ERD
print(model.to_mermaid())

# Serialise to JSON
print(model.model_dump_json(indent=2))

# Merge models from multiple queries
combined = model1.merge(model2)
```

## Domain Model

| Class | Purpose |
|---|---|
| `DataModel` | Container for `QueriedTable`s and `Relationship`s. Supports merging. |
| `QueriedTable` | A base table and its observed `QueriedColumn`s. |
| `QueriedColumn` | Column name, inferred data type (default `varchar`), usage context. |
| `Relationship` | Association between two tables on specific columns. |

All classes are Pydantic models, serialisable to/from JSON.

## Using as a Dependency

```bash
# from another project using uv
uv add ../sql-analyser

# or with pip (editable install)
pip install -e /path/to/sql-analyser
```

## Specification

See [SQL-ANALYSER-SPEC.md](SQL-ANALYSER-SPEC.md) for the full functional and technical specification.

## Licence

TBD
