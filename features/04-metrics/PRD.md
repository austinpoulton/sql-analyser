# PRD: Complexity Metrics (FR-004)

## Overview

Implement complexity metrics computation for SQL queries, providing quantitative measures of AST size and structural complexity through node counting and scope analysis.

## Problem Statement

Data engineers and analysts need objective measures of SQL query complexity to:
- Assess query maintainability and readability
- Identify overly complex queries that may need refactoring
- Track complexity trends over time in a query repository
- Make informed decisions about query optimization priorities

The SQL Analyser must compute deterministic, AST-based complexity metrics without executing or validating SQL.

## Goals

1. **Compute AST node count** — total number of nodes in the sqlglot expression tree
2. **Count scopes** — number of semantic scopes (root, CTEs, subqueries, UNIONs)
3. **Classify scope types** — list of scope types encountered (for detailed complexity profiling)
4. **Integrate with AnalysisResult** — populate the `ComplexityMetrics` field in existing domain model
5. **Provide clean API** — expose `compute_metrics(expression)` function in `metrics.py`

## Non-Goals

- Execution-based metrics (rows processed, execution time)
- Semantic complexity (cyclomatic complexity, nesting depth beyond scope count)
- Query optimization suggestions
- Comparative benchmarking against other queries
- Performance profiling or cost estimation

## Success Metrics

- All metrics tests pass (`pytest tests/test_metrics.py`)
- Metrics correctly computed for TC-004-01 through TC-004-04
- Deterministic output: same SQL → same metrics
- Metrics computed in <100ms for typical queries (<1000 nodes)

## User Stories

### US-1: Baseline Query Metrics
**As a** data engineer analysing simple queries
**I want** to see node count and scope count for basic SELECT statements
**So that** I have a baseline understanding of minimal query complexity

**Acceptance Criteria:**
- Simple `SELECT id, name FROM table WHERE x = 1` returns:
  - `node_count` > 0 (positive integer)
  - `scope_count` = 1 (root scope only)
  - `scope_types` contains one entry representing the root SELECT scope

**Test Coverage:** TC-004-01

### US-2: CTE Scope Detection
**As a** developer working with CTEs
**I want** scope count to include each CTE as a separate scope
**So that** I can quantify the structural complexity introduced by CTEs

**Acceptance Criteria:**
- Query with one CTE returns `scope_count` = 2 (CTE + root)
- `scope_types` includes both CTE and SELECT scope types

**Test Coverage:** TC-004-02

### US-3: Nested Scope Counting
**As a** data engineer reviewing complex queries
**I want** all nested scopes (CTEs, subqueries, correlated subqueries) counted
**So that** I can identify deeply nested queries that may be hard to maintain

**Acceptance Criteria:**
- Query with 2 CTEs and a correlated subquery returns `scope_count` = 4
- Each scope type is recorded in `scope_types`
- AST node count reflects additional structural complexity

**Test Coverage:** TC-004-03

### US-4: UNION Scope Handling
**As a** developer using UNION queries
**I want** each UNION branch counted as a separate scope
**So that** union complexity is reflected in metrics

**Acceptance Criteria:**
- `SELECT ... UNION ALL SELECT ...` returns `scope_count` ≥ 2
- Both branches are represented in scope types

**Test Coverage:** TC-004-04

### US-5: Metrics Integration
**As a** consumer of the SQL Analyser API
**I want** metrics automatically included in `AnalysisResult`
**So that** I get a complete analysis in one call

**Acceptance Criteria:**
- `analyse(expression)` returns `AnalysisResult` with populated `metrics` field
- Metrics can be None (if disabled) or `ComplexityMetrics` instance
- JSON serialisation includes metrics

## Technical Design

### Module Structure

```
src/sql_analyser/
├── metrics.py            # NEW: Complexity metrics computation
└── analyser.py           # MODIFY: Call compute_metrics() and populate AnalysisResult.metrics

tests/
└── test_metrics.py       # NEW: FR-004 test cases
```

### Implementation Details

#### `metrics.py`

```python
"""Complexity metrics computation for SQL expressions."""

from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from .domain import ComplexityMetrics


def compute_metrics(expression: exp.Expression) -> ComplexityMetrics:
    """
    Compute complexity metrics for a SQL expression.

    Args:
        expression: Parsed sqlglot expression

    Returns:
        ComplexityMetrics with node_count, scope_count, and scope_types
    """
    node_count = _count_nodes(expression)
    scopes = list(traverse_scope(expression))
    scope_count = len(scopes)
    scope_types = _extract_scope_types(scopes)

    return ComplexityMetrics(
        node_count=node_count,
        scope_count=scope_count,
        scope_types=scope_types,
    )


def _count_nodes(expression: exp.Expression) -> int:
    """
    Count total AST nodes in expression.

    Uses sqlglot's walk() to traverse all nodes in the tree.
    """
    return sum(1 for _ in expression.walk())


def _extract_scope_types(scopes: list) -> list[str]:
    """
    Extract scope type names from scope list.

    Args:
        scopes: List of sqlglot Scope objects

    Returns:
        List of scope type strings (e.g., ["SELECT", "CTE", "SUBQUERY"])
    """
    # Each Scope has an `expression` attribute which is an exp.Expression
    # The expression's type indicates the scope kind
    scope_types = []
    for scope in scopes:
        # Scope.expression is the root node for that scope
        expr_type = type(scope.expression).__name__
        scope_types.append(expr_type)
    return scope_types
```

**Design Notes:**
- **Node counting**: Use `expression.walk()` generator — iterates all nodes in AST
- **Scope enumeration**: Use `traverse_scope()` from sqlglot — returns all scopes in post-order
- **Scope types**: Extract from `scope.expression` type name (e.g., `Select`, `CTE`, `Subquery`, `Union`)
- **Determinism**: AST structure is deterministic → metrics are deterministic

#### Integration with `analyser.py`

Modify `analyse()` function to compute metrics after building DataModel:

```python
from .metrics import compute_metrics

def analyse(expression: exp.Expression) -> AnalysisResult:
    """Analyse SQL expression and extract source data model."""
    # ... existing table/column/relationship extraction ...

    data_model = DataModel(tables=list(table_registry.values()), relationships=relationships)

    # Compute metrics
    metrics = compute_metrics(expression)

    return AnalysisResult(
        data_model=data_model,
        output_columns=[],  # Populated in Phase 7
        metrics=metrics,
    )
```

**Design Consideration:** Metrics computation is independent of table/column extraction — can be computed directly from the AST before or after data model extraction. We compute it after to maintain pipeline order consistency.

### Domain Model (Already Defined in Phase 1)

```python
class ComplexityMetrics(BaseModel):
    """AST complexity metrics."""

    node_count: int
    scope_count: int
    scope_types: list[str] = Field(default_factory=list)
```

No changes needed — class already defined in `domain.py` from Phase 1.

## Test Coverage

### Test Cases

From [TEST-CASES.md](../../docs/TEST-CASES.md):

| Test ID | Description | Key Assertions |
|---------|-------------|----------------|
| TC-004-01 | Simple single-table query metric baseline | `node_count > 0`, `scope_count = 1`, scope types has one root entry |
| TC-004-02 | CTE increases scope count | `scope_count = 2`, scope types include CTE + SELECT |
| TC-004-03 | Nested CTE and subquery scope count | `scope_count = 4`, includes base CTE, enriched CTE, correlated subquery, root |
| TC-004-04 | UNION ALL scope count | `scope_count ≥ 2`, both UNION branches counted |

Additional edge cases:

| Test ID | Description |
|---------|-------------|
| TC-METRICS-01 | Empty SELECT (no WHERE/JOIN) has minimal node count |
| TC-METRICS-02 | Complex JOIN increases node count significantly vs simple SELECT |
| TC-METRICS-03 | Scope types are descriptive (not just "Expression") |

### Test File Structure

```python
# tests/test_metrics.py

import pytest
import sqlglot
from sql_analyser.metrics import compute_metrics
from sql_analyser.domain import ComplexityMetrics


def test_simple_query_baseline(simple_query_ast):
    """TC-004-01: Simple single-table query metrics."""
    metrics = compute_metrics(simple_query_ast)

    assert isinstance(metrics, ComplexityMetrics)
    assert metrics.node_count > 0
    assert metrics.scope_count == 1
    assert len(metrics.scope_types) == 1


def test_cte_scope_count(cte_query_ast):
    """TC-004-02: CTE increases scope count."""
    metrics = compute_metrics(cte_query_ast)

    assert metrics.scope_count == 2
    assert len(metrics.scope_types) == 2
    # Scope types should include both CTE and SELECT
    assert any("CTE" in st or "Select" in st for st in metrics.scope_types)


def test_nested_cte_subquery_scope_count(nested_cte_subquery_ast):
    """TC-004-03: Nested CTEs and correlated subquery."""
    metrics = compute_metrics(nested_cte_subquery_ast)

    assert metrics.scope_count == 4
    assert metrics.node_count > 20  # Reasonably complex query


def test_union_scope_count(union_query_ast):
    """TC-004-04: UNION ALL branches counted."""
    metrics = compute_metrics(union_query_ast)

    assert metrics.scope_count >= 2
    assert "Union" in str(metrics.scope_types) or len(metrics.scope_types) >= 2


def test_node_count_increases_with_complexity():
    """TC-METRICS-02: Complex queries have higher node counts."""
    simple = sqlglot.parse_one("SELECT id FROM users")
    complex_query = sqlglot.parse_one("""
        SELECT u.id, u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.active = 1 AND o.status IN ('shipped', 'delivered')
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
    """)

    simple_metrics = compute_metrics(simple)
    complex_metrics = compute_metrics(complex_query)

    assert complex_metrics.node_count > simple_metrics.node_count * 3
```

### Fixtures in `conftest.py`

Add fixtures for metrics test queries:

```python
@pytest.fixture
def simple_query_ast():
    """TC-004-01: Simple query AST."""
    return sqlglot.parse_one("SELECT id, name FROM app.users WHERE active = 1")

@pytest.fixture
def cte_query_ast():
    """TC-004-02: CTE query AST."""
    return sqlglot.parse_one("""
        WITH cte AS (SELECT id FROM app.users)
        SELECT id FROM cte
    """)

@pytest.fixture
def nested_cte_subquery_ast():
    """TC-004-03: Nested CTEs with correlated subquery."""
    return sqlglot.parse_one("""
        WITH base AS (
            SELECT id FROM app.users
        ),
        enriched AS (
            SELECT b.id, (SELECT MAX(score) FROM app.scores s WHERE s.user_id = b.id) AS top_score
            FROM base b
        )
        SELECT id, top_score FROM enriched
    """)

@pytest.fixture
def union_query_ast():
    """TC-004-04: UNION ALL query."""
    return sqlglot.parse_one("""
        SELECT id FROM app.table_a
        UNION ALL
        SELECT id FROM app.table_b
    """)
```

## Implementation Plan

### Step 1: Create `src/sql_analyser/metrics.py`

1. Import dependencies: `sqlglot`, `sqlglot.exp`, `traverse_scope`, `ComplexityMetrics`
2. Implement `_count_nodes(expression)` helper using `expression.walk()`
3. Implement `_extract_scope_types(scopes)` helper
4. Implement `compute_metrics(expression)` main function
5. Add docstrings (Google style) to all functions

### Step 2: Modify `src/sql_analyser/analyser.py`

1. Import `compute_metrics` from `.metrics`
2. In `analyse()` function, after building `DataModel`:
   - Call `metrics = compute_metrics(expression)`
   - Pass `metrics` to `AnalysisResult` constructor

### Step 3: Create `tests/test_metrics.py`

1. Import `pytest`, `sqlglot`, `compute_metrics`, `ComplexityMetrics`
2. Implement TC-004-01 through TC-004-04 tests
3. Add edge case tests (TC-METRICS-01, TC-METRICS-02, TC-METRICS-03)
4. Use fixtures from `conftest.py`

### Step 4: Add fixtures to `tests/conftest.py`

1. Add `simple_query_ast` fixture
2. Add `cte_query_ast` fixture
3. Add `nested_cte_subquery_ast` fixture
4. Add `union_query_ast` fixture

### Step 5: Run Tests

```bash
uv run pytest tests/test_metrics.py -v
uv run pytest  # Full suite
```

### Step 6: Verify Integration

Run existing tests to ensure metrics integration doesn't break Phase 2/3 functionality:

```bash
uv run pytest tests/test_source_data_model.py -v
uv run pytest tests/test_relationships.py -v
```

## Dependencies

- **Phase 1 (Domain Model)** — `ComplexityMetrics` class must exist
- **Phase 2 (Core Extraction)** — `analyser.py` and `AnalysisResult` must exist
- **sqlglot ≥ 0.25.0** — for `traverse_scope()` and AST traversal
- **pytest** — testing

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope type names are not human-readable (e.g., "Expression" instead of "SELECT") | Low | Extract from `type(scope.expression).__name__`, which gives class names like `Select`, `CTE`, `Union` |
| `traverse_scope()` behaviour changes across sqlglot versions | Medium | Pin sqlglot version in dependencies; document tested version |
| Node count varies with sqlglot parsing normalisation | Low | Metrics are for relative comparison, not absolute thresholds; normalisation is consistent within a version |
| Performance on very large ASTs (10k+ nodes) | Low | `walk()` is a generator; scope traversal is already used in Phase 2. Defer optimization until profiling shows need. |

## Open Questions

1. **Should we cache metrics computation?**
   → No; computation is fast (<100ms) and expression is already parsed. Caching adds complexity without clear benefit.

2. **Should scope types be normalized/deduplicated?**
   → No; preserve order and duplicates (e.g., a query with 3 CTEs will have 3 "CTE" entries). This gives a more detailed complexity profile.

3. **Should we compute additional metrics (max nesting depth, cyclomatic complexity)?**
   → Not in Phase 4. Focus on node count and scope count per FR-004. Additional metrics can be added later if needed.

4. **Should metrics be optional/configurable?**
   → Not initially. Always compute metrics. If performance becomes an issue, add a flag to `analyse()` to skip metrics.

## Success Criteria (Definition of Done)

- [ ] `src/sql_analyser/metrics.py` created with `compute_metrics()` function
- [ ] `analyser.py` modified to call `compute_metrics()` and populate `AnalysisResult.metrics`
- [ ] `tests/test_metrics.py` created with all TC-004-XX tests
- [ ] Fixtures added to `conftest.py` for metrics test queries
- [ ] All metrics tests pass (`pytest tests/test_metrics.py`)
- [ ] Full test suite passes (`pytest`)
- [ ] Code passes type checking (`mypy src/sql_analyser/metrics.py`)
- [ ] Docstrings on all public functions (Google style)
- [ ] Test coverage ≥ 95% for `metrics.py`

## Future Enhancements (Out of Scope)

- Max nesting depth metric
- Cyclomatic complexity for WHERE/JOIN conditions
- Query "fingerprinting" for similarity detection
- Performance profiling integration (execution time, memory usage)
- Comparative metrics dashboard

## References

- [SQL-ANALYSER-SPEC.md](../../SQL-ANALYSER-SPEC.md) — §6 (FR-004), §7.2 (Domain Model)
- [DOMAIN-MODEL-PLAN.md](../../docs/DOMAIN-MODEL-PLAN.md) — Phase 4 implementation details
- [TEST-CASES.md](../../docs/TEST-CASES.md) — TC-004-01 through TC-004-04
- [AGENTS.md](../../AGENTS.md) — Module layout, coding style, implementation sequence
- [sqlglot Scope documentation](https://sqlglot.com/sqlglot/optimizer/scope.html)
