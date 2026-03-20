# Feature Specification: FR-002 — Relationship Extraction

**Phase:** 3 — Relationships
**Status:** Draft
**Dependencies:** Phase 2 (Core Extraction) ✅ Complete
**Functional Requirement:** FR-002

---

## 1. Overview

### 1.1 Purpose

Extract table relationships from SQL queries by analyzing JOIN conditions and implicit WHERE clause equi-joins. Relationships capture how tables are connected in the query, forming the basis for entity-relationship diagrams and data lineage visualization.

### 1.2 Scope

**In scope:**
- Explicit JOIN relationships (INNER, LEFT, RIGHT, FULL, CROSS)
- Implicit relationships from WHERE clause equi-joins (`WHERE a.id = b.id`)
- Multi-column relationships (composite keys)
- Self-joins (table related to itself via different aliases)
- Relationships through CTE references (resolve to base tables)
- Relationship deduplication using canonical keys

**Out of scope:**
- Non-equi-join conditions (e.g., `ON a.val > b.val`)
- Transitive relationship inference
- Foreign key constraint detection from DDL
- Relationship cardinality (1:1, 1:N, N:M)
- Relationship directionality (left vs right table designation is arbitrary)

### 1.3 Success Criteria

- All explicit JOIN relationships extracted with correct table and column references
- Implicit WHERE clause relationships detected
- Multi-column relationships properly grouped
- Self-joins create valid relationships referencing the same table
- CTE aliases resolved to base tables in relationships
- No duplicate relationships (symmetric deduplication via canonical_key)
- All 7 test cases (TC-002-01 through TC-002-07) passing

---

## 2. Background

### 2.1 Current State

**Phase 2 (Complete)** provides:
- Scope traversal with `traverse_scope()` post-order iteration
- Base table registry (`dict[str, QueriedTable]`)
- Alias resolution mapping (`alias_to_qualified`)
- Column extraction from all SQL clauses
- Wildcard detection

**Existing data model:**
```python
class Relationship(BaseModel):
    left_table: str          # qualified_name
    left_columns: list[str]  # column names
    right_table: str         # qualified_name
    right_columns: list[str] # column names

    @property
    def canonical_key(self) -> tuple:
        """Symmetric key for deduplication."""
        ...
```

### 2.2 Technical Context

**sqlglot AST structure:**
- `exp.Join` nodes contain join type and ON condition
- `exp.Where` nodes contain filter predicates
- Equi-join predicates are `exp.EQ` nodes with `exp.Column` operands
- Complex conditions may have nested `exp.And`, `exp.Or` nodes

**Key challenge:** Resolving aliases in join conditions to base tables, especially when JOINing on CTE references.

---

## 3. Functional Requirements

### 3.1 Explicit JOIN Extraction

**FR-002-01:** Extract relationships from explicit JOIN clauses

**Behavior:**
- Traverse all `exp.Join` nodes in each scope
- Parse ON condition for equality predicates (`col_a = col_b`)
- Resolve both column table aliases to qualified base table names
- Group column pairs by table pair (for multi-column keys)
- Create `Relationship` object with deduplicated column lists

**Example:**
```sql
SELECT o.id, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
```

**Expected output:**
```python
Relationship(
    left_table="orders",
    left_columns=["customer_id"],
    right_table="customers",
    right_columns=["id"]
)
```

### 3.2 Implicit WHERE Join Extraction

**FR-002-02:** Extract relationships from WHERE clause equi-joins

**Behavior:**
- Find `exp.Where` node in scope
- Walk expression tree to find all `exp.EQ` predicates
- For each equality with qualified columns (`col_a = col_b`):
  - Check both operands are `exp.Column` instances
  - Resolve table aliases to qualified names
  - Skip if both columns from same table
  - Create relationship

**Example:**
```sql
SELECT o.id, c.name
FROM orders o, customers c
WHERE o.customer_id = c.id
```

**Expected output:** Same as FR-002-01

### 3.3 Multi-Column Relationships

**FR-002-03:** Support composite key relationships

**Behavior:**
- Accumulate multiple equi-predicates between the same table pair
- Store all column pairs in `left_columns` and `right_columns` lists
- Maintain column order consistency

**Example:**
```sql
SELECT * FROM orders o
JOIN shipments s ON o.region = s.region AND o.order_id = s.order_id
```

**Expected output:**
```python
Relationship(
    left_table="orders",
    left_columns=["region", "order_id"],
    right_table="shipments",
    right_columns=["region", "order_id"]
)
```

### 3.4 Self-Join Relationships

**FR-002-04:** Handle self-joins correctly

**Behavior:**
- When both sides of a join reference the same base table (different aliases)
- Create relationship with `left_table == right_table`
- Preserve correct column distinctions

**Example:**
```sql
SELECT a.id, b.id
FROM users a
JOIN users b ON a.manager_id = b.id
```

**Expected output:**
```python
Relationship(
    left_table="users",
    left_columns=["manager_id"],
    right_table="users",
    right_columns=["id"]
)
```

### 3.5 CTE Alias Resolution

**FR-002-05:** Resolve CTE references to base tables

**Behavior:**
- When a JOIN references a CTE alias (e.g., `JOIN cte_name ON ...`)
- Trace through the CTE's scope to find the base table providing the joined column
- Use base table's qualified name in the Relationship

**Example:**
```sql
WITH tmp AS (SELECT order_id, total FROM orders)
SELECT t.order_id, p.name
FROM tmp t
JOIN products p ON t.order_id = p.order_id
```

**Expected output:**
```python
Relationship(
    left_table="orders",      # resolved from tmp CTE
    left_columns=["order_id"],
    right_table="products",
    right_columns=["order_id"]
)
```

**Note:** This is complex and may require recursive scope traversal. See §4.2 for algorithm.

### 3.6 Relationship Deduplication

**FR-002-06:** Eliminate duplicate relationships

**Behavior:**
- After accumulating all relationships from all scopes
- Deduplicate using `canonical_key` property (symmetric comparison)
- Preserve one representative from each unique relationship

**Example:**
```sql
SELECT * FROM orders o
JOIN customers c ON o.customer_id = c.id
UNION
SELECT * FROM orders o
JOIN customers c ON o.customer_id = c.id
```

**Expected output:** Only ONE relationship, not two

---

## 4. Technical Design

### 4.1 Architecture

**Extend existing `analyser.py`** — no new modules needed.

```
analyse(expression) -> AnalysisResult
    │
    ├─ Step 1: traverse_scope(expression) → scopes
    ├─ Step 2: For each scope:
    │   ├─ 2a: Register base tables → table_registry, alias_to_qualified
    │   ├─ 2b: Extract columns → update table_registry
    │   ├─ 2c: Handle wildcards → update table_registry
    │   └─ 2d: Extract relationships → accumulate in relationships list  ← NEW
    ├─ Step 3: Deduplicate relationships → unique_relationships  ← NEW
    └─ Step 4: Return AnalysisResult(DataModel(tables, relationships))
```

### 4.2 Relationship Extraction Algorithm

#### Step 2d: Extract Relationships (per scope)

```python
# Accumulator for all relationships across scopes
all_relationships: list[Relationship] = []

# For each scope:
for scope in scopes:
    # ... existing table/column extraction ...

    # Step 2d.1: Extract from explicit JOINs
    joins = _walk_in_scope(scope.expression, exp.Join)
    for join in joins:
        on_condition = join.args.get("on")
        if on_condition:
            # Find all EQ predicates
            eq_predicates = _walk_in_scope(on_condition, exp.EQ)

            # Group by table pair
            table_pair_map: dict[tuple[str, str], list[tuple[str, str]]] = {}

            for eq in eq_predicates:
                left_col, right_col = eq.left, eq.right
                if isinstance(left_col, exp.Column) and isinstance(right_col, exp.Column):
                    left_table_alias = str(left_col.table)
                    right_table_alias = str(right_col.table)

                    # Resolve aliases to qualified names
                    left_qn = _resolve_alias(left_table_alias, scope, alias_to_qualified)
                    right_qn = _resolve_alias(right_table_alias, scope, alias_to_qualified)

                    if left_qn and right_qn:
                        # Accumulate column pairs
                        key = (left_qn, right_qn)
                        if key not in table_pair_map:
                            table_pair_map[key] = []
                        table_pair_map[key].append((
                            str(left_col.name),
                            str(right_col.name)
                        ))

            # Create relationships
            for (left_qn, right_qn), col_pairs in table_pair_map.items():
                left_cols = [pair[0] for pair in col_pairs]
                right_cols = [pair[1] for pair in col_pairs]
                all_relationships.append(Relationship(
                    left_table=left_qn,
                    left_columns=left_cols,
                    right_table=right_qn,
                    right_columns=right_cols
                ))

    # Step 2d.2: Extract from WHERE clause implicit joins
    where_clause = scope.expression.find(exp.Where)
    if where_clause:
        eq_predicates = _walk_in_scope(where_clause, exp.EQ)

        for eq in eq_predicates:
            left_col, right_col = eq.left, eq.right
            if isinstance(left_col, exp.Column) and isinstance(right_col, exp.Column):
                left_table_alias = str(left_col.table)
                right_table_alias = str(right_col.table)

                # Skip if not qualified (likely filtering, not join)
                if not left_table_alias or not right_table_alias:
                    continue

                # Resolve aliases
                left_qn = _resolve_alias(left_table_alias, scope, alias_to_qualified)
                right_qn = _resolve_alias(right_table_alias, scope, alias_to_qualified)

                # Skip if same table (self-comparison, not join)
                # Note: Self-joins from explicit JOIN already handled
                if left_qn and right_qn and left_qn != right_qn:
                    all_relationships.append(Relationship(
                        left_table=left_qn,
                        left_columns=[str(left_col.name)],
                        right_table=right_qn,
                        right_columns=[str(right_col.name)]
                    ))

# Step 3: Deduplicate relationships
seen_keys = set()
unique_relationships = []
for rel in all_relationships:
    if rel.canonical_key not in seen_keys:
        seen_keys.add(rel.canonical_key)
        unique_relationships.append(rel)
```

#### CTE Resolution Algorithm (Optional Enhancement)

**Note:** Initial implementation may skip CTE resolution and only handle base table JOINs. CTE resolution can be added incrementally.

```python
def _resolve_cte_column_to_base_table(
    cte_alias: str,
    column_name: str,
    scope: Scope
) -> tuple[str, str] | None:
    """
    Resolve a CTE column reference to its base table and column.

    Returns:
        (qualified_table_name, base_column_name) or None if unresolvable
    """
    source = scope.sources.get(cte_alias)
    if not isinstance(source, Scope):
        return None  # Not a CTE

    # Find the column in the CTE's SELECT list
    cte_scope = source
    if not hasattr(cte_scope.expression, 'expressions'):
        return None

    for select_expr in cte_scope.expression.expressions:
        # Check if this expression has an alias matching column_name
        alias = select_expr.alias_or_name
        if alias == column_name:
            # Find the source column
            columns = _walk_in_scope(select_expr, exp.Column)
            if columns:
                col = columns[0]  # Take first column
                col_table_alias = str(col.table)
                # Recursively resolve (in case of nested CTEs)
                result = _resolve_alias_or_cte(col_table_alias, cte_scope, ...)
                return (result, str(col.name))

    return None
```

### 4.3 Data Flow

```
┌─────────────────┐
│ Scope with JOIN │
└────────┬────────┘
         │
         ▼
┌────────────────────┐
│ Parse ON condition │  → Find exp.EQ predicates
└────────┬───────────┘
         │
         ▼
┌───────────────────────┐
│ Resolve table aliases │  → Use alias_to_qualified map
└────────┬──────────────┘
         │
         ▼
┌──────────────────────┐
│ Group by table pair  │  → Accumulate column pairs
└────────┬─────────────┘
         │
         ▼
┌───────────────────────┐
│ Create Relationship   │  → Append to all_relationships
└────────┬──────────────┘
         │
         ▼
┌──────────────────────┐
│ Deduplicate (Step 3) │  → Use canonical_key
└────────┬─────────────┘
         │
         ▼
    DataModel.relationships
```

### 4.4 Edge Cases

| Case | Behavior |
|------|----------|
| Non-equi-join (`ON a.val > b.val`) | Skip — only extract equi-joins |
| Complex conditions (`ON a.id = b.id AND a.status = 'active'`) | Extract equi-join, ignore filter |
| Unqualified columns in WHERE (`WHERE status = 'active'`) | Skip — not a join predicate |
| Self-join | Create relationship with `left_table == right_table` |
| CTE in JOIN | Resolve to base table (Phase 3A: basic; Phase 3B: CTE support) |
| Multiple JOINs on same table pair | Merge into single multi-column relationship |
| CROSS JOIN (no ON condition) | No relationship created |

---

## 5. Implementation Plan

### Phase 3A: Basic Relationship Extraction

**Scope:** FR-002-01, FR-002-02, FR-002-03, FR-002-04, FR-002-06

**Tasks:**
1. Add relationship accumulator in `analyse()`
2. Implement explicit JOIN extraction (Step 2d.1)
3. Implement implicit WHERE extraction (Step 2d.2)
4. Implement multi-column grouping logic
5. Implement deduplication (Step 3)
6. Add test fixtures for TC-002-01 through TC-002-04, TC-002-06, TC-002-07
7. Add `test_relationships.py` with 7 test cases
8. Verify all tests pass

**Estimated effort:** 4-6 hours

### Phase 3B: CTE Resolution (Required)

**Scope:** FR-002-05

**Tasks:**
1. Implement `_resolve_cte_column_to_base_table()`
2. Update `_resolve_alias()` to handle CTE references
3. Add test fixture for TC-002-05
4. Add test case `test_cte_join()`
5. Verify all tests pass

**Estimated effort:** 2-3 hours

**Decision:** Implement after Phase 3A is complete and tested. CTE JOINs are required for complete FR-002 coverage.

---

## 6. Test Cases

All test cases defined in SQL-ANALYSER-SPEC.md §6.2 (FR-002).

### TC-002-01: Single-column explicit JOIN

```sql
SELECT o.id, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
```

**Assertions:**
- 1 relationship extracted
- `left_table = "orders"`, `left_columns = ["customer_id"]`
- `right_table = "customers"`, `right_columns = ["id"]`

### TC-002-02: Multi-column JOIN

```sql
SELECT * FROM orders o
JOIN shipments s ON o.region = s.region AND o.order_id = s.order_id
```

**Assertions:**
- 1 relationship extracted
- `left_columns = ["region", "order_id"]`
- `right_columns = ["region", "order_id"]`

### TC-002-03: Implicit WHERE join

```sql
SELECT o.id, c.name
FROM orders o, customers c
WHERE o.customer_id = c.id
```

**Assertions:**
- 1 relationship extracted (same as TC-002-01)

### TC-002-04: Multiple JOINs (chain)

```sql
SELECT o.id, c.name, p.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id
```

**Assertions:**
- 2 relationships extracted
- orders ↔ customers
- orders ↔ products

### TC-002-05: CTE JOIN (Phase 3B)

```sql
WITH tmp AS (SELECT order_id, total FROM orders)
SELECT t.order_id, p.name
FROM tmp t
JOIN products p ON t.order_id = p.order_id
```

**Assertions:**
- 1 relationship: orders ↔ products

### TC-002-06: Self-join

```sql
SELECT a.id, b.id
FROM users a
JOIN users b ON a.manager_id = b.id
```

**Assertions:**
- 1 relationship
- `left_table = "users"`, `right_table = "users"`
- `left_columns = ["manager_id"]`, `right_columns = ["id"]`

### TC-002-07: Relationship deduplication

```sql
SELECT * FROM orders o
JOIN customers c ON o.customer_id = c.id
UNION
SELECT * FROM orders o2
JOIN customers c2 ON o2.customer_id = c2.id
```

**Assertions:**
- 1 relationship (deduplicated)

---

## 7. Testing Strategy

### 7.1 Unit Tests

**File:** `tests/test_relationships.py`

**Structure:**
```python
def test_single_column_join(single_column_join):
    """TC-002-01"""
    result = analyse(single_column_join)
    assert len(result.data_model.relationships) == 1
    rel = result.data_model.relationships[0]
    # ... assertions

def test_multi_column_join(multi_column_join):
    """TC-002-02"""
    # ...

# ... etc for all 7 test cases
```

### 7.2 Fixtures

**File:** `tests/conftest.py`

Add parsed AST fixtures:
```python
@pytest.fixture
def single_column_join():
    return sqlglot.parse_one(
        "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
        dialect="postgres"
    )

@pytest.fixture
def multi_column_join():
    return sqlglot.parse_one(
        "SELECT * FROM orders o JOIN shipments s ON o.region = s.region AND o.order_id = s.order_id",
        dialect="postgres"
    )

# ... etc
```

### 7.3 Integration Tests

Use existing `test_complex_integration` from Phase 2 — verify relationships are extracted alongside tables/columns.

### 7.4 Regression Tests

All Phase 1 and Phase 2 tests must continue passing (56 tests).

---

## 8. Success Metrics

- ✅ All 7 test cases (TC-002-01 through TC-002-07) passing
- ✅ 56 existing tests still passing (no regressions)
- ✅ Code coverage on `analyser.py` remains ≥ 90%
- ✅ No mypy strict mode errors
- ✅ No ruff linting warnings
- ✅ Pre-commit hooks pass (ruff + pytest)

---

## 9. Non-Goals

**Not included in Phase 3:**
- Relationship cardinality (1:1, 1:N, N:M)
- Relationship directionality/role naming
- Non-equi-join predicates
- Transitive relationship inference
- Foreign key constraint metadata
- Relationship strength/confidence scoring

---

## 10. Future Enhancements

### Phase 3C: Advanced Relationship Features (Future)

- Relationship cardinality inference from query patterns
- Named relationship roles (e.g., "orders.customer_id → customers.id" labeled as "customer")
- Support for inequality join predicates (for completeness)
- Relationship metadata (join type: INNER, LEFT, etc.)

---

## 11. References

- **SQL-ANALYSER-SPEC.md** §3.2 (FR-002 definition)
- **SQL-ANALYSER-SPEC.md** §6.2 (FR-002 test cases)
- **DOMAIN-MODEL-PLAN.md** §2 (Analysis Processing Sequence, Step 2d)
- **AGENTS.md** §4 (Implementation Sequence — Phase 3)
- **src/sql_analyser/domain.py** (`Relationship` class definition)
- **Phase 2 TODO.md** (completed dependencies)

---

## 12. Approval & Sign-off

**Prepared by:** AI Agent
**Date:** 2026-03-20
**Status:** Draft — Awaiting User Review

**Next steps after approval:**
1. Create `features/03-relationships/TODO.md` with detailed task breakdown
2. Create tickets in `tk` system with dependencies
3. Create feature branch `feature/03-relationships`
4. Set up pre-commit hooks
5. Begin implementation
