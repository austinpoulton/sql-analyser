# Phase 3: Relationship Extraction — Implementation TODO

**Feature:** FR-002 — Relationship Extraction
**Status:** 🟡 Not Started
**Dependencies:** Phase 2 (Core Extraction) ✅ Complete

---

## Overview

Extract table relationships from SQL queries by analyzing:
1. Explicit JOIN conditions (all join types)
2. Implicit WHERE clause equi-joins
3. Multi-column relationships (composite keys)
4. CTE JOINs (resolve to base tables)

**Implementation approach:** Two-phase incremental delivery
- **Phase 3A:** Basic relationship extraction (base tables only)
- **Phase 3B:** CTE resolution for JOINs

---

## Progress Tracking

**Overall Status:** 🟡 **0% COMPLETE**

| Phase | Status | Test Coverage | Estimated Effort |
|---|---|---|---|
| 3A - Basic Relationship Extraction | 🟡 Not Started | TC-002-01, 02, 03, 04, 06, 07 | 4-6 hours |
| 3B - CTE Resolution | 🟡 Not Started | TC-002-05 | 2-3 hours |

**Test Results:** ⏳ Not run yet
**Target:** 63 tests passing (56 existing + 7 new Phase 3 tests)

---

## Phase 3A: Basic Relationship Extraction

**Goal:** Extract relationships from JOINs and WHERE clauses for base tables only.

### 3A.1 — Setup & Infrastructure

**Tasks:**
- [ ] 3A.1.1 — Create feature branch `feature/03-relationships`
- [ ] 3A.1.2 — Set up pre-commit hooks (ruff + pytest)
- [ ] 3A.1.3 — Create test file `tests/test_relationships.py` (empty shell)
- [ ] 3A.1.4 — Verify Phase 2 baseline: run `uv run pytest` (expect 56 passing)

**Acceptance Criteria:**
- Feature branch exists and is checked out
- Pre-commit hooks configured and tested
- Test file created with proper imports
- All existing tests passing

**Estimated effort:** 30 minutes

---

### 3A.2 — Add Relationship Accumulator

**Tasks:**
- [ ] 3A.2.1 — Add `all_relationships: list[Relationship] = []` to `analyse()` function
- [ ] 3A.2.2 — Update DataModel construction to include relationships list
- [ ] 3A.2.3 — Add logging statement: "Starting relationship extraction"

**Files to modify:**
- `src/sql_analyser/analyser.py` (lines ~189, ~329-333)

**Acceptance Criteria:**
- `all_relationships` list initialized in `analyse()`
- DataModel receives relationships list (currently empty)
- No test regressions

**Estimated effort:** 15 minutes

---

### 3A.3 — Extract Explicit JOIN Relationships (Single-Column)

**Tasks:**
- [ ] 3A.3.1 — Implement Step 2d.1: Find all `exp.Join` nodes in scope
- [ ] 3A.3.2 — Extract ON condition from each join
- [ ] 3A.3.3 — Find all `exp.EQ` predicates in ON condition
- [ ] 3A.3.4 — For each EQ with Column operands:
  - Resolve left and right table aliases using `_resolve_alias()`
  - Skip if either alias is None (unresolved or CTE)
  - Create `Relationship` object
  - Append to `all_relationships`
- [ ] 3A.3.5 — Add debug logging for each relationship extracted

**Implementation details:**
```python
# Inside the scope loop, after wildcard detection
joins = _walk_in_scope(cast(exp.Expression, scope.expression), exp.Join)
for join in joins:
    on_condition = join.args.get("on") if hasattr(join, "args") else None
    if on_condition:
        eq_predicates = _walk_in_scope(on_condition, exp.EQ)
        for eq in eq_predicates:
            # Check operands are columns
            if isinstance(eq.left, exp.Column) and isinstance(eq.right, exp.Column):
                left_table_alias = str(eq.left.table if hasattr(eq.left, "table") else "")
                right_table_alias = str(eq.right.table if hasattr(eq.right, "table") else "")

                # Resolve to qualified names
                left_qn = _resolve_alias(left_table_alias, scope, alias_to_qualified)
                right_qn = _resolve_alias(right_table_alias, scope, alias_to_qualified)

                if left_qn is not None and right_qn is not None:
                    all_relationships.append(Relationship(
                        left_table=left_qn,
                        left_columns=[str(eq.left.name)],
                        right_table=right_qn,
                        right_columns=[str(eq.right.name)]
                    ))
                    logger.debug(f"Extracted JOIN relationship: {left_qn} ↔ {right_qn}")
```

**Files to modify:**
- `src/sql_analyser/analyser.py` (add after line ~327, within scope loop)

**Acceptance Criteria:**
- Single-column JOIN relationships extracted
- Aliases correctly resolved to qualified names
- No crashes on non-Column EQ operands (e.g., `ON a.id = 123`)
- Logging shows relationships extracted

**Estimated effort:** 1.5 hours

---

### 3A.4 — Add Test Fixtures (Basic JOINs)

**Tasks:**
- [ ] 3A.4.1 — Add `single_column_join` fixture to `conftest.py`
- [ ] 3A.4.2 — Add `multiple_joins` fixture (chain: orders → customers → products)
- [ ] 3A.4.3 — Add `self_join` fixture

**Fixtures to add:**
```python
@pytest.fixture
def single_column_join():
    """TC-002-01: Single-column explicit JOIN."""
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
        dialect="postgres"
    )

@pytest.fixture
def multiple_joins():
    """TC-002-04: Multiple JOINs (chain)."""
    return sqlglot.parse_one(
        "SELECT o.id, c.name, p.name FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN products p ON o.product_id = p.id",
        dialect="postgres"
    )

@pytest.fixture
def self_join():
    """TC-002-06: Self-join."""
    return sqlglot.parse_one(
        "SELECT a.id, b.id FROM users a JOIN users b ON a.manager_id = b.id",
        dialect="postgres"
    )
```

**Files to modify:**
- `tests/conftest.py`

**Acceptance Criteria:**
- 3 new fixtures added
- Fixtures parse without errors
- Fixtures available to test functions

**Estimated effort:** 30 minutes

---

### 3A.5 — Write Tests for Single-Column JOINs

**Tasks:**
- [ ] 3A.5.1 — Implement `test_single_column_join()` (TC-002-01)
- [ ] 3A.5.2 — Implement `test_multiple_joins()` (TC-002-04)
- [ ] 3A.5.3 — Implement `test_self_join()` (TC-002-06)
- [ ] 3A.5.4 — Run tests: `uv run pytest tests/test_relationships.py -v`

**Test structure:**
```python
def test_single_column_join(single_column_join):
    """TC-002-01: Extract relationship from single-column JOIN."""
    result = analyse(single_column_join)

    # Verify relationship extracted
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify relationship properties (order-independent)
    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "customers" in tables

    # Verify columns (determine which side is which)
    if rel.left_table == "orders":
        assert rel.left_columns == ["customer_id"]
        assert rel.right_columns == ["id"]
    else:
        assert rel.left_columns == ["id"]
        assert rel.right_columns == ["customer_id"]
```

**Files to modify:**
- `tests/test_relationships.py`

**Acceptance Criteria:**
- 3 tests written and passing
- Tests verify relationship count, table names, and column names
- Tests handle left/right order independence

**Estimated effort:** 1 hour

---

### 3A.6 — Multi-Column Relationship Support

**Tasks:**
- [ ] 3A.6.1 — Refactor JOIN extraction to group column pairs by table pair
- [ ] 3A.6.2 — Accumulate multiple EQ predicates between same table pair
- [ ] 3A.6.3 — Create single Relationship with multiple columns

**Implementation details:**
```python
# Group by table pair
table_pair_map: dict[tuple[str, str], list[tuple[str, str]]] = {}

for eq in eq_predicates:
    # ... existing resolution logic ...

    if left_qn is not None and right_qn is not None:
        # Normalize table pair order for grouping
        key = (left_qn, right_qn)
        if key not in table_pair_map:
            table_pair_map[key] = []
        table_pair_map[key].append((str(eq.left.name), str(eq.right.name)))

# Create relationships from grouped data
for (left_qn, right_qn), col_pairs in table_pair_map.items():
    left_cols = [pair[0] for pair in col_pairs]
    right_cols = [pair[1] for pair in col_pairs]
    all_relationships.append(Relationship(
        left_table=left_qn,
        left_columns=left_cols,
        right_table=right_qn,
        right_columns=right_cols
    ))
```

**Files to modify:**
- `src/sql_analyser/analyser.py` (refactor Step 2d.1)

**Acceptance Criteria:**
- Multi-column JOINs grouped correctly
- Single Relationship created with multiple columns
- Previous tests (single-column) still pass

**Estimated effort:** 1 hour

---

### 3A.7 — Add Multi-Column Test

**Tasks:**
- [ ] 3A.7.1 — Add `multi_column_join` fixture to `conftest.py`
- [ ] 3A.7.2 — Implement `test_multi_column_join()` (TC-002-02)
- [ ] 3A.7.3 — Run tests: expect 4 passing

**Fixture:**
```python
@pytest.fixture
def multi_column_join():
    """TC-002-02: Multi-column JOIN."""
    return sqlglot.parse_one(
        "SELECT * FROM orders o "
        "JOIN shipments s ON o.region = s.region AND o.order_id = s.order_id",
        dialect="postgres"
    )
```

**Test:**
```python
def test_multi_column_join(multi_column_join):
    """TC-002-02: Extract multi-column relationship."""
    result = analyse(multi_column_join)

    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    # Verify both columns present (order may vary)
    assert len(rel.left_columns) == 2
    assert len(rel.right_columns) == 2
    assert set(rel.left_columns) == {"region", "order_id"}
    assert set(rel.right_columns) == {"region", "order_id"}
```

**Files to modify:**
- `tests/conftest.py`
- `tests/test_relationships.py`

**Acceptance Criteria:**
- Multi-column test passing
- Both columns captured in single relationship

**Estimated effort:** 30 minutes

---

### 3A.8 — Implicit WHERE Join Extraction

**Tasks:**
- [ ] 3A.8.1 — Implement Step 2d.2: Find WHERE clause in scope
- [ ] 3A.8.2 — Extract all `exp.EQ` predicates from WHERE
- [ ] 3A.8.3 — For each EQ with qualified columns from different tables:
  - Resolve aliases
  - Create Relationship
  - Append to `all_relationships`
- [ ] 3A.8.4 — Skip unqualified columns (likely filters, not joins)
- [ ] 3A.8.5 — Skip same-table comparisons (not joins)

**Implementation details:**
```python
# Step 2d.2: Extract from WHERE clause implicit joins
where_clause = scope.expression.find(exp.Where)
if where_clause:
    eq_predicates = _walk_in_scope(where_clause, exp.EQ)

    for eq in eq_predicates:
        if isinstance(eq.left, exp.Column) and isinstance(eq.right, exp.Column):
            left_table_alias = str(eq.left.table if hasattr(eq.left, "table") else "")
            right_table_alias = str(eq.right.table if hasattr(eq.right, "table") else "")

            # Skip unqualified columns
            if not left_table_alias or not right_table_alias:
                continue

            # Resolve aliases
            left_qn = _resolve_alias(left_table_alias, scope, alias_to_qualified)
            right_qn = _resolve_alias(right_table_alias, scope, alias_to_qualified)

            # Skip same-table comparisons
            if left_qn is not None and right_qn is not None and left_qn != right_qn:
                all_relationships.append(Relationship(
                    left_table=left_qn,
                    left_columns=[str(eq.left.name)],
                    right_table=right_qn,
                    right_columns=[str(eq.right.name)]
                ))
                logger.debug(f"Extracted implicit WHERE relationship: {left_qn} ↔ {right_qn}")
```

**Files to modify:**
- `src/sql_analyser/analyser.py` (add after Step 2d.1)

**Acceptance Criteria:**
- WHERE clause implicit joins extracted
- Unqualified columns skipped (e.g., `WHERE status = 'active'`)
- Same-table comparisons skipped
- Logging shows implicit relationships

**Estimated effort:** 45 minutes

---

### 3A.9 — Add Implicit JOIN Test

**Tasks:**
- [ ] 3A.9.1 — Add `implicit_where_join` fixture to `conftest.py`
- [ ] 3A.9.2 — Implement `test_implicit_where_join()` (TC-002-03)
- [ ] 3A.9.3 — Run tests: expect 5 passing

**Fixture:**
```python
@pytest.fixture
def implicit_where_join():
    """TC-002-03: Implicit WHERE join."""
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o, customers c WHERE o.customer_id = c.id",
        dialect="postgres"
    )
```

**Test:**
```python
def test_implicit_where_join(implicit_where_join):
    """TC-002-03: Extract relationship from implicit WHERE join."""
    result = analyse(implicit_where_join)

    # Should produce same relationship as explicit JOIN
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "customers" in tables
```

**Files to modify:**
- `tests/conftest.py`
- `tests/test_relationships.py`

**Acceptance Criteria:**
- Implicit WHERE join test passing
- Same relationship as explicit JOIN

**Estimated effort:** 30 minutes

---

### 3A.10 — Relationship Deduplication

**Tasks:**
- [ ] 3A.10.1 — After scope loop, deduplicate relationships by `canonical_key`
- [ ] 3A.10.2 — Use set to track seen keys
- [ ] 3A.10.3 — Build `unique_relationships` list
- [ ] 3A.10.4 — Pass `unique_relationships` to DataModel

**Implementation details:**
```python
# Step 3: Deduplicate relationships
seen_keys: set[tuple] = set()
unique_relationships: list[Relationship] = []

for rel in all_relationships:
    if rel.canonical_key not in seen_keys:
        seen_keys.add(rel.canonical_key)
        unique_relationships.append(rel)

logger.debug(
    f"Deduplicated {len(all_relationships)} relationships to {len(unique_relationships)} unique"
)

# Step 4: Compose DataModel
data_model = DataModel(
    tables=list(table_registry.values()),
    relationships=unique_relationships,  # Use deduplicated list
)
```

**Files to modify:**
- `src/sql_analyser/analyser.py` (add before DataModel construction)

**Acceptance Criteria:**
- Deduplication logic implemented
- Symmetric relationships detected (e.g., A→B same as B→A)
- Logging shows deduplication count

**Estimated effort:** 30 minutes

---

### 3A.11 — Add Deduplication Test

**Tasks:**
- [ ] 3A.11.1 — Add `union_with_duplicate_join` fixture to `conftest.py`
- [ ] 3A.11.2 — Implement `test_relationship_deduplication()` (TC-002-07)
- [ ] 3A.11.3 — Run tests: expect 6 passing

**Fixture:**
```python
@pytest.fixture
def union_with_duplicate_join():
    """TC-002-07: Relationship deduplication."""
    return sqlglot.parse_one(
        "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id "
        "UNION "
        "SELECT * FROM orders o2 JOIN customers c2 ON o2.customer_id = c2.id",
        dialect="postgres"
    )
```

**Test:**
```python
def test_relationship_deduplication(union_with_duplicate_join):
    """TC-002-07: Deduplicate relationships from UNION."""
    result = analyse(union_with_duplicate_join)

    # Should have only 1 relationship despite two identical JOINs
    assert len(result.data_model.relationships) == 1
```

**Files to modify:**
- `tests/conftest.py`
- `tests/test_relationships.py`

**Acceptance Criteria:**
- Deduplication test passing
- Only 1 relationship despite 2 identical JOINs

**Estimated effort:** 30 minutes

---

### 3A.12 — Phase 3A Testing & Validation

**Tasks:**
- [ ] 3A.12.1 — Run full Phase 3A test suite: `uv run pytest tests/test_relationships.py -v`
- [ ] 3A.12.2 — Run full regression suite: `uv run pytest`
- [ ] 3A.12.3 — Check test count: expect 62 passing (56 existing + 6 new)
- [ ] 3A.12.4 — Run mypy: `uv run mypy src/sql_analyser/analyser.py --strict`
- [ ] 3A.12.5 — Run ruff: `uv run ruff check . && uv run ruff format .`
- [ ] 3A.12.6 — Check code coverage: `uv run pytest --cov=src/sql_analyser --cov-report=term-missing`

**Acceptance Criteria:**
- 62 tests passing (6/7 Phase 3 tests complete)
- No mypy errors
- No ruff warnings
- Code coverage ≥ 90% on analyser.py
- Pre-commit hooks pass

**Estimated effort:** 30 minutes

---

### 3A.13 — Commit Phase 3A

**Tasks:**
- [ ] 3A.13.1 — Stage changes: `git add src/ tests/`
- [ ] 3A.13.2 — Commit with message following convention
- [ ] 3A.13.3 — Push to feature branch

**Commit message:**
```
feat: Phase 3A complete - Basic relationship extraction

Implement FR-002 relationship extraction for base tables:
- Extract explicit JOIN relationships (single & multi-column)
- Extract implicit WHERE clause equi-joins
- Support self-joins
- Implement relationship deduplication via canonical_key

Test coverage:
- 6/7 Phase 3 tests passing (TC-002-01, 02, 03, 04, 06, 07)
- TC-002-05 (CTE JOIN) deferred to Phase 3B
- All 56 Phase 1+2 tests still passing

Changes:
- src/sql_analyser/analyser.py: Add relationship extraction in scope loop
- tests/test_relationships.py: Add 6 test cases
- tests/conftest.py: Add 6 test fixtures

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Acceptance Criteria:**
- Changes committed to feature branch
- Commit message follows convention
- Pre-commit hooks passed

**Estimated effort:** 15 minutes

---

## Phase 3B: CTE Resolution

**Goal:** Resolve CTE aliases in JOIN conditions to base tables.

### 3B.1 — Analyze CTE Resolution Requirements

**Tasks:**
- [ ] 3B.1.1 — Read TC-002-05 test case requirements
- [ ] 3B.1.2 — Study existing `_resolve_alias()` function behavior
- [ ] 3B.1.3 — Understand sqlglot Scope structure for CTEs
- [ ] 3B.1.4 — Design `_resolve_cte_to_base_table()` function signature
- [ ] 3B.1.5 — Document algorithm in comments

**Research questions:**
- How to traverse from CTE alias → CTE Scope → base table?
- How to handle nested CTEs (CTE references another CTE)?
- How to find which base table provides a specific column?

**Acceptance Criteria:**
- Algorithm documented
- Function signature defined
- Edge cases identified

**Estimated effort:** 1 hour

---

### 3B.2 — Implement CTE Resolution Helper

**Tasks:**
- [ ] 3B.2.1 — Implement `_resolve_cte_to_base_table()` function
- [ ] 3B.2.2 — Handle direct CTE → base table resolution
- [ ] 3B.2.3 — Handle nested CTE resolution (recursive)
- [ ] 3B.2.4 — Add logging for CTE resolution steps
- [ ] 3B.2.5 — Add unit-level testing (manual calls)

**Function signature:**
```python
def _resolve_cte_to_base_table(
    cte_alias: str,
    column_name: str,
    scope: Scope,
    table_registry: dict[str, QueriedTable]
) -> str | None:
    """
    Resolve a CTE column reference to its base table qualified name.

    Args:
        cte_alias: The CTE alias used in the JOIN.
        column_name: The column name referenced.
        scope: The current scope containing the CTE reference.
        table_registry: Registry of base tables.

    Returns:
        Qualified table name, or None if unresolvable.

    Algorithm:
        1. Look up cte_alias in scope.sources
        2. If it's a Scope, traverse its SELECT expressions
        3. Find the expression with alias matching column_name
        4. Extract source column and table from that expression
        5. If source table is another CTE, recurse
        6. If source table is base table, return qualified name
    """
    ...
```

**Files to modify:**
- `src/sql_analyser/analyser.py` (add new function)

**Acceptance Criteria:**
- Function implemented and handles basic CTE → base table
- Function handles nested CTEs (recursion)
- Logging shows resolution path
- No infinite loops on circular references

**Estimated effort:** 2 hours

---

### 3B.3 — Integrate CTE Resolution into JOIN Extraction

**Tasks:**
- [ ] 3B.3.1 — Update Step 2d.1 (JOIN extraction) to call `_resolve_cte_to_base_table()`
- [ ] 3B.3.2 — When `_resolve_alias()` returns None, check if it's a CTE
- [ ] 3B.3.3 — If CTE, call `_resolve_cte_to_base_table()` with column name
- [ ] 3B.3.4 — Use resolved base table in Relationship

**Implementation details:**
```python
# In Step 2d.1, after _resolve_alias() returns None
if left_qn is None:
    # Check if it's a CTE reference
    if left_table_alias in scope.sources and isinstance(scope.sources[left_table_alias], Scope):
        left_qn = _resolve_cte_to_base_table(
            left_table_alias,
            str(eq.left.name),
            scope,
            table_registry
        )

# Same for right_qn
```

**Files to modify:**
- `src/sql_analyser/analyser.py` (Step 2d.1)

**Acceptance Criteria:**
- CTE JOINs now resolve to base tables
- Non-CTE JOINs still work (no regression)

**Estimated effort:** 30 minutes

---

### 3B.4 — Add CTE JOIN Test

**Tasks:**
- [ ] 3B.4.1 — Add `cte_join` fixture to `conftest.py`
- [ ] 3B.4.2 — Implement `test_cte_join()` (TC-002-05)
- [ ] 3B.4.3 — Run test: expect passing
- [ ] 3B.4.4 — Run full suite: expect 63 passing (56 + 7 new)

**Fixture:**
```python
@pytest.fixture
def cte_join():
    """TC-002-05: CTE JOIN."""
    return sqlglot.parse_one(
        """
        WITH tmp AS (SELECT order_id, total FROM orders)
        SELECT t.order_id, p.name
        FROM tmp t
        JOIN products p ON t.order_id = p.order_id
        """,
        dialect="postgres"
    )
```

**Test:**
```python
def test_cte_join(cte_join):
    """TC-002-05: Resolve CTE in JOIN to base table."""
    result = analyse(cte_join)

    # Should resolve tmp → orders
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]

    tables = {rel.left_table, rel.right_table}
    assert "orders" in tables
    assert "products" in tables
    assert "tmp" not in tables  # CTE should not appear
```

**Files to modify:**
- `tests/conftest.py`
- `tests/test_relationships.py`

**Acceptance Criteria:**
- CTE JOIN test passing
- Relationship uses base table "orders", not CTE "tmp"
- All 63 tests passing

**Estimated effort:** 30 minutes

---

### 3B.5 — Phase 3B Testing & Validation

**Tasks:**
- [ ] 3B.5.1 — Run full Phase 3 test suite: `uv run pytest tests/test_relationships.py -v`
- [ ] 3B.5.2 — Run full regression suite: `uv run pytest`
- [ ] 3B.5.3 — Check test count: expect 63 passing (56 + 7 new)
- [ ] 3B.5.4 — Run mypy: `uv run mypy src/sql_analyser/analyser.py --strict`
- [ ] 3B.5.5 — Run ruff: `uv run ruff check . && uv run ruff format .`
- [ ] 3B.5.6 — Check code coverage: expect ≥ 90% on analyser.py

**Acceptance Criteria:**
- All 63 tests passing (7/7 Phase 3 tests complete)
- No mypy errors
- No ruff warnings
- Code coverage ≥ 90%
- Pre-commit hooks pass

**Estimated effort:** 30 minutes

---

### 3B.6 — Commit Phase 3B

**Tasks:**
- [ ] 3B.6.1 — Stage changes: `git add src/ tests/`
- [ ] 3B.6.2 — Commit with message
- [ ] 3B.6.3 — Push to feature branch

**Commit message:**
```
feat: Phase 3B complete - CTE resolution for JOINs

Implement CTE alias resolution in JOIN conditions:
- Add _resolve_cte_to_base_table() helper function
- Traverse CTE scopes to find base tables for columns
- Support nested CTE resolution (recursive)
- Integrate into JOIN extraction logic

Test coverage:
- TC-002-05 (CTE JOIN) now passing
- All 7 Phase 3 tests passing
- All 63 tests passing (no regressions)

Changes:
- src/sql_analyser/analyser.py: Add CTE resolution logic
- tests/test_relationships.py: Add TC-002-05 test
- tests/conftest.py: Add cte_join fixture

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Acceptance Criteria:**
- Changes committed
- Commit message follows convention
- Pre-commit hooks passed

**Estimated effort:** 15 minutes

---

## Phase 3 Finalization

### 3F.1 — Documentation Update

**Tasks:**
- [ ] 3F.1.1 — Update `CLAUDE.md` (formerly AGENTS.md): Mark Phase 3 as Complete
- [ ] 3F.1.2 — Update this TODO.md with final status (100% complete)
- [ ] 3F.1.3 — Verify all docstrings in `analyser.py` for new functions
- [ ] 3F.1.4 — Commit documentation updates

**Acceptance Criteria:**
- CLAUDE.md reflects Phase 3 completion
- TODO.md shows 100% complete
- All new functions have docstrings

**Estimated effort:** 20 minutes

---

### 3F.2 — Create Pull Request

**Tasks:**
- [ ] 3F.2.1 — Review all changes: `git log main..feature/03-relationships`
- [ ] 3F.2.2 — Check diff stats: `git diff --stat main`
- [ ] 3F.2.3 — Create PR using `gh pr create` (or manually on GitHub)
- [ ] 3F.2.4 — Include test results and coverage metrics in PR description

**PR Template:**
```markdown
## Summary
Phase 3: Relationship Extraction (FR-002) - Complete

Extracts table relationships from SQL queries by analyzing JOIN conditions and implicit WHERE clause equi-joins.

## Changes
- ✅ Explicit JOIN relationship extraction (single & multi-column)
- ✅ Implicit WHERE clause equi-joins
- ✅ Self-join support
- ✅ CTE alias resolution in JOINs
- ✅ Relationship deduplication

## Test Coverage
- 7 new tests for FR-002 (TC-002-01 through TC-002-07)
- All 63 tests passing (56 existing + 7 new)
- Code coverage: ≥90% on analyser.py

## Files Changed
- `src/sql_analyser/analyser.py`: +150 lines (relationship extraction logic)
- `tests/test_relationships.py`: New file with 7 tests
- `tests/conftest.py`: +7 fixtures
- `features/03-relationships/`: PRD + TODO
- `CLAUDE.md`: Updated status

## Checklist
- [x] All tests passing
- [x] No mypy errors (strict mode)
- [x] No ruff warnings
- [x] Pre-commit hooks passing
- [x] Documentation updated
- [x] Commits follow convention

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**Acceptance Criteria:**
- PR created on GitHub
- PR description complete with metrics
- Ready for review

**Estimated effort:** 30 minutes

---

## Test Case Summary

| Test Case | Description | Fixture | Phase |
|---|---|---|---|
| TC-002-01 | Single-column explicit JOIN | `single_column_join` | 3A |
| TC-002-02 | Multi-column JOIN | `multi_column_join` | 3A |
| TC-002-03 | Implicit WHERE join | `implicit_where_join` | 3A |
| TC-002-04 | Multiple JOINs (chain) | `multiple_joins` | 3A |
| TC-002-05 | CTE JOIN | `cte_join` | 3B |
| TC-002-06 | Self-join | `self_join` | 3A |
| TC-002-07 | Relationship deduplication | `union_with_duplicate_join` | 3A |

---

## Dependencies

**Required before starting:**
- ✅ Phase 1 complete (domain.py with Relationship class)
- ✅ Phase 2 complete (analyser.py with scope traversal)
- ✅ Git repository clean state
- ✅ All 56 existing tests passing

**Blocked tasks:** None

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| CTE resolution complexity | Implement Phase 3A first, defer 3B if needed |
| Relationship duplication bugs | Thoroughly test canonical_key symmetry |
| Performance impact from relationship extraction | Profile with large queries; optimize if needed |
| Regression in existing tests | Run full suite after each phase |

---

## Success Criteria

**Phase 3A Complete:**
- ✅ 6/7 relationship tests passing
- ✅ 62 total tests passing
- ✅ No regressions

**Phase 3B Complete:**
- ✅ 7/7 relationship tests passing
- ✅ 63 total tests passing
- ✅ CTE JOINs resolved correctly

**Phase 3 Complete:**
- ✅ All FR-002 requirements implemented
- ✅ All test cases (TC-002-01 through TC-002-07) passing
- ✅ Code coverage ≥ 90% on analyser.py
- ✅ No mypy or ruff errors
- ✅ PR created and ready for merge

---

## Estimated Total Effort

- **Phase 3A:** 4-6 hours
- **Phase 3B:** 2-3 hours
- **Finalization:** 1 hour
- **Total:** 7-10 hours

---

## Notes

- CTE resolution (Phase 3B) is required but can be implemented after Phase 3A is stable
- Relationship deduplication is critical — test thoroughly
- Self-joins are a common edge case — ensure left_table == right_table works
- Consider adding integration test combining relationships with Phase 2 features

---

**Last Updated:** 2026-03-20
**Status:** Ready for implementation
