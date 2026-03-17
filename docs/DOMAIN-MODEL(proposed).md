# Plan: Domain Model Design for SQL Analyser

## TL;DR

Design and iteratively build the Pydantic v2 domain model that underpins all SQL analysis features. The model is split into two tiers: a **source data model** (DataModel with tables/relationships) and an **AnalysisResult** wrapper that adds output lineage, classification, and complexity metrics. Implementation follows 4 iterations, each independently testable.

## Design Decisions

- **AnalysisResult wraps DataModel** — DataModel stays focused on source tables and relationships (FR-001, FR-002, FR-009). AnalysisResult adds output lineage (FR-007), metrics (FR-004), and classification (FR-006).
- **ColumnUsage as enum set** — `usages: set[ColumnUsage]` tracks where each column was referenced (SELECT, WHERE, JOIN_ON, etc.).
- **Relationship direction follows SQL order** — left/right matches query order. A `canonical_key` property enables symmetric deduplication.
- **Data types as open strings** — `data_type: str = "varchar"` accommodates arbitrary CAST targets without restricting to an enum.

## Class Hierarchy

```
ColumnUsage (StrEnum)
    SELECT, WHERE, HAVING, ORDER_BY, GROUP_BY, JOIN_ON

ColumnClassification (StrEnum)
    MEASURE, DIMENSION, ATTRIBUTE

QueriedColumn (BaseModel)
    name: str
    data_type: str = "varchar"
    usages: set[ColumnUsage] = set()

QueriedTable (BaseModel)
    name: str                          # bare table name e.g. "orders"
    schema_name: str = ""              # schema/database e.g. "core_facts"
    catalog_name: str = ""             # catalog e.g. "my_catalog"
    columns: list[QueriedColumn] = []
    has_wildcard: bool = False
    → qualified_name (computed)        # joins non-empty parts with "."

Relationship (BaseModel)
    left_table: str
    left_columns: list[str]
    right_table: str
    right_columns: list[str]

DataModel (BaseModel)
    tables: list[QueriedTable] = []
    relationships: list[Relationship] = []

OutputColumn (BaseModel)
    alias: str
    source_table: str | None = None
    source_column: str | None = None
    transforms: list[str] = []
    classification: ColumnClassification = ATTRIBUTE

ComplexityMetrics (BaseModel)
    node_count: int
    scope_count: int
    scope_types: list[str]

AnalysisResult (BaseModel)
    data_model: DataModel
    output_columns: list[OutputColumn] = []
    metrics: ComplexityMetrics | None = None
```

## Iterative Implementation

### Iteration 1 — Core source model (Phase 1 from AGENTS.md)

Build the minimal domain model needed to support FR-001 (table/column extraction) and FR-002 (relationships).

**What to build:**
1. Create `src/sql_analyser/domain.py`
2. Implement `ColumnUsage` as a `StrEnum` with values: `SELECT`, `WHERE`, `HAVING`, `ORDER_BY`, `GROUP_BY`, `JOIN_ON`
3. Implement `QueriedColumn` — fields: `name: str`, `data_type: str = "varchar"`, `usages: set[ColumnUsage] = set()`
4. Implement `QueriedTable` — fields: `name: str`, `schema_name: str = ""`, `catalog_name: str = ""`, `columns: list[QueriedColumn] = []`, `has_wildcard: bool = False`. Add a `qualified_name` computed property that joins non-empty parts `[catalog_name, schema_name, name]` with `"."`.
5. Implement `Relationship` — fields: `left_table: str`, `left_columns: list[str]`, `right_table: str`, `right_columns: list[str]`. Add a `canonical_key` property that returns a normalised tuple for symmetric deduplication (handles self-joins correctly by sorting the two `(table, sorted_columns)` pairs).
6. Implement `DataModel` — fields: `tables: list[QueriedTable] = []`, `relationships: list[Relationship] = []`
7. Create `src/sql_analyser/__init__.py` with public re-exports
8. Create `tests/test_domain_model.py` — test serialisation (round-trip JSON), construction, `qualified_name` computation, `canonical_key` symmetry

**Design notes:**
- Use default Pydantic v2 structural equality (all fields compared). Merge matching uses explicit name-based lookup, not `__eq__`.
- `set[ColumnUsage]` serialises as a JSON array of strings via Pydantic's StrEnum support.
- `QueriedTable` stores namespace parts separately (`name`, `schema_name`, `catalog_name`) mirroring sqlglot's `exp.Table` properties (`name`, `db`, `catalog`). The `qualified_name` computed property provides the dotted string used for merge matching and Relationship references.
- `Relationship.canonical_key` normalises for deduplication: `tuple(sorted([(left_table, tuple(sorted(left_columns))), (right_table, tuple(sorted(right_columns)))]))`. For self-joins, both entries have the same table name but different columns, so sorting still yields a unique key.

### Iteration 2 — Merge support (FR-009)

Add merge logic co-located in `domain.py` so DataModels from multiple queries can be combined.

**What to build:**
1. Add merge functions to `src/sql_analyser/domain.py`
2. `merge_columns(left: QueriedColumn, right: QueriedColumn) -> QueriedColumn` — match by name; union usages; resolve data_type (non-`varchar` wins; if both non-`varchar` and different, warn and prefer left)
3. `merge_tables(left: QueriedTable, right: QueriedTable) -> QueriedTable` — assert same `qualified_name`; merge column lists by name using `merge_columns`; OR the `has_wildcard` flags
4. `merge_models(left: DataModel, right: DataModel) -> DataModel` — union tables (merge overlapping by `qualified_name`); union relationships (deduplicate via `canonical_key`)
5. Add a convenience `DataModel.merge(other)` method that delegates to `merge_models`
6. Add merge tests to `tests/test_domain_model.py` — test: disjoint merge, overlapping tables, type specificity resolution (varchar vs numeric), conflicting non-varchar types (warning), relationship deduplication, wildcard flag propagation

### Iteration 3 — Output model (FR-006, FR-007, FR-004)

Add the analysis result wrapper with lineage, classification, and metrics.

**What to build:**
1. Add `ColumnClassification` StrEnum to `domain.py`: `MEASURE`, `DIMENSION`, `ATTRIBUTE`
2. Add `OutputColumn` to `domain.py` — fields: `alias: str`, `source_table: str | None`, `source_column: str | None`, `transforms: list[str] = []`, `classification: ColumnClassification = ATTRIBUTE`
3. Add `ComplexityMetrics` to `domain.py` — fields: `node_count: int`, `scope_count: int`, `scope_types: list[str]`
4. Add `AnalysisResult` to `domain.py` — fields: `data_model: DataModel`, `output_columns: list[OutputColumn] = []`, `metrics: ComplexityMetrics | None = None`
5. Add serialisation tests for the new classes in `tests/test_domain_model.py`

### Iteration 4 — Rendering support (FR-003)

Add properties/methods needed for Jinja2 template consumption.

**What to build:**
1. Add `DataModel.to_mermaid() -> str` and `DataModel.to_dbml() -> str` methods that render via Jinja2 templates
2. Create `src/sql_analyser/templates/mermaid_erd.j2` and `dbml.j2`
3. Add any computed properties needed by templates (e.g. `Relationship.label` returning `"orders.prod_sku = product.sku"` format)
4. Create `tests/test_rendering.py` — test expected Mermaid/DBML output against the spec's example

## Relevant files

- `src/sql_analyser/domain.py` — all Pydantic domain classes and merge logic (create new)
- `src/sql_analyser/__init__.py` — public API re-exports (create new)
- `src/sql_analyser/templates/mermaid_erd.j2` — Mermaid template (create in iteration 4)
- `src/sql_analyser/templates/dbml.j2` — DBML template (create in iteration 4)
- `tests/test_domain_model.py` — domain model and merge tests (create new)
- `tests/test_rendering.py` — rendering tests (create in iteration 4)
- [SQL-ANALYSER-SPEC.md](SQL-ANALYSER-SPEC.md) — spec reference (sections 6, 7.2, 8)
- [AGENTS.md](AGENTS.md) — implementation roadmap and conventions

## Verification

1. **Iteration 1**: `uv run pytest tests/test_domain_model.py` — all core model tests pass (construction, JSON round-trip, qualified_name, canonical_key)
2. **Iteration 2**: `uv run pytest tests/test_domain_model.py` — all merge scenarios pass (disjoint, overlapping, type resolution, dedup)
3. **Iteration 3**: `uv run pytest tests/test_domain_model.py` — extended tests for OutputColumn, ComplexityMetrics, AnalysisResult serialisation
4. **Iteration 4**: `uv run pytest tests/test_rendering.py` — Mermaid ERD output matches spec example (section 8.1)
5. **Cross-check**: After all iterations, `uv run pytest` passes all tests with no warnings

## Key Design Rationale

- **DataModel vs AnalysisResult separation**: DataModel represents the *source* data model — the tables and relationships the query depends on. This is the unit of merging (FR-009). AnalysisResult adds per-query analysis products (lineage, metrics) that don't participate in merging.
- **ColumnUsage as StrEnum**: Type-safe, serialises cleanly to JSON strings, supports set operations for union during merge.
- **Relationship.canonical_key for deduplication**: Stores relationships in SQL order for readability but provides a normalised key for set-based deduplication. Self-joins work because the column lists differ even when table names match.
- **Open string for data_type**: CAST expressions can produce arbitrary SQL type names (e.g. `DECIMAL(10,2)`, `DATE`). An enum would be too restrictive.
- **Structured namespace for QueriedTable**: `name`, `schema_name`, `catalog_name` stored separately mirroring sqlglot's `exp.Table` properties. A `qualified_name` computed property joins non-empty parts with `"."`. This preserves AST structure and enables future schema-level features.
- **No frozen models**: Merge operations create new instances. Pydantic's default structural equality (`__eq__` on all fields) is correct for assertion in tests. Merge matching uses explicit `qualified_name`-based lookup.

## Scope

**Included:** All domain model classes, enums, serialisation, merge logic, and rendering methods.
**Excluded:** Analyser logic (scope traversal, column extraction), lineage computation logic, metrics computation logic — these are downstream consumers of the domain model, built in Phases 2–8 per AGENTS.md.
