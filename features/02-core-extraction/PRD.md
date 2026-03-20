# PRD: Core Table & Column Extraction (Phase 2)

## Overview

**Feature ID:** 02
**Phase:** 2 — Core extraction
**Dependencies:** Phase 1 (Domain Model)
**Functional Requirements:** FR-001 (Source Data Model Extraction), FR-008 (Wildcard Handling)

## Problem Statement

SQL Analyser needs to extract the complete source data model (tables and columns) from any SQL statement by traversing sqlglot's AST scope hierarchy. This requires:

1. Identifying all **base tables** (physical tables, not CTEs or subqueries) referenced across all scopes
2. Extracting **columns** from every SQL clause (SELECT, WHERE, HAVING, ORDER BY, GROUP BY, JOIN ON)
3. Correctly resolving **table aliases** to their underlying base tables
4. Handling **CTEs and subqueries** by processing inner scopes first (post-order traversal)
5. Detecting **wildcards** (`SELECT *`, `table.*`) without inventing columns

The core extraction engine forms the foundation for all downstream features (relationships, lineage, metrics, rendering).

## Goals

### Primary Goals

1. Implement robust scope traversal that processes innermost scopes (CTEs, subqueries) before outer scopes
2. Build a table registry mapping qualified table names to `QueriedTable` instances
3. Extract columns from all SQL clauses with correct usage classification
4. Resolve table aliases to base tables, including CTE/subquery references
5. Flag wildcard usage without attempting column expansion
6. Produce a complete `DataModel` with tables and columns (relationships handled in Phase 3)

### Non-Goals

- Relationship extraction (deferred to Phase 3)
- Data type inference (deferred to Phase 5)
- Column lineage tracking (deferred to Phase 7)
- SQL validation or execution
- Column expansion for wildcards (we flag, not expand)

## Success Metrics

- All FR-001 test cases (TC-001-01 through TC-001-10) pass
- All FR-008 test cases (TC-008-01 through TC-008-03) pass
- Zero false negatives: every column referenced in the SQL is captured
- Zero false positives: no columns invented or duplicated
- Handles deeply nested CTEs (≥3 levels) correctly

## User Stories

### US-001: Extract tables and columns from a simple SELECT

**As a** data analyst
**I want** to extract the source tables and columns from `SELECT customer_id, order_total FROM orders`
**So that** I can understand which base tables my query reads from

**Acceptance Criteria:**
- DataModel contains one `QueriedTable` named `"orders"`
- Table has two columns: `"customer_id"`, `"order_total"`
- Both columns have usage `{ColumnUsage.SELECT}`
- No relationships (Phase 3)

### US-002: Handle multi-table joins with aliases

**As a** data engineer
**I want** to analyse `SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id`
**So that** I can see which columns are used from each aliased table

**Acceptance Criteria:**
- DataModel contains two tables: `"orders"`, `"customers"`
- `"orders"` has column `"id"` (SELECT usage) and `"customer_id"` (JOIN_ON usage)
- `"customers"` has columns `"id"` (JOIN_ON), `"name"` (SELECT)
- Aliases `o`, `c` are resolved to base tables, not present in output

### US-003: Process CTEs without double-counting columns

**As a** BI developer
**I want** to analyse `WITH tmp AS (SELECT * FROM orders) SELECT order_id FROM tmp`
**So that** the tool correctly identifies `"orders"` as the base table, not `"tmp"`

**Acceptance Criteria:**
- DataModel contains one table: `"orders"`
- Table has column `"order_id"` with SELECT usage
- CTE alias `"tmp"` does not appear as a table in the output
- No duplicate column entries

### US-004: Detect SELECT * as a wildcard flag

**As a** query optimizer
**I want** `SELECT * FROM products` to flag wildcard usage
**So that** I know the query result schema is dynamic

**Acceptance Criteria:**
- DataModel contains one table: `"products"`
- `has_wildcard = True` on the table
- No columns are invented
- Column list may be empty or contain explicitly referenced columns from other clauses

### US-005: Extract columns from WHERE, GROUP BY, HAVING, ORDER BY

**As a** performance analyst
**I want** to see all columns used in filter/grouping/sorting clauses
**So that** I can recommend appropriate indexes

**Acceptance Criteria:**
- `SELECT COUNT(*) FROM sales WHERE region = 'EMEA' GROUP BY product_id HAVING COUNT(*) > 100 ORDER BY product_id`
- Table `"sales"` has columns:
  - `"region"` (WHERE usage)
  - `"product_id"` (GROUP_BY, HAVING, ORDER_BY usages)
- Usages are accumulated (product_id has 3 usage types)

### US-006: Handle schema-qualified and catalog-qualified table names

**As a** database administrator
**I want** `SELECT id FROM my_catalog.core_facts.orders` to preserve namespace parts
**So that** I can distinguish tables with the same name in different schemas

**Acceptance Criteria:**
- `QueriedTable.name = "orders"`
- `QueriedTable.schema_name = "core_facts"`
- `QueriedTable.catalog_name = "my_catalog"`
- `qualified_name = "my_catalog.core_facts.orders"`

### US-007: Process nested subqueries correctly

**As a** SQL developer
**I want** nested subqueries to resolve to their base tables
**So that** the analyser shows the true data sources, not intermediate aliases

**Acceptance Criteria:**
- `SELECT a FROM (SELECT a FROM (SELECT a FROM t1) x) y`
- DataModel contains one table: `"t1"`
- Column `"a"` appears once with SELECT usage
- Subquery aliases `x`, `y` do not appear in output

## Functional Requirements

### FR-001: Source Data Model Extraction

Extract all base tables and their columns from any SQL statement, correctly handling:

- Single-table queries
- Multi-table joins (with and without aliases)
- CTEs (WITH clauses)
- Subqueries (in FROM, WHERE, SELECT)
- UNION/INTERSECT/EXCEPT (multiple scopes)
- Self-joins (same table, different aliases)

**Output:** `DataModel` with `tables` list populated; `relationships` list empty (Phase 3)

### FR-008: Wildcard Handling

Detect `SELECT *` and `table.*` patterns and flag them in `QueriedTable.has_wildcard`. Do **not** invent or expand columns.

**Rules:**
- `SELECT *` → all base tables in that scope have `has_wildcard = True`
- `SELECT t1.*, t2.id` → `t1.has_wildcard = True`, `t2.has_wildcard = False`
- Wildcard flag propagates through merges (OR operation)

## Technical Design

### Architecture

```
analyse(expression: sqlglot.Expression) -> AnalysisResult
    │
    ├─ traverse_scope(expression) → list[Scope]  # post-order: innermost first
    │
    ├─ table_registry: dict[str, QueriedTable]
    ├─ alias_to_qualified: dict[str, str]
    │
    └─ FOR each scope in scopes:
         ├─ Register base tables (skip CTE/subquery sources)
         ├─ Build alias → qualified_name map
         ├─ Extract columns per clause (SELECT, WHERE, etc.)
         ├─ Handle wildcards
         └─ (Relationships deferred to Phase 3)
    │
    └─ DataModel(tables=list(table_registry.values()), relationships=[])
```

### Key Components

#### 1. Scope Traversal (`traverse_scope`)

- Uses `sqlglot.optimizer.scope.traverse_scope(expression)`
- Returns scopes in **post-order** (children before parent)
- Ensures CTE/subquery base tables are registered before outer scope processes them

#### 2. Table Registry

```python
table_registry: dict[str, QueriedTable] = {}
# Key: qualified_name (e.g., "schema.table")
# Value: QueriedTable instance
```

- Single source of truth for all tables
- Prevents duplicates across scopes
- Accumulates columns as we walk clauses

#### 3. Alias Resolution

```python
alias_to_qualified: dict[str, str] = {}
# Per-scope map: alias → qualified_name
```

**Algorithm:**
```python
for alias, source in scope.sources.items():
    if isinstance(source, exp.Table):
        qn = build_qualified_name(source.name, source.db, source.catalog)
        alias_to_qualified[alias] = qn
        if qn not in table_registry:
            table_registry[qn] = QueriedTable(
                name=source.name,
                schema_name=source.db or "",
                catalog_name=source.catalog or ""
            )
    # else: source is a Scope (CTE/subquery) → skip, already processed
```

#### 4. Column Extraction Per Clause

Instead of walking from each column node, iterate each clause type:

```python
clause_map = {
    ColumnUsage.SELECT: scope.expression.expressions,       # SELECT list
    ColumnUsage.WHERE: scope.expression.find(exp.Where),
    ColumnUsage.GROUP_BY: scope.expression.find(exp.Group),
    ColumnUsage.HAVING: scope.expression.find(exp.Having),
    ColumnUsage.ORDER_BY: scope.expression.find(exp.Order),
    ColumnUsage.JOIN_ON: [j.args.get("on") for j in scope.expression.find_all(exp.Join)]
}

for usage, clause_node in clause_map.items():
    if clause_node:
        for column in walk_in_scope(clause_node, exp.Column):
            table_alias = column.table
            column_name = column.name

            # Resolve alias → qualified_name
            qualified_name = resolve_alias(table_alias, scope, alias_to_qualified)
            if qualified_name and qualified_name in table_registry:
                table = table_registry[qualified_name]
                add_or_update_column(table, column_name, usage)
```

**Helper: `resolve_alias(alias, scope, alias_map)`**

- If `alias` in `alias_map` → return `alias_map[alias]`
- If `alias` is empty and scope has exactly one base table → return that table's qualified_name
- If `alias` maps to a Scope source (CTE) → return `None` (skip, handled by child scope)
- Otherwise → return `None` (unresolved)

#### 5. Wildcard Detection

```python
for star in scope.stars:
    if star is qualified (has table reference):
        table_alias = star.table
        qn = resolve_alias(table_alias, scope, alias_to_qualified)
        if qn in table_registry:
            table_registry[qn].has_wildcard = True
    else:  # SELECT *
        for qn in [qn for alias, qn in alias_to_qualified.items()
                   if isinstance(scope.sources[alias], exp.Table)]:
            table_registry[qn].has_wildcard = True
```

### Data Structures

#### QueriedTable

```python
class QueriedTable(BaseModel):
    name: str
    schema_name: str = ""
    catalog_name: str = ""
    columns: list[QueriedColumn] = []
    has_wildcard: bool = False

    @property
    def qualified_name(self) -> str:
        parts = [p for p in [self.catalog_name, self.schema_name, self.name] if p]
        return ".".join(parts)
```

#### QueriedColumn

```python
class QueriedColumn(BaseModel):
    name: str
    data_type: str = "varchar"  # Phase 5 will infer types
    usages: set[ColumnUsage] = Field(default_factory=set)
```

### Edge Cases

| Case | Handling |
|---|---|
| Self-join (`FROM t1 a, t1 b`) | Single `QueriedTable` for `t1`; columns accumulated from both aliases |
| Unqualified column in multi-table scope | Warn and skip if cannot resolve (or use sqlglot's `qualify_columns` optimizer) |
| Nested CTEs (3+ levels) | Post-order traversal handles depth automatically |
| UNION queries | Each SELECT arm is a separate scope; tables registered from all arms |
| Correlated subquery | Outer scope columns may appear in subquery; handled via scope.sources resolution |
| `SELECT *` with explicit columns | Both wildcard flag and explicit columns coexist |

## Implementation Plan

### Phase 2A: Basic Scope Traversal & Table Registry

**Files:**
- `src/sql_analyser/analyser.py` (new)
- `tests/conftest.py` (new — fixtures)
- `tests/test_source_data_model.py` (new)

**Tasks:**
1. Create `analyser.py` with `analyse(expression) -> AnalysisResult` stub
2. Implement `traverse_scope` wrapper (returns sqlglot scopes in post-order)
3. Implement `build_qualified_name(name, schema, catalog) -> str`
4. Implement table registration loop (base tables only)
5. Create `conftest.py` with fixtures for simple SQL (TC-001-01, TC-001-02)
6. Write tests: single-table SELECT, multi-table JOIN

**Acceptance Criteria:**
- TC-001-01 (single table) passes
- TC-001-02 (multi-table join) passes
- Table names and qualified_name are correct

### Phase 2B: Column Extraction from All Clauses

**Tasks:**
1. Implement `clause_map` construction (SELECT, WHERE, GROUP BY, HAVING, ORDER BY, JOIN ON)
2. Implement `walk_in_scope(node, node_type) -> Iterator[Node]` helper
3. Implement `resolve_alias(alias, scope, alias_map) -> str | None`
4. Implement `add_or_update_column(table, column_name, usage)` helper
5. Add fixtures for all clause types (TC-001-03 through TC-001-06)
6. Write tests for each clause type

**Acceptance Criteria:**
- TC-001-03 (WHERE), TC-001-04 (GROUP BY), TC-001-05 (HAVING), TC-001-06 (ORDER BY) pass
- Columns have correct `usages` sets
- No duplicate columns

### Phase 2C: CTE & Subquery Handling

**Tasks:**
1. Implement CTE source detection (skip Scope sources in table registration)
2. Implement alias resolution for CTE references (returns None → column skipped)
3. Add fixtures for CTEs (TC-001-07, TC-001-08) and subqueries (TC-001-09)
4. Write tests for nested CTEs, subqueries in FROM/WHERE

**Acceptance Criteria:**
- TC-001-07 (CTE), TC-001-08 (nested CTE), TC-001-09 (subquery) pass
- CTE aliases do not appear in table list
- Columns are attributed to base tables, not CTEs

### Phase 2D: Wildcard Detection

**Tasks:**
1. Implement wildcard detection loop (qualified `table.*` and unqualified `*`)
2. Add fixtures for wildcard cases (TC-008-01 through TC-008-03)
3. Write tests for `SELECT *`, `SELECT t1.*, t2.id`, wildcard + explicit columns

**Acceptance Criteria:**
- TC-008-01, TC-008-02, TC-008-03 pass
- `has_wildcard` flag is correctly set
- No columns are invented

### Phase 2E: Edge Cases & UNION

**Tasks:**
1. Handle self-joins (TC-001-10)
2. Handle UNION queries (multiple scopes, same depth)
3. Add error handling for unresolved aliases (warn, don't crash)
4. Add logging for debugging scope traversal

**Acceptance Criteria:**
- TC-001-10 (self-join) passes
- UNION queries produce tables from all SELECT arms
- Unresolved columns logged but do not block analysis

## Test Strategy

### Test Pyramid

- **Unit tests** (80%): Individual helper functions (`build_qualified_name`, `resolve_alias`, `add_or_update_column`)
- **Integration tests** (20%): Full `analyse()` call on representative SQL (fixtures in `conftest.py`)

### Coverage Requirements

- All FR-001 test cases (TC-001-01 through TC-001-10)
- All FR-008 test cases (TC-008-01 through TC-008-03)
- Line coverage ≥90% for `analyser.py`

### Test Fixtures (conftest.py)

```python
@pytest.fixture
def simple_select():
    return sqlglot.parse_one("SELECT id FROM users", dialect="postgres")

@pytest.fixture
def multi_table_join():
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
        dialect="postgres"
    )

# ... (fixtures for all TC-001-XX and TC-008-XX cases)
```

### Test Pattern

```python
def test_single_table_select(simple_select):
    result = analyse(simple_select)

    assert len(result.data_model.tables) == 1
    table = result.data_model.tables[0]
    assert table.name == "users"
    assert table.qualified_name == "users"

    assert len(table.columns) == 1
    col = table.columns[0]
    assert col.name == "id"
    assert ColumnUsage.SELECT in col.usages
```

## Dependencies

### Phase 1 (Completed)

- `domain.py` with all Pydantic classes
- `QueriedTable`, `QueriedColumn`, `DataModel`, `AnalysisResult`

### External Libraries

- `sqlglot` ≥25.29.0 — AST parsing and scope traversal
- `pydantic` ≥2.0 — domain model serialisation

## Open Questions

1. **Unqualified columns in multi-table scopes**: Run sqlglot's `qualify_columns` optimizer first, or warn and skip?
   - **Decision needed by:** Phase 2B
   - **Recommendation:** Warn and skip for now; Phase 2E can add `qualify_columns` if needed

2. **Column deduplication within a table**: If the same column appears in multiple clauses, do we union usages or create separate entries?
   - **Decision:** Union usages (single `QueriedColumn` per name per table)

3. **Correlated subquery column attribution**: Outer scope columns referenced in subquery WHERE — attribute to which scope?
   - **Decision:** Attribute to the scope where the column's source table is registered (innermost scope wins)

## Success Criteria

- [ ] All 10 TC-001-XX test cases pass
- [ ] All 3 TC-008-XX test cases pass
- [ ] `analyse()` returns complete `DataModel` with tables and columns
- [ ] No false positives (invented columns)
- [ ] No false negatives (missed columns)
- [ ] Code coverage ≥90% on `analyser.py`
- [ ] Public API in `src/sql_analyser/__init__.py` exports `analyse()` and domain classes

## Out of Scope (Future Phases)

- Relationship extraction → Phase 3
- Data type inference → Phase 5
- Column classification (measure/dimension) → Phase 6
- Output column lineage → Phase 7
- Complexity metrics → Phase 4
- Mermaid ERD rendering → Phase 8

## References

- [SQL-ANALYSER-SPEC.md](../../SQL-ANALYSER-SPEC.md) — §3.1 (FR-001), §3.8 (FR-008), §6 (Test Cases)
- [docs/DOMAIN-MODEL-PLAN.md](../../docs/DOMAIN-MODEL-PLAN.md) — §5 (Analysis Processing Sequence), §6.2 (Phase 2)
- sqlglot documentation: [Scope Traversal](https://sqlglot.com/sqlglot/optimizer/scope.html)
