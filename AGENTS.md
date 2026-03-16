# AI Agent Instructions — SQL Analyser

## Project Overview

SQL Analyser deterministically extracts a source data model from a single SQL statement using sqlglot's AST and scope analysis. It does **not** execute, validate, or optimise SQL.

## Tech Stack

- **Python ≥ 3.12**, managed with **uv**
- **sqlglot** — SQL parsing and AST traversal
- **pydantic** — domain model classes (serialisation, validation)
- **Jinja2** — rendering templates (Mermaid ERD, DBML)
- **pytest** — testing

## Module Layout

```
src/sql_analyser/
├── __init__.py          # public API: analyse() entry point
├── models.py            # Pydantic domain classes: DataModel, QueriedTable, QueriedColumn, Relationship
├── analyser.py          # core analysis: scope traversal, table/column extraction, type inference
├── relationships.py     # relationship extraction from JOIN and WHERE conditions
├── lineage.py           # output column lineage tracking
├── metrics.py           # complexity metrics computation
├── merge.py             # DataModel and QueriedTable merging logic
└── templates/           # Jinja2 templates
    ├── mermaid_erd.j2
    └── dbml.j2

tests/
├── conftest.py          # shared fixtures (parsed ASTs for test SQL)
├── test_models.py       # domain model serialisation, merge rules
├── test_analyser.py     # core extraction (FR-001, FR-005, FR-006, FR-008)
├── test_relationships.py # relationship extraction (FR-002)
├── test_lineage.py      # column lineage (FR-007)
├── test_metrics.py      # complexity metrics (FR-004)
├── test_merge.py        # model merging (FR-009)
└── test_rendering.py    # Mermaid ERD and DBML output (FR-003)
```

> This is the target layout. Create modules as needed when implementing each feature — do not create empty placeholder files.

## Analysis Pipeline

The analyser processes a `sqlglot.Expression` through these stages:

```
sqlglot.Expression (input)
        │
        ▼
┌─────────────────────┐
│  traverse_scope()   │  Enumerate all scopes (root, CTEs, subqueries, unions)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Resolve base tables│  Walk scopes; resolve CTE/subquery aliases to physical tables
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Extract columns    │  For each base table, collect columns from all clauses
└────────┬────────────┘  (SELECT, WHERE, HAVING, ORDER BY, GROUP BY, JOIN ON)
         │
         ▼
┌─────────────────────┐
│  Infer data types   │  Apply heuristics: aggregates→numeric, CAST→target type,
└────────┬────────────┘  else→varchar
         │
         ▼
┌───────────────────────┐
│  Extract relationships│  From explicit JOINs and implicit WHERE equi-joins
└────────┬──────────────┘
         │
         ▼
┌──────────────────────┐
│  Build output lineage│  Map each SELECT alias to source table.column + transforms
└────────┬─────────────┘
         │
         ▼
┌─────────────────────┐
│  Compute metrics    │  AST node count, scope count/types
└────────┬────────────┘
         │
         ▼
     DataModel (output)
```

## Implementation Sequence

Features have dependencies. Implement in this order:

| Phase | FRs | What to Build | Depends On |
|---|---|---|---|
| 1 — Domain model | — | `models.py`: Pydantic classes, JSON serialisation, `__eq__`/`__hash__` | Nothing |
| 2 — Core extraction | FR-001 | `analyser.py`: scope traversal, base table resolution, column extraction from all clauses | Phase 1 |
| 3 — Relationships | FR-002 | `relationships.py`: JOIN and WHERE implicit join extraction | Phase 2 |
| 4 — Rendering | FR-003 | `templates/`, rendering methods on DataModel | Phases 2–3 |
| 5 — Metrics | FR-004 | `metrics.py`: AST node count, scope count | Phase 2 |
| 6 — Type inference | FR-005 | Type inference logic in `analyser.py` | Phase 2 |
| 7 — Classification | FR-006 | Measure/dimension/attribute classification | Phase 2 |
| 8 — Lineage | FR-007 | `lineage.py`: output column → source mapping | Phase 2 |
| 9 — Wildcards | FR-008 | `SELECT *` detection and flagging | Phase 2 |
| 10 — Merging | FR-009 | `merge.py`: DataModel and QueriedTable merging | Phase 1 |

Individual features will have PRD documents in a `docs/prds/` directory. When a PRD exists for a feature, treat it as the source of truth over the spec for that feature's details.

## Key Conventions

- Input is always a `sqlglot.Expression` (pre-parsed AST). Dialect handling is the caller's responsibility.
- CTEs and subqueries are resolved to **base tables**; the domain model never contains CTE aliases.
- Default inferred data type is `varchar`. Columns inside aggregate functions are typed `numeric` when inferable. Explicit `CAST` expressions are honoured.
- `SELECT *` is flagged as an unresolved wildcard — never invent columns.
- Merging two `DataModel` instances: union of tables and relationships; columns matched by name with type-specificity resolution (non-`varchar` wins over `varchar`).

## Coding Style

- **Type hints** on all function signatures and return types. Use `list[X]` not `List[X]`.
- **Docstrings** on all public classes and functions (Google style).
- **Imports**: stdlib → third-party → local, separated by blank lines. Use `from __future__ import annotations` at the top of each module.
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes. No abbreviations in public API names.
- **No star imports** (`from x import *`).
- **Keep modules focused**: one responsibility per module, aligned with the module layout above.

## Domain Model

| Class | Key Fields |
|---|---|
| `DataModel` | tables, relationships |
| `QueriedTable` | name (fully-qualified), columns, has_wildcard |
| `QueriedColumn` | name, data_type, usage context |
| `Relationship` | left table+columns, right table+columns |

All classes are Pydantic models, serialisable to/from JSON.

## Testing

```bash
uv run pytest
```

- Each functional requirement (FR-001 – FR-009) must have unit tests. See [SQL-ANALYSER-SPEC.md](SQL-ANALYSER-SPEC.md) §6 and §8 for requirements and test patterns.
- Use **fixtures** in `conftest.py` for shared parsed ASTs — do not repeat SQL parsing in every test.
- Test both the happy path and edge cases (self-joins, `SELECT *`, nested CTEs, correlated subqueries).
- Assert on domain model objects, not string output. Rendering tests are separate.

## Common Pitfalls

- Do not confuse CTE aliases with base tables — always resolve through scope analysis.
- Columns may appear only in `WHERE`, `HAVING`, or `ORDER BY` — they must still be captured in the source model.
- Self-joins: same table appears once in the model; the relationship references the same table on both sides.
- Implicit joins (`FROM a, b WHERE a.id = b.id`) must produce relationships, not just table references.
- When merging, conflicting non-`varchar` types should warn but not fail — prefer the left-hand operand.

## Reference

- Full specification: [SQL-ANALYSER-SPEC.md](SQL-ANALYSER-SPEC.md)
- Feature PRDs (when available): `docs/prds/`
