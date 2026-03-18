# PRD: Domain Model & Serialisation (FR-009)

## Overview

Implement the core domain model classes for SQL Analyser using Pydantic, providing type-safe data structures for representing extracted SQL metadata (tables, columns, relationships) with JSON serialisation and merge capabilities.

## Problem Statement

The SQL Analyser needs a robust, serialisable domain model to represent:
- Source tables and their columns extracted from SQL queries
- Relationships between tables (from JOINs and WHERE clauses)
- Output column lineage and classifications
- Complexity metrics

This domain model must support:
- JSON serialisation for persistence and API responses
- Merging multiple data models (for analysing related queries)
- Type safety and validation via Pydantic
- Clear separation of concerns (storage structure vs computed properties)

## Goals

1. **Define all domain model classes** as Pydantic models in `domain.py`
2. **Implement JSON serialisation** with round-trip fidelity
3. **Build merge logic** for combining DataModels with type specificity rules
4. **Create computed properties** for qualified names and relationship deduplication
5. **Establish foundation** for subsequent extraction and analysis phases

## Non-Goals

- SQL parsing or AST traversal (Phase 2)
- Relationship extraction logic (Phase 3)
- Metrics computation (Phase 4)
- Template rendering (Phase 8)

## Success Metrics

- All domain model tests pass (`pytest tests/test_domain_model.py`)
- 100% test coverage of domain classes and merge logic
- JSON round-trip serialisation preserves all data
- Merge operations follow type specificity rules correctly

## User Stories

### US-1: Type-Safe Domain Model
**As a** developer building the SQL Analyser
**I want** Pydantic models for all domain classes
**So that** I get automatic validation, serialisation, and IDE support

**Acceptance Criteria:**
- All domain classes are Pydantic `BaseModel` subclasses
- Type hints on all fields
- Default values specified where appropriate
- Models are importable from `sql_analyser` package

### US-2: JSON Serialisation
**As a** data engineer using SQL Analyser output
**I want** to serialise DataModel to JSON
**So that** I can persist analysis results and pass them to other tools

**Acceptance Criteria:**
- `.model_dump()` produces valid JSON-serialisable dict
- `.model_dump_json()` produces valid JSON string
- `.model_validate()` and `.model_validate_json()` reconstruct objects
- Round-trip preserves all fields including enums and sets

### US-3: Qualified Table Names
**As a** developer resolving table references
**I want** `QueriedTable.qualified_name` to compute dotted notation
**So that** I can match tables across catalogs/schemas consistently

**Acceptance Criteria:**
- `qualified_name` property joins non-empty parts: `[catalog, schema, name]`
- Examples: `"orders"`, `"core_facts.orders"`, `"my_catalog.core_facts.orders"`
- Property is computed, not stored
- Used for merge matching and relationship references

### US-4: Symmetric Relationship Deduplication
**As a** developer extracting relationships
**I want** `Relationship.canonical_key` to normalise join sides
**So that** `(A→B)` and `(B→A)` deduplicate correctly

**Acceptance Criteria:**
- `canonical_key` property returns normalised tuple
- Symmetry: `Relationship(A, [c1], B, [c2]).canonical_key == Relationship(B, [c2], A, [c1]).canonical_key`
- Multi-column joins: column lists are sorted within each side
- Key suitable for set deduplication

### US-5: Merge DataModels
**As a** developer analysing multiple related queries
**I want** to merge DataModels from different queries
**So that** I can build a unified source data model

**Acceptance Criteria:**
- `DataModel.merge(other)` returns new merged DataModel
- Tables matched by `qualified_name`
- Columns within matching tables merged by name
- Relationships deduplicated by `canonical_key`
- Type specificity: non-`varchar` wins over `varchar`
- Conflicting non-`varchar` types warn but prefer left operand
- `has_wildcard` flag: `True` if either side is `True`

## Technical Design

### Module Structure

```
src/sql_analyser/
├── __init__.py       # Public API: re-export domain classes
└── domain.py         # All Pydantic models + merge logic

tests/
└── test_domain_model.py  # Domain model tests
```

### Domain Model Classes

#### Enums

```python
from enum import StrEnum

class ColumnUsage(StrEnum):
    """SQL clause where a column was referenced."""
    SELECT = "select"
    WHERE = "where"
    HAVING = "having"
    ORDER_BY = "order_by"
    GROUP_BY = "group_by"
    JOIN_ON = "join_on"

class ColumnClassification(StrEnum):
    """Business classification of an output column."""
    MEASURE = "measure"
    DIMENSION = "dimension"
    ATTRIBUTE = "attribute"
```

#### QueriedColumn

```python
class QueriedColumn(BaseModel):
    """A column extracted from SQL, with inferred type and usage tracking."""

    name: str
    data_type: str = "varchar"
    usages: set[ColumnUsage] = Field(default_factory=set)
```

**Design Notes:**
- `data_type` defaults to `"varchar"` (lowest specificity)
- `usages` is a set to avoid duplicates; serialises as JSON array
- Merge logic: union usages; type specificity wins

#### QueriedTable

```python
class QueriedTable(BaseModel):
    """A base table extracted from SQL with its referenced columns."""

    name: str
    schema_name: str = ""
    catalog_name: str = ""
    columns: list[QueriedColumn] = Field(default_factory=list)
    has_wildcard: bool = False

    @property
    def qualified_name(self) -> str:
        """Fully-qualified table name: catalog.schema.name (omits empty parts)."""
        parts = [p for p in [self.catalog_name, self.schema_name, self.name] if p]
        return ".".join(parts)
```

**Design Rationale:**
- Stores namespace parts separately (mirrors sqlglot's `exp.Table`)
- `qualified_name` is computed property for display and matching
- Preserves structure for future catalog-level features
- Merge matching: tables are equal if `qualified_name` matches

#### Relationship

```python
class Relationship(BaseModel):
    """A relationship between two tables on specific columns."""

    left_table: str
    left_columns: list[str]
    right_table: str
    right_columns: list[str]

    @property
    def canonical_key(self) -> tuple:
        """Normalised key for symmetric deduplication."""
        left = (self.left_table, tuple(sorted(self.left_columns)))
        right = (self.right_table, tuple(sorted(self.right_columns)))
        return tuple(sorted([left, right]))
```

**Design Notes:**
- Table references are `qualified_name` strings (decoupled from QueriedTable instances)
- Multi-column joins: `left_columns` and `right_columns` are lists
- `canonical_key` ensures `(A→B) == (B→A)` for deduplication

#### DataModel

```python
class DataModel(BaseModel):
    """Container for extracted source data model: tables + relationships."""

    tables: list[QueriedTable] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    def merge(self, other: "DataModel") -> "DataModel":
        """Merge with another DataModel."""
        return merge_models(self, other)
```

#### OutputColumn

```python
class OutputColumn(BaseModel):
    """Lineage and classification for a SELECT output column."""

    alias: str
    source_table: str | None = None
    source_column: str | None = None
    transforms: list[str] = Field(default_factory=list)
    classification: ColumnClassification = ColumnClassification.ATTRIBUTE
```

#### ComplexityMetrics

```python
class ComplexityMetrics(BaseModel):
    """AST complexity metrics."""

    node_count: int
    scope_count: int
    scope_types: list[str] = Field(default_factory=list)
```

#### AnalysisResult

```python
class AnalysisResult(BaseModel):
    """Top-level wrapper for complete analysis output."""

    data_model: DataModel
    output_columns: list[OutputColumn] = Field(default_factory=list)
    metrics: ComplexityMetrics | None = None
```

### Merge Logic

#### `merge_columns(left: QueriedColumn, right: QueriedColumn) -> QueriedColumn`

**Rules:**
1. Assert names match
2. Union usages
3. Type specificity:
   - If both `varchar`: result is `varchar`
   - If one `varchar`, other not: non-`varchar` wins
   - If both non-`varchar` and different: warn, prefer left

```python
def merge_columns(left: QueriedColumn, right: QueriedColumn) -> QueriedColumn:
    if left.name != right.name:
        raise ValueError(f"Cannot merge columns with different names: {left.name} vs {right.name}")

    usages = left.usages | right.usages

    if left.data_type == right.data_type:
        data_type = left.data_type
    elif left.data_type == "varchar":
        data_type = right.data_type
    elif right.data_type == "varchar":
        data_type = left.data_type
    else:
        warnings.warn(f"Column {left.name}: conflicting types {left.data_type} vs {right.data_type}, using {left.data_type}")
        data_type = left.data_type

    return QueriedColumn(name=left.name, data_type=data_type, usages=usages)
```

#### `merge_tables(left: QueriedTable, right: QueriedTable) -> QueriedTable`

**Rules:**
1. Assert `qualified_name` matches
2. Merge columns by name (union)
3. OR `has_wildcard` flags

```python
def merge_tables(left: QueriedTable, right: QueriedTable) -> QueriedTable:
    if left.qualified_name != right.qualified_name:
        raise ValueError(f"Cannot merge tables with different qualified names")

    # Build column index by name
    merged_cols: dict[str, QueriedColumn] = {}
    for col in left.columns:
        merged_cols[col.name] = col
    for col in right.columns:
        if col.name in merged_cols:
            merged_cols[col.name] = merge_columns(merged_cols[col.name], col)
        else:
            merged_cols[col.name] = col

    return QueriedTable(
        name=left.name,
        schema_name=left.schema_name,
        catalog_name=left.catalog_name,
        columns=list(merged_cols.values()),
        has_wildcard=left.has_wildcard or right.has_wildcard
    )
```

#### `merge_models(left: DataModel, right: DataModel) -> DataModel`

**Rules:**
1. Union tables by `qualified_name`
2. Union relationships by `canonical_key`

```python
def merge_models(left: DataModel, right: DataModel) -> DataModel:
    # Merge tables
    table_index: dict[str, QueriedTable] = {}
    for table in left.tables:
        table_index[table.qualified_name] = table
    for table in right.tables:
        qn = table.qualified_name
        if qn in table_index:
            table_index[qn] = merge_tables(table_index[qn], table)
        else:
            table_index[qn] = table

    # Deduplicate relationships
    rel_set: set[tuple] = set()
    merged_rels: list[Relationship] = []
    for rel in left.relationships + right.relationships:
        key = rel.canonical_key
        if key not in rel_set:
            rel_set.add(key)
            merged_rels.append(rel)

    return DataModel(tables=list(table_index.values()), relationships=merged_rels)
```

## Test Coverage

### Test Cases

From [TEST-CASES.md](../../docs/TEST-CASES.md):

| Test ID | Description | What to Assert |
|---------|-------------|----------------|
| TC-009-01 | Merge disjoint DataModels | Union of tables and relationships |
| TC-009-02 | Merge overlapping DataModels (same table, different columns) | Columns are unioned; table appears once |
| TC-009-03 | Merge with type specificity (varchar vs int) | Non-varchar wins |
| TC-009-04 | Merge with conflicting non-varchar types | Left wins, warning issued |
| TC-009-05 | Relationship deduplication via canonical_key | `(A→B)` and `(B→A)` merge to one |

Additional tests:

| Test ID | Description |
|---------|-------------|
| TC-DOMAIN-01 | Construct all domain classes with valid data |
| TC-DOMAIN-02 | JSON serialisation round-trip (model → dict → model) |
| TC-DOMAIN-03 | JSON string serialisation round-trip |
| TC-DOMAIN-04 | `QueriedTable.qualified_name` with all namespace parts |
| TC-DOMAIN-05 | `QueriedTable.qualified_name` with partial namespace |
| TC-DOMAIN-06 | `Relationship.canonical_key` symmetry |
| TC-DOMAIN-07 | `Relationship.canonical_key` multi-column sort |
| TC-DOMAIN-08 | Merge columns with usage union |
| TC-DOMAIN-09 | Merge tables with wildcard OR |

### Test File Structure

```python
# tests/test_domain_model.py

def test_column_usage_enum():
    """TC-DOMAIN-01: Enum construction and serialisation."""
    ...

def test_queried_column_construction():
    """TC-DOMAIN-01: QueriedColumn with defaults."""
    ...

def test_json_round_trip():
    """TC-DOMAIN-02, TC-DOMAIN-03: Full model serialisation."""
    ...

def test_qualified_name_full():
    """TC-DOMAIN-04: catalog.schema.name"""
    ...

def test_qualified_name_partial():
    """TC-DOMAIN-05: schema.name and name only"""
    ...

def test_relationship_canonical_key_symmetry():
    """TC-DOMAIN-06: (A→B) == (B→A)"""
    ...

def test_merge_columns_type_specificity():
    """TC-009-03: Non-varchar beats varchar"""
    ...

def test_merge_models_disjoint():
    """TC-009-01: Union of disjoint sets"""
    ...

def test_merge_models_overlapping():
    """TC-009-02: Column union within same table"""
    ...

def test_merge_relationship_deduplication():
    """TC-009-05: Symmetric relationship dedup"""
    ...
```

## Implementation Plan

### Step 1: Create `src/sql_analyser/domain.py`

1. Import dependencies: `pydantic`, `enum`, `warnings`
2. Define enums: `ColumnUsage`, `ColumnClassification`
3. Define models in dependency order:
   - `QueriedColumn`
   - `QueriedTable` (with `qualified_name` property)
   - `Relationship` (with `canonical_key` property)
   - `DataModel` (with `merge` method)
   - `OutputColumn`
   - `ComplexityMetrics`
   - `AnalysisResult`
4. Implement merge functions:
   - `merge_columns`
   - `merge_tables`
   - `merge_models`

### Step 2: Create `src/sql_analyser/__init__.py`

Re-export domain classes for public API:

```python
from .domain import (
    ColumnUsage,
    ColumnClassification,
    QueriedColumn,
    QueriedTable,
    Relationship,
    DataModel,
    OutputColumn,
    ComplexityMetrics,
    AnalysisResult,
)

__all__ = [
    "ColumnUsage",
    "ColumnClassification",
    "QueriedColumn",
    "QueriedTable",
    "Relationship",
    "DataModel",
    "OutputColumn",
    "ComplexityMetrics",
    "AnalysisResult",
]
```

### Step 3: Create `tests/test_domain_model.py`

1. Test basic construction
2. Test JSON serialisation (dict and string)
3. Test computed properties (`qualified_name`, `canonical_key`)
4. Test merge functions (all 5 merge scenarios)
5. Test edge cases (empty sets, conflicting types, wildcards)

### Step 4: Run Tests

```bash
uv run pytest tests/test_domain_model.py -v
```

## Dependencies

- **Python ≥ 3.12**
- **pydantic ≥ 2.0** (for `BaseModel`, `Field`, `StrEnum` serialisation)
- **pytest** (testing)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pydantic serialisation of `set[StrEnum]` | High | Use Pydantic v2 which natively supports set and StrEnum serialisation |
| Conflicting type resolution policy unclear | Medium | Follow spec: non-varchar wins; conflicting non-varchar warns and prefers left |
| `qualified_name` computation inconsistent | Medium | Centralize in computed property; write explicit tests for all namespace combinations |

## Open Questions

1. **Should merge functions mutate or return new instances?**
   → Return new instances (immutable merge)

2. **Should conflicting non-varchar types raise exception or warn?**
   → Warn (as per spec §7.2); prefer left operand

3. **Should we validate table/column name syntax?**
   → No; trust sqlglot parsing for now

## Success Criteria (Definition of Done)

- [ ] All domain classes implemented in `domain.py`
- [ ] All merge functions implemented
- [ ] Public API re-exports in `__init__.py`
- [ ] All tests in `test_domain_model.py` pass
- [ ] Code passes type checking (`mypy`)
- [ ] Docstrings on all public classes and functions (Google style)
- [ ] Test coverage ≥ 95% for `domain.py`

## References

- [SQL-ANALYSER-SPEC.md](../../SQL-ANALYSER-SPEC.md) — §6 (FR-009), §7.2 (Domain Model)
- [DOMAIN-MODEL-PLAN.md](../../docs/DOMAIN-MODEL-PLAN.md) — Phase 1 implementation details
- [TEST-CASES.md](../../docs/TEST-CASES.md) — TC-009-01 through TC-009-05
- [AGENTS.md](../../AGENTS.md) — Module layout, coding style
