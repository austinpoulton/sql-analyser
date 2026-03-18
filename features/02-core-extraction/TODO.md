# TODO: Core Table & Column Extraction (Phase 2)

## Progress Summary

**Overall Status:** ~55% Complete (Phases 2A, 2B, 2C done; 2D, 2E, 2F remaining)

| Phase | Status | Test Coverage | Tickets |
|---|---|---|---|
| 2A - Basic Scope Traversal & Table Registry | ✅ **COMPLETE** | TC-001-01, TC-001-02 | sa-11ii, sa-2uo3, sa-no13, sa-xvv7 |
| 2B - Column Extraction from All Clauses | ✅ **COMPLETE** | TC-001-03 through TC-001-06 + multiple usages | sa-5fwj, sa-vgh8, sa-26na |
| 2C - CTE & Subquery Handling | ✅ **COMPLETE** | TC-001-07, TC-001-08, TC-001-09 + correlated | sa-vtdu, sa-0kit |
| 2D - Wildcard Detection | ⏳ **Pending** | TC-008-01, TC-008-02, TC-008-03 | sa-qdjl, sa-gkyx |
| 2E - Edge Cases & Finalization | ⏳ Pending | TC-001-10, self-join, UNION | sa-xabo, sa-p7wb, sa-rfd5, sa-sev6 |
| 2F - Documentation & Cleanup | ⏳ Pending | Code review, docstrings, coverage | sa-vytn, sa-cckm |

**Test Results:** 50 tests passing (39 Phase 1 + 11 Phase 2)

---

## Overview

This TODO breaks down the Phase 2 PRD into specific, actionable tasks. Each task should be small enough to complete in one focused session and have clear acceptance criteria.

**Dependencies:** Phase 1 (Domain Model) must be complete before starting Phase 2.

---

## Phase 2A: Basic Scope Traversal & Table Registry

### Task 2A.1: Create analyser.py skeleton

**Description:** Set up the basic module structure with imports and stub functions.

**Files:**
- `src/sql_analyser/analyser.py` (new)

**Subtasks:**
1. Create `src/sql_analyser/analyser.py`
2. Add module docstring
3. Add imports: `sqlglot`, `sqlglot.expressions as exp`, `sqlglot.optimizer.scope`
4. Import domain classes from `domain.py`
5. Create stub `analyse(expression: exp.Expression) -> AnalysisResult` function

**Acceptance Criteria:**
- Module imports without errors
- `analyse()` stub returns empty `AnalysisResult` with empty `DataModel`
- Type hints on all function signatures

**Estimated Time:** 15 minutes

---

### Task 2A.2: Implement build_qualified_name helper

**Description:** Create helper function to construct qualified table names from AST parts.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Implement `build_qualified_name(name: str, schema: str | None, catalog: str | None) -> str`
2. Join non-empty parts with `"."`
3. Handle empty/None values correctly
4. Add docstring with examples

**Acceptance Criteria:**
- `build_qualified_name("orders", None, None)` → `"orders"`
- `build_qualified_name("orders", "core_facts", None)` → `"core_facts.orders"`
- `build_qualified_name("orders", "core_facts", "my_catalog")` → `"my_catalog.core_facts.orders"`
- Empty strings treated same as None

**Estimated Time:** 15 minutes

---

### Task 2A.3: Implement scope traversal wrapper

**Description:** Wrap sqlglot's `traverse_scope` to return scopes in post-order.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Import `from sqlglot.optimizer.scope import traverse_scope, Scope`
2. Create `_enumerate_scopes(expression: exp.Expression) -> list[Scope]` helper
3. Call `traverse_scope(expression)` and collect results
4. Verify post-order (innermost first)
5. Add docstring explaining post-order rationale

**Acceptance Criteria:**
- Returns list of `Scope` objects
- CTE scopes appear before their parent scope
- Subquery scopes appear before their parent scope
- Function handles expressions with no scopes (returns root only)

**Estimated Time:** 20 minutes

---

### Task 2A.4: Implement table registration loop

**Description:** Build the table registry by iterating scopes and registering base tables.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Initialize `table_registry: dict[str, QueriedTable] = {}`
2. For each scope, iterate `scope.sources.items()`
3. Check if source is `exp.Table` (not `Scope`)
4. Extract `name`, `db`, `catalog` from `exp.Table`
5. Build qualified name
6. Create `QueriedTable` if not in registry
7. Skip Scope sources (CTEs/subqueries)

**Acceptance Criteria:**
- Base tables from all scopes added to registry
- CTE/subquery names do not appear in registry
- No duplicate tables (same qualified_name)
- `QueriedTable.name`, `schema_name`, `catalog_name` correctly populated

**Estimated Time:** 30 minutes

---

### Task 2A.5: Create conftest.py with basic fixtures

**Description:** Set up shared test fixtures for common SQL patterns.

**Files:**
- `tests/conftest.py` (new)

**Subtasks:**
1. Create `tests/conftest.py`
2. Import `pytest`, `sqlglot`
3. Add `@pytest.fixture` for `simple_select` (TC-001-01)
4. Add `@pytest.fixture` for `multi_table_join` (TC-001-02)
5. Use `dialect="postgres"` for all fixtures
6. Add module docstring explaining fixture purpose

**Fixtures to create:**
```python
@pytest.fixture
def simple_select():
    """SELECT id FROM users"""
    return sqlglot.parse_one("SELECT id FROM users", dialect="postgres")

@pytest.fixture
def multi_table_join():
    """SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id"""
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
        dialect="postgres"
    )
```

**Acceptance Criteria:**
- Both fixtures parse without errors
- Fixtures return `sqlglot.Expression` objects
- Module imports successfully in tests

**Estimated Time:** 20 minutes

---

### Task 2A.6: Create test_source_data_model.py skeleton

**Description:** Set up test module structure.

**Files:**
- `tests/test_source_data_model.py` (new)

**Subtasks:**
1. Create `tests/test_source_data_model.py`
2. Import `pytest`, domain classes, `analyse` function
3. Add module docstring: "Tests for FR-001: Source Data Model Extraction"
4. Create test stubs for TC-001-01 and TC-001-02

**Acceptance Criteria:**
- Module imports without errors
- Test discovery finds the module
- Stub tests are skipped (use `pytest.skip`)

**Estimated Time:** 15 minutes

---

### Task 2A.7: Write test for TC-001-01 (single table)

**Description:** Test simple single-table SELECT.

**Files:**
- `tests/test_source_data_model.py`

**Test SQL:**
```sql
SELECT id FROM users
```

**Subtasks:**
1. Implement `test_single_table_select(simple_select)`
2. Call `analyse(simple_select)`
3. Assert `len(result.data_model.tables) == 1`
4. Assert `table.name == "users"`
5. Assert `table.qualified_name == "users"`
6. Assert `len(table.columns) == 1`
7. Assert `col.name == "id"`
8. Assert `ColumnUsage.SELECT in col.usages`

**Acceptance Criteria:**
- Test passes
- Correct table extracted
- Correct column extracted
- Column has SELECT usage

**Estimated Time:** 15 minutes

---

### Task 2A.8: Write test for TC-001-02 (multi-table join)

**Description:** Test multi-table join with aliases.

**Files:**
- `tests/test_source_data_model.py`

**Test SQL:**
```sql
SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id
```

**Subtasks:**
1. Implement `test_multi_table_join(multi_table_join)`
2. Assert 2 tables extracted: `"orders"`, `"customers"`
3. Assert `"orders"` has columns: `"id"`, `"customer_id"`
4. Assert `"customers"` has columns: `"id"`, `"name"`
5. Assert column usages are correct (SELECT, JOIN_ON as appropriate)
6. Assert no table aliases (`o`, `c`) in output

**Acceptance Criteria:**
- Test passes
- Both tables extracted
- Aliases resolved to base tables
- Columns attributed to correct tables
- JOIN_ON columns have correct usage (Phase 2B will implement, Phase 2A may skip)

**Estimated Time:** 20 minutes

---

### Task 2A.9: Run and verify Phase 2A tests

**Description:** Ensure all Phase 2A tests pass.

**Subtasks:**
1. Run `uv run pytest tests/test_source_data_model.py::test_single_table_select -v`
2. Run `uv run pytest tests/test_source_data_model.py::test_multi_table_join -v`
3. Fix any failures
4. Verify no warnings

**Acceptance Criteria:**
- Both tests pass
- No pytest warnings
- Code coverage for new code ≥90%

**Estimated Time:** 15 minutes

---

## Phase 2B: Column Extraction from All Clauses

### Task 2B.1: Implement alias resolution helper

**Description:** Create function to resolve table aliases to qualified names.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Implement `_resolve_alias(alias: str, scope: Scope, alias_map: dict[str, str]) -> str | None`
2. If `alias` in `alias_map`, return `alias_map[alias]`
3. If `alias` is empty and scope has exactly one base table source, return that qualified_name
4. If `alias` maps to a `Scope` source (CTE), return `None`
5. Otherwise return `None`
6. Add docstring with examples

**Acceptance Criteria:**
- Direct alias lookup works
- Unqualified columns in single-table scope resolve correctly
- CTE references return None
- Unresolvable aliases return None

**Estimated Time:** 25 minutes

---

### Task 2B.2: Implement add_or_update_column helper

**Description:** Add or update a column in a table's column list.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Implement `_add_or_update_column(table: QueriedTable, column_name: str, usage: ColumnUsage) -> None`
2. Search for existing column by name
3. If found, add usage to existing `usages` set
4. If not found, create new `QueriedColumn` with name and usage
5. Append to `table.columns`
6. Handle case-sensitivity (preserve original case, match case-insensitively)

**Acceptance Criteria:**
- First reference creates new column
- Subsequent references add to usages set
- No duplicate columns
- Column order preserved (insertion order)

**Estimated Time:** 20 minutes

---

### Task 2B.3: Implement walk_in_scope helper

**Description:** Walk AST nodes within a clause, yielding nodes of a specific type.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Implement `_walk_in_scope(node: exp.Expression | None, node_type: type[exp.Expression]) -> Iterator[exp.Expression]`
2. If node is None, return empty iterator
3. Use `node.find_all(node_type)` to find all descendants
4. Yield each match
5. Add docstring

**Acceptance Criteria:**
- Returns iterator of matching nodes
- Handles None input gracefully
- Works for `exp.Column`, `exp.Table`, etc.

**Estimated Time:** 15 minutes

---

### Task 2B.4: Build per-scope alias map

**Description:** Create alias → qualified_name mapping for each scope.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. In main scope loop, initialize `alias_to_qualified: dict[str, str] = {}`
2. For each `(alias, source)` in `scope.sources.items()`
3. If `isinstance(source, exp.Table)`, add to map
4. Skip `Scope` sources
5. Store map for use in column extraction

**Acceptance Criteria:**
- Map contains all table aliases → qualified names
- CTE aliases excluded
- Map is per-scope (not global)

**Estimated Time:** 15 minutes

---

### Task 2B.5: Implement SELECT clause column extraction

**Description:** Extract columns from SELECT clause.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Get `scope.expression.expressions` (SELECT list)
2. For each expression in list, use `_walk_in_scope(expr, exp.Column)`
3. For each column, get `column.table` and `column.name`
4. Resolve table alias using `_resolve_alias`
5. If resolved, call `_add_or_update_column(table, column_name, ColumnUsage.SELECT)`
6. Skip if unresolved

**Acceptance Criteria:**
- Columns from SELECT list extracted
- Usage is `SELECT`
- Aliases resolved correctly
- Unresolved columns skipped (not crashed)

**Estimated Time:** 25 minutes

---

### Task 2B.6: Implement WHERE clause column extraction

**Description:** Extract columns from WHERE clause.

**Files:**
- `src/sql_analyser/analyser.py`
- `tests/conftest.py` (add fixture)

**Subtasks:**
1. Find WHERE node: `scope.expression.find(exp.Where)`
2. If found, use `_walk_in_scope(where_node, exp.Column)`
3. For each column, resolve and add with `ColumnUsage.WHERE`
4. Add fixture to conftest: `where_clause` (TC-001-03)
5. Write test in `test_source_data_model.py`

**Test SQL:**
```sql
SELECT id FROM orders WHERE region = 'EMEA'
```

**Acceptance Criteria:**
- Columns in WHERE extracted
- Usage is `WHERE`
- Test TC-001-03 passes

**Estimated Time:** 30 minutes

---

### Task 2B.7: Implement GROUP BY clause column extraction

**Description:** Extract columns from GROUP BY clause.

**Files:**
- `src/sql_analyser/analyser.py`
- `tests/conftest.py` (add fixture)

**Subtasks:**
1. Find GROUP BY node: `scope.expression.find(exp.Group)`
2. If found, use `_walk_in_scope(group_node, exp.Column)`
3. For each column, resolve and add with `ColumnUsage.GROUP_BY`
4. Add fixture: `group_by_clause` (TC-001-04)
5. Write test

**Test SQL:**
```sql
SELECT product_id, COUNT(*) FROM sales GROUP BY product_id
```

**Acceptance Criteria:**
- GROUP BY columns extracted
- Usage is `GROUP_BY`
- Test TC-001-04 passes

**Estimated Time:** 25 minutes

---

### Task 2B.8: Implement HAVING clause column extraction

**Description:** Extract columns from HAVING clause.

**Files:**
- `src/sql_analyser/analyser.py`
- `tests/conftest.py` (add fixture)

**Subtasks:**
1. Find HAVING node: `scope.expression.find(exp.Having)`
2. Extract columns with usage `ColumnUsage.HAVING`
3. Add fixture: `having_clause` (TC-001-05)
4. Write test

**Test SQL:**
```sql
SELECT product_id, COUNT(*) FROM sales GROUP BY product_id HAVING COUNT(*) > 100
```

**Acceptance Criteria:**
- HAVING columns extracted
- Usage is `HAVING`
- Test TC-001-05 passes

**Estimated Time:** 25 minutes

---

### Task 2B.9: Implement ORDER BY clause column extraction

**Description:** Extract columns from ORDER BY clause.

**Files:**
- `src/sql_analyser/analyser.py`
- `tests/conftest.py` (add fixture)

**Subtasks:**
1. Find ORDER BY node: `scope.expression.find(exp.Order)`
2. Extract columns with usage `ColumnUsage.ORDER_BY`
3. Add fixture: `order_by_clause` (TC-001-06)
4. Write test

**Test SQL:**
```sql
SELECT id, name FROM products ORDER BY name, id
```

**Acceptance Criteria:**
- ORDER BY columns extracted
- Usage is `ORDER_BY`
- Test TC-001-06 passes

**Estimated Time:** 25 minutes

---

### Task 2B.10: Implement JOIN ON clause column extraction

**Description:** Extract columns from JOIN ON conditions.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Find all JOIN nodes: `scope.expression.find_all(exp.Join)`
2. For each join, get `join.args.get("on")`
3. If ON condition exists, extract columns with usage `ColumnUsage.JOIN_ON`
4. Handle both sides of equi-joins

**Acceptance Criteria:**
- JOIN ON columns extracted
- Usage is `JOIN_ON`
- Both sides of condition captured
- Test TC-001-02 now fully passes (JOIN_ON columns have correct usage)

**Estimated Time:** 30 minutes

---

### Task 2B.11: Test multiple usages accumulation

**Description:** Verify that columns appearing in multiple clauses accumulate usages.

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL:**
```sql
SELECT product_id, COUNT(*)
FROM sales
WHERE region = 'EMEA'
GROUP BY product_id
HAVING COUNT(*) > 100
ORDER BY product_id
```

**Subtasks:**
1. Add fixture: `multiple_usages`
2. Write test asserting `product_id` has 4 usages: SELECT, GROUP_BY, HAVING, ORDER_BY
3. Write test asserting `region` has 1 usage: WHERE

**Acceptance Criteria:**
- Single column with multiple usages
- Usages set contains all expected values
- No duplicate columns

**Estimated Time:** 20 minutes

---

### Task 2B.12: Run and verify Phase 2B tests

**Description:** Ensure all Phase 2B tests pass.

**Subtasks:**
1. Run `uv run pytest tests/test_source_data_model.py -v`
2. Fix any failures
3. Verify TC-001-01 through TC-001-06 pass
4. Check code coverage

**Acceptance Criteria:**
- All Phase 2A + 2B tests pass
- Coverage ≥90% for `analyser.py`
- No warnings

**Estimated Time:** 20 minutes

---

## Phase 2C: CTE & Subquery Handling

### Task 2C.1: Update table registration to skip CTE sources

**Description:** Ensure CTE/subquery sources are not registered as tables.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. In table registration loop, check `isinstance(source, Scope)`
2. If true, skip (do not add to registry)
3. Add comment explaining why CTEs are skipped
4. Ensure only `exp.Table` sources are registered

**Acceptance Criteria:**
- CTE names do not appear in table registry
- Base tables from CTE bodies are registered
- No functional change if already implemented in 2A.4

**Estimated Time:** 10 minutes (verification/refinement)

---

### Task 2C.2: Handle CTE references in alias resolution

**Description:** When a column's table reference is a CTE, skip attribution.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. In `_resolve_alias`, check if `scope.sources.get(alias)` is a `Scope`
2. If yes, return `None` (CTE reference, skip)
3. Add docstring note about CTE handling

**Acceptance Criteria:**
- Columns referencing CTE aliases return None
- Such columns are skipped in column extraction
- No crash or incorrect attribution

**Estimated Time:** 15 minutes

---

### Task 2C.3: Add CTE test fixture and test

**Description:** Test simple CTE resolution.

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL (TC-001-07):**
```sql
WITH tmp AS (SELECT order_id FROM orders)
SELECT order_id FROM tmp
```

**Subtasks:**
1. Add fixture: `simple_cte`
2. Write test asserting:
   - One table: `"orders"`
   - Column `"order_id"` with SELECT usage
   - No table named `"tmp"`

**Acceptance Criteria:**
- Test passes
- CTE alias not in table list
- Base table extracted
- Column attributed to base table

**Estimated Time:** 25 minutes

---

### Task 2C.4: Add nested CTE test

**Description:** Test nested CTEs (3 levels).

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL (TC-001-08):**
```sql
WITH
  cte1 AS (SELECT id FROM users),
  cte2 AS (SELECT id FROM cte1 WHERE id > 10),
  cte3 AS (SELECT id FROM cte2)
SELECT id FROM cte3
```

**Subtasks:**
1. Add fixture: `nested_cte`
2. Write test asserting:
   - One table: `"users"`
   - Column `"id"` (may have multiple usages: SELECT, WHERE)
   - No CTE aliases in tables

**Acceptance Criteria:**
- Test passes
- Only base table extracted
- Post-order traversal handles nesting correctly

**Estimated Time:** 25 minutes

---

### Task 2C.5: Add subquery test

**Description:** Test subquery in FROM clause.

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL (TC-001-09):**
```sql
SELECT a FROM (SELECT a FROM (SELECT a FROM t1) x) y
```

**Subtasks:**
1. Add fixture: `nested_subquery`
2. Write test asserting:
   - One table: `"t1"`
   - Column `"a"` with SELECT usage
   - No subquery aliases (`x`, `y`) in tables

**Acceptance Criteria:**
- Test passes
- Deep nesting handled correctly
- Single base table extracted

**Estimated Time:** 25 minutes

---

### Task 2C.6: Add correlated subquery test

**Description:** Test subquery referencing outer scope column.

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL:**
```sql
SELECT o.id
FROM orders o
WHERE EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id)
```

**Subtasks:**
1. Add fixture: `correlated_subquery`
2. Write test asserting:
   - Two tables: `"orders"`, `"order_items"`
   - `"orders"` has column `"id"` (SELECT, WHERE usages)
   - `"order_items"` has column `"order_id"` (WHERE usage)

**Acceptance Criteria:**
- Both tables extracted
- Columns from both scopes attributed correctly
- Outer scope column references in subquery handled

**Estimated Time:** 30 minutes

---

### Task 2C.7: Run and verify Phase 2C tests

**Description:** Ensure all CTE/subquery tests pass.

**Subtasks:**
1. Run `uv run pytest tests/test_source_data_model.py -v -k "cte or subquery"`
2. Fix any failures
3. Verify TC-001-07, TC-001-08, TC-001-09 pass

**Acceptance Criteria:**
- All CTE/subquery tests pass
- No CTE aliases in output
- Base tables correctly extracted

**Estimated Time:** 20 minutes

---

## Phase 2D: Wildcard Detection

### Task 2D.1: Implement unqualified wildcard detection

**Description:** Detect `SELECT *` and flag all base tables.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. After column extraction, check `scope.stars`
2. For each star, check if `star.table` is empty (unqualified `SELECT *`)
3. If unqualified, flag `has_wildcard = True` on all base tables in scope
4. Use alias_to_qualified map to identify base tables

**Acceptance Criteria:**
- `SELECT * FROM t1` → `t1.has_wildcard = True`
- `SELECT * FROM t1, t2` → both flagged
- Columns list may be empty

**Estimated Time:** 25 minutes

---

### Task 2D.2: Implement qualified wildcard detection

**Description:** Detect `table.*` and flag that specific table.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. For each star in `scope.stars`, check if `star.table` is not empty
2. Resolve table alias using `_resolve_alias`
3. If resolved, flag that table's `has_wildcard = True`

**Acceptance Criteria:**
- `SELECT t1.* FROM t1` → `t1.has_wildcard = True`
- `SELECT t1.*, t2.id FROM t1, t2` → only `t1` flagged
- Explicit columns still extracted

**Estimated Time:** 20 minutes

---

### Task 2D.3: Add wildcard test fixtures

**Description:** Create fixtures for wildcard test cases.

**Files:**
- `tests/conftest.py`

**Subtasks:**
1. Add `unqualified_wildcard` fixture (TC-008-01): `SELECT * FROM products`
2. Add `qualified_wildcard` fixture (TC-008-02): `SELECT t1.*, t2.id FROM table1 t1, table2 t2`
3. Add `wildcard_with_columns` fixture (TC-008-03): `SELECT *, status FROM orders WHERE region = 'US'`

**Acceptance Criteria:**
- All three fixtures parse successfully
- Fixtures ready for testing

**Estimated Time:** 15 minutes

---

### Task 2D.4: Write wildcard tests

**Description:** Test all wildcard scenarios.

**Files:**
- `tests/test_source_data_model.py`

**Subtasks:**
1. Write `test_unqualified_wildcard` (TC-008-01)
   - Assert `products.has_wildcard = True`
   - Assert no columns invented
2. Write `test_qualified_wildcard` (TC-008-02)
   - Assert `table1.has_wildcard = True`
   - Assert `table2.has_wildcard = False`
   - Assert `table2` has column `"id"`
3. Write `test_wildcard_with_explicit_columns` (TC-008-03)
   - Assert `orders.has_wildcard = True`
   - Assert columns `"status"` (SELECT) and `"region"` (WHERE) extracted

**Acceptance Criteria:**
- All three tests pass
- Wildcard flag correctly set
- No column invention
- Explicit columns still captured

**Estimated Time:** 30 minutes

---

### Task 2D.5: Run and verify Phase 2D tests

**Description:** Ensure all wildcard tests pass.

**Subtasks:**
1. Run `uv run pytest tests/test_source_data_model.py::test_unqualified_wildcard -v`
2. Run `uv run pytest tests/test_source_data_model.py::test_qualified_wildcard -v`
3. Run `uv run pytest tests/test_source_data_model.py::test_wildcard_with_explicit_columns -v`
4. Fix any failures

**Acceptance Criteria:**
- TC-008-01, TC-008-02, TC-008-03 pass
- All previous tests still pass

**Estimated Time:** 15 minutes

---

## Phase 2E: Edge Cases & Finalization

### Task 2E.1: Add self-join test

**Description:** Test self-join scenario (same table, different aliases).

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL (TC-001-10):**
```sql
SELECT a.id, b.id
FROM users a
JOIN users b ON a.manager_id = b.id
```

**Subtasks:**
1. Add fixture: `self_join`
2. Write test asserting:
   - One table: `"users"`
   - Columns: `"id"` (SELECT, JOIN_ON), `"manager_id"` (JOIN_ON)
   - Usages accumulated from both aliases

**Acceptance Criteria:**
- Test passes
- Single table in output
- Columns from both aliases merged
- No duplicate tables

**Estimated Time:** 25 minutes

---

### Task 2E.2: Add UNION test

**Description:** Test UNION query with multiple SELECT arms.

**Files:**
- `tests/conftest.py` (add fixture)
- `tests/test_source_data_model.py`

**Test SQL:**
```sql
SELECT id FROM orders
UNION
SELECT id FROM archived_orders
```

**Subtasks:**
1. Add fixture: `union_query`
2. Write test asserting:
   - Two tables: `"orders"`, `"archived_orders"`
   - Both have column `"id"` with SELECT usage

**Acceptance Criteria:**
- Test passes
- Tables from both arms extracted
- Post-order traversal handles UNION scopes

**Estimated Time:** 25 minutes

---

### Task 2E.3: Add error handling for unresolved aliases

**Description:** Handle unresolved table aliases gracefully.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. In column extraction, when `_resolve_alias` returns `None`, skip column
2. Add logging: `logger.warning(f"Unresolved alias for column {column.name}")`
3. Do not crash or raise exception
4. Continue processing other columns

**Acceptance Criteria:**
- Unresolved aliases logged as warnings
- Analysis continues without crash
- Resolvable columns still extracted

**Estimated Time:** 20 minutes

---

### Task 2E.4: Add logging infrastructure

**Description:** Set up Python logging for debugging.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Import `logging`
2. Create module logger: `logger = logging.getLogger(__name__)`
3. Add debug logs at key points:
   - Scope enumeration: `logger.debug(f"Found {len(scopes)} scopes")`
   - Table registration: `logger.debug(f"Registered table {qualified_name}")`
   - Column extraction: `logger.debug(f"Added column {col_name} to {table_name}")`

**Acceptance Criteria:**
- Logging set up
- Debug logs useful for troubleshooting
- No log output by default (user must configure)

**Estimated Time:** 20 minutes

---

### Task 2E.5: Update __init__.py with public API

**Description:** Export analyse function and domain classes.

**Files:**
- `src/sql_analyser/__init__.py`

**Subtasks:**
1. Import `analyse` from `analyser`
2. Re-export all domain classes from `domain`
3. Define `__all__` list
4. Add module docstring

**Public API:**
```python
from .analyser import analyse
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
    "analyse",
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

**Acceptance Criteria:**
- `from sql_analyser import analyse` works
- All domain classes importable
- No breaking changes to existing Phase 1 code

**Estimated Time:** 15 minutes

---

### Task 2E.6: Run full test suite

**Description:** Verify all Phase 2 tests pass.

**Subtasks:**
1. Run `uv run pytest tests/test_source_data_model.py -v`
2. Run `uv run pytest tests/test_domain_model.py -v` (Phase 1 regression)
3. Fix any failures
4. Verify no warnings

**Acceptance Criteria:**
- All TC-001-01 through TC-001-10 pass
- All TC-008-01 through TC-008-03 pass
- Phase 1 tests still pass
- No pytest warnings

**Estimated Time:** 20 minutes

---

### Task 2E.7: Check code coverage

**Description:** Ensure ≥90% coverage on analyser.py.

**Subtasks:**
1. Run `uv run pytest --cov=src/sql_analyser/analyser --cov-report=term-missing`
2. Identify uncovered lines
3. Add tests or remove dead code to reach 90%

**Acceptance Criteria:**
- Coverage ≥90% on `analyser.py`
- All critical paths tested
- No untested error paths

**Estimated Time:** 30 minutes

---

### Task 2E.8: Update AGENTS.md

**Description:** Update module layout in AGENTS.md to reflect Phase 2 implementation.

**Files:**
- `AGENTS.md`

**Subtasks:**
1. Update module layout section to mark `analyser.py` as implemented
2. Update test layout to mark `conftest.py` and `test_source_data_model.py` as implemented
3. Add note: "Phase 2 (Core extraction) complete"

**Acceptance Criteria:**
- AGENTS.md reflects current state
- Module status clear for next phases

**Estimated Time:** 10 minutes

---

### Task 2E.9: Write integration test

**Description:** End-to-end test with complex SQL combining multiple features.

**Files:**
- `tests/test_source_data_model.py`

**Test SQL:**
```sql
WITH regional_sales AS (
  SELECT region, product_id, SUM(amount) as total
  FROM sales
  WHERE year = 2023
  GROUP BY region, product_id
)
SELECT rs.region, p.name, rs.total
FROM regional_sales rs
JOIN products p ON rs.product_id = p.id
WHERE rs.total > 1000
ORDER BY rs.total DESC
```

**Subtasks:**
1. Add fixture: `complex_integration`
2. Write test asserting:
   - Three tables: `"sales"`, `"products"`, (regional_sales is CTE)
   - `"sales"` columns: `"region"` (GROUP_BY, SELECT), `"product_id"` (GROUP_BY, SELECT), `"amount"` (SELECT), `"year"` (WHERE)
   - `"products"` columns: `"id"` (JOIN_ON), `"name"` (SELECT)
   - No CTE in tables
   - All usages correct

**Acceptance Criteria:**
- Integration test passes
- Complex SQL handled correctly
- All features work together

**Estimated Time:** 40 minutes

---

## Phase 2F: Documentation & Cleanup

### Task 2F.1: Add docstrings to all functions

**Description:** Ensure all functions have Google-style docstrings.

**Files:**
- `src/sql_analyser/analyser.py`

**Subtasks:**
1. Review all functions
2. Add/update docstrings with:
   - Brief description
   - Args
   - Returns
   - Examples (for public functions)

**Acceptance Criteria:**
- All public functions have docstrings
- All private helpers have docstrings
- Docstring format consistent (Google style)

**Estimated Time:** 30 minutes

---

### Task 2F.2: Add type hints to all functions

**Description:** Verify complete type annotation coverage.

**Subtasks:**
1. Run `mypy src/sql_analyser/analyser.py --strict`
2. Fix any type errors
3. Add missing type hints
4. Ensure return types annotated

**Acceptance Criteria:**
- `mypy --strict` passes with no errors
- All function signatures type-annotated
- No `Any` types unless necessary

**Estimated Time:** 30 minutes

---

### Task 2F.3: Code review and refactoring

**Description:** Review code for clarity and simplicity.

**Subtasks:**
1. Check for code duplication
2. Extract repeated logic into helpers
3. Simplify complex conditionals
4. Add comments for non-obvious logic
5. Verify naming clarity

**Acceptance Criteria:**
- No code duplication
- Functions are focused (single responsibility)
- Code is readable and maintainable

**Estimated Time:** 45 minutes

---

### Task 2F.4: Run linting and formatting

**Description:** Ensure code adheres to project style.

**Subtasks:**
1. Run `uv run ruff check .`
2. Fix any linting errors
3. Run `uv run ruff format .`
4. Commit formatting changes

**Acceptance Criteria:**
- No ruff check errors
- Code formatted consistently
- Pre-commit hook passes

**Estimated Time:** 15 minutes

---

### Task 2F.5: Final test run

**Description:** Run full test suite one last time.

**Subtasks:**
1. Run `uv run pytest -v`
2. Verify all tests pass
3. Check coverage report
4. No warnings

**Acceptance Criteria:**
- All tests pass (Phase 1 + Phase 2)
- Coverage ≥90%
- Zero warnings
- Pre-commit hook passes

**Estimated Time:** 15 minutes

---

## Summary Checklist

### Phase 2A: Basic Scope Traversal & Table Registry
- [ ] Task 2A.1: Create analyser.py skeleton
- [ ] Task 2A.2: Implement build_qualified_name helper
- [ ] Task 2A.3: Implement scope traversal wrapper
- [ ] Task 2A.4: Implement table registration loop
- [ ] Task 2A.5: Create conftest.py with basic fixtures
- [ ] Task 2A.6: Create test_source_data_model.py skeleton
- [ ] Task 2A.7: Write test for TC-001-01 (single table)
- [ ] Task 2A.8: Write test for TC-001-02 (multi-table join)
- [ ] Task 2A.9: Run and verify Phase 2A tests

### Phase 2B: Column Extraction from All Clauses
- [ ] Task 2B.1: Implement alias resolution helper
- [ ] Task 2B.2: Implement add_or_update_column helper
- [ ] Task 2B.3: Implement walk_in_scope helper
- [ ] Task 2B.4: Build per-scope alias map
- [ ] Task 2B.5: Implement SELECT clause column extraction
- [ ] Task 2B.6: Implement WHERE clause column extraction
- [ ] Task 2B.7: Implement GROUP BY clause column extraction
- [ ] Task 2B.8: Implement HAVING clause column extraction
- [ ] Task 2B.9: Implement ORDER BY clause column extraction
- [ ] Task 2B.10: Implement JOIN ON clause column extraction
- [ ] Task 2B.11: Test multiple usages accumulation
- [ ] Task 2B.12: Run and verify Phase 2B tests

### Phase 2C: CTE & Subquery Handling
- [ ] Task 2C.1: Update table registration to skip CTE sources
- [ ] Task 2C.2: Handle CTE references in alias resolution
- [ ] Task 2C.3: Add CTE test fixture and test
- [ ] Task 2C.4: Add nested CTE test
- [ ] Task 2C.5: Add subquery test
- [ ] Task 2C.6: Add correlated subquery test
- [ ] Task 2C.7: Run and verify Phase 2C tests

### Phase 2D: Wildcard Detection
- [ ] Task 2D.1: Implement unqualified wildcard detection
- [ ] Task 2D.2: Implement qualified wildcard detection
- [ ] Task 2D.3: Add wildcard test fixtures
- [ ] Task 2D.4: Write wildcard tests
- [ ] Task 2D.5: Run and verify Phase 2D tests

### Phase 2E: Edge Cases & Finalization
- [ ] Task 2E.1: Add self-join test
- [ ] Task 2E.2: Add UNION test
- [ ] Task 2E.3: Add error handling for unresolved aliases
- [ ] Task 2E.4: Add logging infrastructure
- [ ] Task 2E.5: Update __init__.py with public API
- [ ] Task 2E.6: Run full test suite
- [ ] Task 2E.7: Check code coverage
- [ ] Task 2E.8: Update AGENTS.md
- [ ] Task 2E.9: Write integration test

### Phase 2F: Documentation & Cleanup
- [ ] Task 2F.1: Add docstrings to all functions
- [ ] Task 2F.2: Add type hints to all functions
- [ ] Task 2F.3: Code review and refactoring
- [ ] Task 2F.4: Run linting and formatting
- [ ] Task 2F.5: Final test run

---

## Estimated Total Time

- **Phase 2A:** ~2.5 hours
- **Phase 2B:** ~4.5 hours
- **Phase 2C:** ~2.5 hours
- **Phase 2D:** ~1.5 hours
- **Phase 2E:** ~4 hours
- **Phase 2F:** ~2 hours

**Total:** ~17 hours (spread over multiple sessions)

---

## Dependencies

- Phase 1 (Domain Model) must be complete
- sqlglot ≥25.29.0 installed
- pytest configured
- ruff configured for linting

---

## Success Criteria

- All FR-001 test cases (TC-001-01 through TC-001-10) pass
- All FR-008 test cases (TC-008-01 through TC-008-03) pass
- Code coverage ≥90% on `analyser.py`
- No ruff errors
- All tests pass with no warnings
- Pre-commit hook passes
- Public API exported from `__init__.py`
