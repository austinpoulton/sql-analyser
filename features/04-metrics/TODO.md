# Phase 4: Complexity Metrics — Implementation Plan

## Overview

Implement FR-004 (Complexity Metrics) by creating `metrics.py` module, integrating with `analyser.py`, and writing comprehensive tests.

**Dependencies:**
- Phase 1 (Domain Model) ✅ Complete — `ComplexityMetrics` and `AnalysisResult` classes exist
- Phase 2 (Core Extraction) ✅ Complete — `analyser.py` exists with `analyse()` function
- Phase 3 (Relationships) ✅ Complete — Not a blocker for metrics

## Tasks

### 1. Project Setup

**Task:** Create feature branch and set up git hooks
**Dependencies:** None
**Acceptance Criteria:**
- [ ] Create branch `feature/04-metrics` from `main`
- [ ] Set up pre-commit hook to run linting
- [ ] Set up pre-commit hook to run all tests
- [ ] Verify hooks block commits on failure

**Estimated Effort:** 15 minutes

---

### 2. Implement `src/sql_analyser/metrics.py`

**Task:** Create metrics module with node counting and scope analysis
**Dependencies:** Task 1
**Acceptance Criteria:**
- [ ] Module created with proper imports (`from __future__ import annotations`)
- [ ] `compute_metrics(expression: exp.Expression) -> ComplexityMetrics` function implemented
- [ ] `_count_nodes(expression: exp.Expression) -> int` helper using `expression.walk()`
- [ ] `_extract_scope_types(scopes: list) -> list[str]` helper extracting scope type names
- [ ] All functions have Google-style docstrings
- [ ] All functions have type hints
- [ ] No linting errors

**Implementation Notes:**
- Use `sqlglot.optimizer.scope.traverse_scope(expression)` to enumerate scopes
- Use `expression.walk()` generator to count all AST nodes
- Extract scope types from `type(scope.expression).__name__` (e.g., "Select", "CTE", "Union")
- Keep scope_types as ordered list (no deduplication)

**Test Coverage:** Will be validated by Task 5

**Estimated Effort:** 30 minutes

---

### 3. Integrate metrics into `src/sql_analyser/analyser.py`

**Task:** Modify `analyse()` to compute and populate metrics
**Dependencies:** Task 2
**Acceptance Criteria:**
- [ ] Import `compute_metrics` from `.metrics`
- [ ] Call `metrics = compute_metrics(expression)` in `analyse()` function
- [ ] Pass `metrics` to `AnalysisResult` constructor
- [ ] Existing tests still pass (no regression)
- [ ] Metrics are populated in returned `AnalysisResult`

**Implementation Location:**
```python
def analyse(expression: exp.Expression) -> AnalysisResult:
    # ... existing table/column/relationship extraction ...

    data_model = DataModel(tables=list(table_registry.values()), relationships=relationships)

    # NEW: Compute metrics
    metrics = compute_metrics(expression)

    return AnalysisResult(
        data_model=data_model,
        output_columns=[],  # Phase 7
        metrics=metrics,    # NEW
    )
```

**Test Coverage:** Verified by Task 6 (integration test)

**Estimated Effort:** 15 minutes

---

### 4. Add test fixtures to `tests/conftest.py`

**Task:** Add reusable fixtures for metrics test cases
**Dependencies:** None (can be done in parallel with Task 2)
**Acceptance Criteria:**
- [ ] `simple_query_ast` fixture added (TC-004-01)
- [ ] `cte_query_ast` fixture added (TC-004-02)
- [ ] `nested_cte_subquery_ast` fixture added (TC-004-03)
- [ ] `union_query_ast` fixture added (TC-004-04)
- [ ] All fixtures use `sqlglot.parse_one()`
- [ ] Fixtures match SQL from PRD test cases

**Fixture SQL:**
```python
# TC-004-01
simple_query_ast = "SELECT id, name FROM app.users WHERE active = 1"

# TC-004-02
cte_query_ast = """
    WITH cte AS (SELECT id FROM app.users)
    SELECT id FROM cte
"""

# TC-004-03
nested_cte_subquery_ast = """
    WITH base AS (
        SELECT id FROM app.users
    ),
    enriched AS (
        SELECT b.id, (SELECT MAX(score) FROM app.scores s WHERE s.user_id = b.id) AS top_score
        FROM base b
    )
    SELECT id, top_score FROM enriched
"""

# TC-004-04
union_query_ast = """
    SELECT id FROM app.table_a
    UNION ALL
    SELECT id FROM app.table_b
"""
```

**Estimated Effort:** 15 minutes

---

### 5. Create `tests/test_metrics.py`

**Task:** Write comprehensive test suite for metrics module
**Dependencies:** Tasks 2, 4
**Acceptance Criteria:**
- [ ] TC-004-01: Simple query baseline test
- [ ] TC-004-02: CTE scope count test
- [ ] TC-004-03: Nested CTE and correlated subquery test
- [ ] TC-004-04: UNION scope count test
- [ ] TC-METRICS-01: Empty SELECT minimal node count
- [ ] TC-METRICS-02: Complex JOIN increases node count
- [ ] TC-METRICS-03: Scope types are descriptive
- [ ] All tests use fixtures from `conftest.py`
- [ ] Tests assert on `ComplexityMetrics` fields: `node_count`, `scope_count`, `scope_types`
- [ ] All tests pass

**Key Test Patterns:**
```python
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
```

**Test Coverage Goal:** ≥95% for `metrics.py`

**Estimated Effort:** 45 minutes

---

### 6. Integration Testing

**Task:** Verify metrics are correctly integrated into full analysis pipeline
**Dependencies:** Tasks 2, 3, 5
**Acceptance Criteria:**
- [ ] Write integration test in `test_metrics.py` that calls `analyse()` directly
- [ ] Verify `AnalysisResult.metrics` is populated
- [ ] Verify metrics are JSON-serializable
- [ ] All existing tests still pass (run full test suite)

**Test Pattern:**
```python
def test_metrics_integration_in_analyse():
    """Verify metrics are populated in AnalysisResult from analyse()."""
    from sql_analyser import analyse
    import sqlglot

    expression = sqlglot.parse_one("SELECT id, name FROM users WHERE id = 1")
    result = analyse(expression)

    assert result.metrics is not None
    assert isinstance(result.metrics, ComplexityMetrics)
    assert result.metrics.node_count > 0
    assert result.metrics.scope_count == 1

    # Verify JSON serialization
    json_str = result.model_dump_json()
    assert "metrics" in json_str
    assert "node_count" in json_str
```

**Estimated Effort:** 20 minutes

---

### 7. Validation & Documentation

**Task:** Run full test suite, check coverage, update documentation
**Dependencies:** Tasks 1-6
**Acceptance Criteria:**
- [ ] Run `uv run pytest tests/test_metrics.py -v` — all pass
- [ ] Run `uv run pytest` — all tests pass (no regression)
- [ ] Check test coverage for `metrics.py` — ≥95%
- [ ] Verify no linting errors
- [ ] Update AGENTS.md Phase 4 status to "✅ Complete"
- [ ] Verify all success criteria from PRD are met

**Commands:**
```bash
uv run pytest tests/test_metrics.py -v
uv run pytest
uv run pytest --cov=src/sql_analyser/metrics --cov-report=term-missing
```

**Estimated Effort:** 20 minutes

---

### 8. Create Pull Request

**Task:** Commit changes and create PR for Phase 4
**Dependencies:** Task 7
**Acceptance Criteria:**
- [ ] All changes committed to `feature/04-metrics` branch
- [ ] Commit message follows convention (includes Claude Code attribution)
- [ ] Push branch to remote
- [ ] Create PR with descriptive title and summary
- [ ] PR description includes test results and coverage stats
- [ ] Link related tickets in PR description

**PR Title:** `feat: Phase 4 - Complexity Metrics (FR-004)`

**PR Summary Template:**
```markdown
## Summary
- Implemented `metrics.py` with AST node counting and scope analysis
- Integrated metrics computation into `analyse()` function
- Added comprehensive test suite with TC-004-01 through TC-004-04
- All tests pass, coverage ≥95% for metrics module

## Test Plan
- [x] All TC-004-XX test cases pass
- [x] Integration test verifies metrics in AnalysisResult
- [x] Full test suite passes (no regression)
- [x] Metrics are JSON-serializable

## Metrics
- Test coverage: XX%
- All linting checks pass
- Performance: metrics computed in <100ms for typical queries
```

**Estimated Effort:** 15 minutes

---

## Total Estimated Effort

~3 hours (including testing and validation)

## Dependencies Graph

```
Task 1 (Setup)
  ├─→ Task 2 (metrics.py)
  │     ├─→ Task 3 (analyser.py integration)
  │     └─→ Task 5 (test_metrics.py)
  │           └─→ Task 6 (integration tests)
  │                 └─→ Task 7 (validation)
  │                       └─→ Task 8 (PR)
  └─→ Task 4 (conftest.py fixtures)
        └─→ Task 5 (test_metrics.py)
```

## Success Criteria (Phase 4 Complete)

- [x] Domain model classes exist (Phase 1)
- [ ] `src/sql_analyser/metrics.py` created
- [ ] `compute_metrics()` function implemented
- [ ] Integration with `analyser.py` complete
- [ ] All TC-004-XX tests pass
- [ ] Test coverage ≥95% for `metrics.py`
- [ ] Full test suite passes
- [ ] Documentation updated
- [ ] PR created and ready for review

## Notes

- **Parallel Work:** Tasks 2 and 4 can be done in parallel
- **Testing Strategy:** Write tests immediately after implementing each function
- **Performance:** Monitor metrics computation time; should be <100ms for typical queries
- **Scope Types:** Keep as ordered list, no deduplication (detailed complexity profile)
