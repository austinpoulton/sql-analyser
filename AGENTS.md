# AI Agent Instructions — SQL Analyser

## Project Overview

SQL Analyser deterministically extracts a source data model from a single SQL statement using sqlglot's AST and scope analysis. It does **not** execute, validate, or optimise SQL.

## Tech Stack

- **Python ≥ 3.12**, managed with **uv**
- **sqlglot** — SQL parsing and AST traversal
- **pydantic** — domain model classes (serialisation, validation)
- **Jinja2** — rendering templates (Mermaid ERD, DBML)
- **pytest** — testing

## Issue management and tracking
This project uses a CLI ticket system for task management. Run `tk help` when you need to use it.

**Important:** After completing a task, always update the corresponding ticket status to `closed` using the `tk` command.

## Feature Specfications
Feature specifications live in features/XX-feature-name/ where XX is increasing numbers like 01, 02. Typically we write a PRD.md (use best practices). After I have reviewed it, I will ask you to break down the PRD into a detailed TODO.md plan in the same directory.  This should contain all the tasks necessary to complete the feature. After creating the TODO, we should also create tickets (`tk --help`) to track the work. Tickets should be as complete as possible, with Acceptance Criteria, and have the dependencies linked.

## Feature Branch Workflow

**Critical:** For each new feature, you MUST:

1. Create a feature branch from `main` using the naming convention `feature/XX-feature-name` (matching the feature directory name)
2. Set up git commit hooks on the feature branch to enforce code quality:
   - Pre-commit hook must run linting checks
   - Pre-commit hook must run all tests (`uv run pytest`)
   - Commits should be blocked if either linting or tests fail
3. Work on all feature implementation in the feature branch
4. Only merge to `main` after all tests pass and the feature is complete


## Module Layout

```
src/sql_analyser/
├── __init__.py          # public API: analyse() + re-exports of domain classes
├── domain.py            # Pydantic domain classes, enums, and merge logic
├── analyser.py          # scope traversal, base table resolution, column extraction,
│                        #   relationship extraction (JOIN + WHERE), type inference
├── lineage.py           # output column lineage tracking
├── metrics.py           # complexity metrics computation
└── templates/           # Jinja2 templates
    ├── mermaid_erd.j2
    └── dbml.j2

tests/
├── conftest.py               # shared fixtures (parsed ASTs for test SQL)
├── test_domain_model.py      # domain classes, serialisation, merge logic (FR-009)
├── test_source_data_model.py  # table/column extraction (FR-001, FR-005, FR-006, FR-008)
├── test_relationships.py      # relationship extraction (FR-002)
├── test_lineage.py            # column lineage (FR-007)
├── test_metrics.py            # complexity metrics (FR-004)
└── test_rendering.py          # Mermaid ERD and DBML output (FR-003)
```

> This is the target layout. Create modules as needed when implementing each feature — do not create empty placeholder files.
>
> **Consolidation rationale:** Merge logic is tightly coupled to domain classes, so `domain.py` co-locates both. Table/column extraction and relationship extraction share the same scope traversal loop and alias resolution, so `analyser.py` handles both.

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

| Phase | Status | FRs | What to Build | Depends On |
|---|---|---|---|---|
| 1 — Domain model | ✅ Complete | FR-009 | `domain.py`: Pydantic classes, enums, JSON serialisation, merge logic | Nothing |
| 2 — Core extraction | ✅ Complete | FR-001, FR-008 | `analyser.py`: scope traversal, base table resolution, column extraction from all clauses, wildcard detection | Phase 1 |
| 3 — Relationships | ✅ Complete | FR-002 | Extend `analyser.py`: JOIN and WHERE implicit join extraction within the scope loop | Phase 2 |
| 4 — Metrics | ✅ Complete | FR-004 | `metrics.py`: AST node count, scope count | Phase 2 |
| 5 — Type inference | Planned | FR-005 | Type inference logic in `analyser.py` | Phase 2 |
| 6 — Classification | Planned | FR-006 | Measure/dimension/attribute classification | Phase 2 |
| 7 — Lineage | Planned | FR-007 | `lineage.py`: output column → source mapping | Phase 2 |
| 8 — Rendering | Planned | FR-003 | `templates/`, rendering methods on DataModel | Phases 2–3 |

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

All classes are Pydantic models defined in `domain.py`, serialisable to/from JSON.

| Class | Key Fields | Notes |
|---|---|---|
| `ColumnUsage` | StrEnum: `SELECT`, `WHERE`, `HAVING`, `ORDER_BY`, `GROUP_BY`, `JOIN_ON` | Tracks which SQL clause a column was referenced in |
| `ColumnClassification` | StrEnum: `MEASURE`, `DIMENSION`, `ATTRIBUTE` | Output column classification |
| `QueriedColumn` | name, data_type (`"varchar"` default), usages (`set[ColumnUsage]`) | |
| `QueriedTable` | name, schema_name, catalog_name, columns, has_wildcard | `qualified_name` property joins non-empty parts with `"."` |
| `Relationship` | left_table, left_columns, right_table, right_columns | `canonical_key` property for symmetric deduplication |
| `DataModel` | tables, relationships | `merge(other)` method for combining models |
| `OutputColumn` | alias, source_table, source_column, transforms, classification | Column lineage tracking |
| `ComplexityMetrics` | node_count, scope_count, scope_types | AST complexity |
| `AnalysisResult` | data_model, output_columns, metrics | Top-level wrapper |

`QueriedTable` stores namespace parts separately (`name`, `schema_name`, `catalog_name`) mirroring sqlglot's `exp.Table` properties (`name`, `db`, `catalog`). The `qualified_name` computed property provides the dotted string (e.g. `"core_facts.orders"`) used for merge matching and Relationship references.

## Testing

```bash
uv run pytest
```

- Each functional requirement (FR-001 – FR-009) must have unit tests. See [SQL-ANALYSER-SPEC.md](SQL-ANALYSER-SPEC.md) §6 and §8 for requirements and test patterns.
- Use **fixtures** in `conftest.py` for shared parsed ASTs — do not repeat SQL parsing in every test.
- Test both the happy path and edge cases (self-joins, `SELECT *`, nested CTEs, correlated subqueries).
- Assert on domain model objects, not string output. Rendering tests are separate.

**Critical:** After completing any implementation task, you MUST run all tests using `uv run pytest`. If test failures occur, you MUST NOT SKIP or ignore them. All test failures must be resolved before considering the task complete.

## Common Pitfalls

- Do not confuse CTE aliases with base tables — always resolve through scope analysis.
- Columns may appear only in `WHERE`, `HAVING`, or `ORDER BY` — they must still be captured in the source model.
- Self-joins: same table appears once in the model; the relationship references the same table on both sides.
- Implicit joins (`FROM a, b WHERE a.id = b.id`) must produce relationships, not just table references.
- When merging, conflicting non-`varchar` types should warn but not fail — prefer the left-hand operand.

## Reference

- Full specification: [SQL-ANALYSER-SPEC.md](SQL-ANALYSER-SPEC.md)
- Domain model & module plan: [docs/DOMAIN-MODEL-PLAN.md](docs/DOMAIN-MODEL-PLAN.md)
- Feature PRDs (when available): `docs/prds/`
