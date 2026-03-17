# Plan: Revised Module Structure & Domain Model

## TL;DR

Revise the SQL Analyser's module layout, domain model attributes, and analysis processing sequence. Consolidate `models.py` + `merge.py` into `domain.py`; combine `analyser.py` + `relationships.py` into a single `analyser.py`. Restructure QueriedTable with separate namespace parts (`name`, `schema_name`, `catalog_name`) plus a computed `qualified_name`. Define the analysis processing algorithm that traverses scopes, builds a table registry, extracts columns per clause, resolves CTE/subquery aliases, and composes the DataModel.

---

## Module Layout (Revised)

```
src/sql_analyser/
├── __init__.py          # public API: analyse() + re-exports of domain classes
├── domain.py            # All Pydantic domain classes + enums + merge logic
├── analyser.py          # Scope traversal, base table resolution, column extraction,
│                        #   relationship extraction (JOIN + WHERE), type inference
├── lineage.py           # Output column lineage tracking (later)
├── metrics.py           # Complexity metrics computation (later)
└── templates/           # Jinja2 templates (later)
    ├── mermaid_erd.j2
    └── dbml.j2

tests/
├── conftest.py              # Shared fixtures: parsed ASTs for test SQL
├── test_domain_model.py     # Domain classes, serialisation round-trip, merge logic
├── test_source_data_model.py # FR-001: table/column extraction across all clause types
├── test_relationships.py     # FR-002: explicit JOIN + implicit WHERE relationships
├── test_metrics.py           # FR-004: AST node count, scope count
├── test_lineage.py           # FR-007 (later)
└── test_rendering.py         # FR-003 (later)
```

### Rationale for consolidation
- **domain.py**: Merge logic operates on domain classes and is tightly coupled. At this stage there's no benefit to a separate `merge.py`. Can split later if the file grows.
- **analyser.py**: Table/column extraction and relationship extraction share the same scope traversal loop, alias resolution, and scope-to-base-table mapping. Combining avoids duplicating the scope-walking infrastructure.

### What changed vs AGENTS.md
- `models.py` → `domain.py` (renamed + absorbs merge logic)
- `merge.py` → absorbed into `domain.py`
- `relationships.py` → absorbed into `analyser.py`
- Test modules renamed: `test_models.py` → `test_domain_model.py`, `test_merge.py` → absorbed into `test_domain_model.py`, `test_analyser.py` → split into `test_source_data_model.py` + `test_relationships.py`

---

## Domain Model Classes

### Enums

```python
class ColumnUsage(StrEnum):
    SELECT = "select"
    WHERE = "where"
    HAVING = "having"
    ORDER_BY = "order_by"
    GROUP_BY = "group_by"
    JOIN_ON = "join_on"

class ColumnClassification(StrEnum):
    MEASURE = "measure"
    DIMENSION = "dimension"
    ATTRIBUTE = "attribute"
```

### QueriedColumn

```
Fields:
  name: str                        # bare column name (e.g., "customer_id")
  data_type: str = "varchar"       # inferred type; default varchar
  usages: set[ColumnUsage] = {}    # which clauses the column was referenced in
```

No change from previous design except usages serialises as JSON array of strings via StrEnum.

### QueriedTable (revised — structured namespace)

```
Fields:
  name: str              # bare table name (e.g., "orders")
  schema_name: str = ""  # schema/database (e.g., "core_facts")
  catalog_name: str = "" # catalog (e.g., "my_catalog")
  columns: list[QueriedColumn] = []
  has_wildcard: bool = False

Computed property:
  qualified_name → str
    Joins non-empty parts [catalog_name, schema_name, name] with ".".
    e.g., "core_facts.orders", "my_catalog.core_facts.orders", or "orders"
```

**Design rationale**: sqlglot's `exp.Table` provides `name`, `db`, `catalog` as separate identifiers. Storing parts separately:
- Preserves the original AST structure without lossy concatenation
- Enables future features (e.g., catalog-level filtering, schema normalisation)
- `qualified_name` computed property provides the dotted string for display, merge matching, and Relationship references

**Merge matching**: Two QueriedTables are mergeable when `qualified_name` matches (all parts must agree).

### Relationship (unchanged)

```
Fields:
  left_table: str          # qualified_name of left table
  left_columns: list[str]  # column names on left side
  right_table: str         # qualified_name of right table
  right_columns: list[str] # column names on right side

Property:
  canonical_key → tuple
    Normalised for symmetric deduplication:
    tuple(sorted([(left_table, tuple(sorted(left_columns))),
                  (right_table, tuple(sorted(right_columns)))]))
```

Table references use `qualified_name` strings, keeping Relationship serialisation-friendly and decoupled from QueriedTable instances.

### DataModel

```
Fields:
  tables: list[QueriedTable] = []
  relationships: list[Relationship] = []

Method:
  merge(other: DataModel) -> DataModel
    Delegates to merge_models() in the same module.
```

### OutputColumn

```
Fields:
  alias: str                                          # output column alias
  source_table: str | None = None                     # qualified_name
  source_column: str | None = None                    # bare column name
  transforms: list[str] = []                          # e.g., ["SUM"]
  classification: ColumnClassification = ATTRIBUTE
```

### ComplexityMetrics

```
Fields:
  node_count: int
  scope_count: int
  scope_types: list[str]
```

### AnalysisResult

```
Fields:
  data_model: DataModel
  output_columns: list[OutputColumn] = []
  metrics: ComplexityMetrics | None = None
```

### Merge functions (in domain.py)

- `merge_columns(left, right) -> QueriedColumn` — match by name; union usages; non-varchar wins over varchar; conflicting non-varchar warns, prefers left
- `merge_tables(left, right) -> QueriedTable` — assert same qualified_name; merge columns by name; OR has_wildcard flags
- `merge_models(left, right) -> DataModel` — union tables by qualified_name; union relationships by canonical_key

---

## Analysis Processing Sequence

The analyser processes a `sqlglot.Expression` through a single scope traversal loop. Key data structures maintained across the loop:

- **table_registry**: `dict[str, QueriedTable]` — maps qualified_name → QueriedTable
- **relationships**: `list[Relationship]` — accumulated relationships

### Step 1: Enumerate scopes

```
scopes = traverse_scope(expression)
# Returns post-order: innermost (CTEs, subqueries) first, root last
```

### Step 2: Per-scope processing loop

For each scope in `scopes`:

#### 2a. Register base tables and build alias map

```
alias_to_qualified: dict[str, str] = {}

For (alias, source) in scope.sources.items():
    if isinstance(source, exp.Table):
        qn = build_qualified_name(source.name, source.db, source.catalog)
        alias_to_qualified[alias] = qn
        if qn not in table_registry:
            table_registry[qn] = QueriedTable(
                name=source.name,
                schema_name=source.db,
                catalog_name=source.catalog
            )
```

Sources that are Scope instances (CTE/derived table) are NOT registered — their base tables are already registered by the child scope's iteration (earlier in the post-order traversal).

#### 2b. Extract columns per clause with usage classification

Rather than parent-walking from each Column node, iterate each SQL clause node separately within the scope's expression:

```
clause_map = {
    ColumnUsage.SELECT:  scope.expression.expressions,  # SELECT list items
    ColumnUsage.WHERE:   scope.expression.find(exp.Where),
    ColumnUsage.GROUP_BY: scope.expression.find(exp.Group),
    ColumnUsage.HAVING:  scope.expression.find(exp.Having),
    ColumnUsage.ORDER_BY: scope.expression.find(exp.Order),
    ColumnUsage.JOIN_ON: [join.args.get("on") for join in scope.expression.find_all(exp.Join)]
}

For each (usage, clause_node) in clause_map:
    For each Column in walk_in_scope(clause_node):
        Resolve column.table → qualified_name via alias_to_qualified
        Add/update QueriedColumn on the corresponding QueriedTable
```

**Resolving column.table**:
- If `column.table` is in `alias_to_qualified` → direct mapping to base table
- If `column.table` is empty and scope has exactly one base table source → unambiguous assignment
- If `column.table` maps to a Scope source (CTE/subquery) → skip (handled by child scope)

#### 2c. Handle wildcards

```
For star in scope.stars:
    if star is qualified (table.*):
        Resolve table alias → flag has_wildcard on that QueriedTable
    else (SELECT *):
        Flag has_wildcard on ALL base tables in this scope
```

#### 2d. Extract relationships

**From explicit JOINs:**
```
For each Join node in scope.expression.find_all(exp.Join):
    on_condition = join.args.get("on")
    if on_condition:
        For each equi-predicate (col_a = col_b) in on_condition:
            left_qn = resolve_to_base_table(col_a.table, scope)
            right_qn = resolve_to_base_table(col_b.table, scope)
            Accumulate column pairs per (left_qn, right_qn) pair
        Create Relationship with multi-column support
```

**From implicit WHERE joins:**
```
where_clause = scope.expression.find(exp.Where)
if where_clause:
    For each equality predicate (col_a = col_b) in where_clause:
        if col_a.table and col_b.table and they resolve to different base tables:
            Create Relationship
```

**Resolving aliases to base tables** (handles CTE references in JOINs):
```
resolve_to_base_table(alias, scope, column_name=None) -> str | None:
    source = scope.sources.get(alias)
    if isinstance(source, exp.Table):
        return build_qualified_name(source)
    if isinstance(source, Scope):
        # Trace through CTE/subquery to find the base table
        # Look at inner scope's columns for the same column_name
        # Recursively resolve
        ...
    return None
```

### Step 3: Compose DataModel

```
Deduplicate relationships by canonical_key
DataModel(tables=list(table_registry.values()), relationships=unique_relationships)
```

### Step 4: Wrap in AnalysisResult

```
AnalysisResult(data_model=data_model)
# output_columns and metrics populated by separate phases (lineage.py, metrics.py)
```

---

## Implementation Phases

### Phase 1 — Domain model (domain.py + test_domain_model.py)

Build all Pydantic classes, enums, and merge logic.

**What to build:**
1. `src/sql_analyser/domain.py` — ColumnUsage, ColumnClassification, QueriedColumn, QueriedTable (with qualified_name), Relationship (with canonical_key), DataModel (with merge method), OutputColumn, ComplexityMetrics, AnalysisResult, merge functions
2. `src/sql_analyser/__init__.py` — re-exports of domain classes
3. `tests/test_domain_model.py` — construction, JSON round-trip, qualified_name computation, canonical_key symmetry, all merge scenarios (disjoint, overlapping, type specificity, conflicting types, relationship dedup, wildcard propagation)

**Test cases covered:** TC-003-03 (JSON round-trip), TC-009-01 through TC-009-05 (merge scenarios)

### Phase 2 — Core extraction (analyser.py + test_source_data_model.py)

Build scope traversal and table/column extraction.

**What to build:**
1. `src/sql_analyser/analyser.py` — `analyse(expression) -> AnalysisResult`, scope traversal loop (steps 1–2b, 2c, 3–4 above), helper functions for alias resolution, column extraction per clause
2. `tests/conftest.py` — shared fixtures with parsed ASTs for all test SQL
3. `tests/test_source_data_model.py` — FR-001 test cases

**Test cases covered:** TC-001-01 through TC-001-10

### Phase 3 — Relationships (extend analyser.py + test_relationships.py)

Add relationship extraction to the existing scope loop.

**What to build:**
1. Extend `analyser.py` with step 2d (JOIN and WHERE relationship extraction, CTE alias resolution for relationships)
2. `tests/test_relationships.py` — FR-002 test cases

**Test cases covered:** TC-002-01 through TC-002-07

### Phase 4 — Metrics (metrics.py + test_metrics.py)

**What to build:**
1. `src/sql_analyser/metrics.py` — `compute_metrics(expression) -> ComplexityMetrics`
2. `tests/test_metrics.py` — FR-004 test cases

**Test cases covered:** TC-004-01 through TC-004-04

---

## Relevant Files

- `src/sql_analyser/domain.py` — all domain classes + merge logic (create new)
- `src/sql_analyser/__init__.py` — public API and re-exports (create new)
- `src/sql_analyser/analyser.py` — scope traversal, extraction, relationships (create in phase 2, extend in phase 3)
- `src/sql_analyser/metrics.py` — complexity metrics (create in phase 4)
- `tests/conftest.py` — shared parsed AST fixtures (create in phase 2)
- `tests/test_domain_model.py` — domain model + merge tests (create in phase 1)
- `tests/test_source_data_model.py` — FR-001 tests (create in phase 2)
- `tests/test_relationships.py` — FR-002 tests (create in phase 3)
- `tests/test_metrics.py` — FR-004 tests (create in phase 4)
- `AGENTS.md` — update module layout section to reflect revised structure
- `docs/DOMAIN-MODEL(proposed).md` — superseded by this plan

## Verification

1. **Phase 1**: `uv run pytest tests/test_domain_model.py` — all construction, serialisation, merge tests pass
2. **Phase 2**: `uv run pytest tests/test_source_data_model.py` — TC-001-01 through TC-001-10 pass
3. **Phase 3**: `uv run pytest tests/test_relationships.py` — TC-002-01 through TC-002-07 pass
4. **Phase 4**: `uv run pytest tests/test_metrics.py` — TC-004-01 through TC-004-04 pass
5. **Full suite**: `uv run pytest` — all tests pass with no warnings

## Decisions

- **QueriedTable uses structured namespace parts** (name, schema_name, catalog_name) with computed `qualified_name` — mirrors sqlglot Table AST; preserves structure for future features
- **Relationship references tables by `qualified_name` string** — keeps serialisation simple, decoupled from QueriedTable instances
- **Column clause detection via per-clause AST walking** — more reliable than parent-chain walking; iterate Select.expressions, Where, Group, Having, Order, Join.on separately
- **CTE/subquery columns are handled by child scopes** — the post-order traversal ensures inner scopes are processed first; outer scope columns referencing CTE aliases are skipped (not double-counted)
- **AnalysisResult included upfront** — OutputColumn, ComplexityMetrics, AnalysisResult defined in domain.py from phase 1; populated by later phases
- **domain.py as single file** (not package) — simpler at this stage; can split if it grows
- **AGENTS.md module layout to be updated** to reflect the revised structure

## Open Consideration

- **Unqualified columns in multi-table scopes**: When `column.table` is empty and the scope has multiple base tables, we cannot resolve without sqlglot's `qualify_columns` optimiser pass. Recommendation: either run qualification first, or leave unresolved columns unassigned with a warning. Decide during phase 2 implementation.
