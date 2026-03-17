# Tickets: Domain Model & Serialisation (FR-009)

## Epic: sa-tlx0

**FR-009: Domain Model & Serialisation**

Implement core Pydantic domain model classes with JSON serialisation and merge capabilities for SQL Analyser. Foundation for all subsequent features.

**Tags**: `foundation`, `domain-model`, `fr-009`
**External Ref**: `features/01-domain-model`

---

## Work Breakdown

### Phase 1: Setup (1 ticket)

#### sa-0hcc: Setup project structure for domain model
**Priority**: P0 | **Status**: Open | **Dependencies**: None

Create initial module structure:
- `src/sql_analyser/` directory
- `src/sql_analyser/__init__.py`
- `src/sql_analyser/domain.py`
- `tests/` directory
- `tests/test_domain_model.py`

**Maps to**: TODO TASK-01

---

### Phase 2: Implementation (3 tickets)

#### sa-5a6p: Implement domain model enums and base classes
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-0hcc

Implement core domain model classes in `domain.py`:
- ColumnUsage enum (6 values)
- ColumnClassification enum (3 values)
- QueriedColumn model with 3 fields
- QueriedTable model with `qualified_name` property
- Relationship model with `canonical_key` property
- DataModel class (without merge initially)
- OutputColumn model
- ComplexityMetrics model
- AnalysisResult model

**Maps to**: TODO TASK-02 through TASK-09

#### sa-7tcf: Implement merge logic functions
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-5a6p

Implement three merge functions:
1. `merge_columns(left, right)` — type specificity, usage union
2. `merge_tables(left, right)` — column merging, wildcard OR
3. `merge_models(left, right)` — table union, relationship deduplication

Wire `DataModel.merge()` method to call `merge_models()`.

**Maps to**: TODO TASK-10 through TASK-13

#### sa-0nnp: Implement public API exports
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-5a6p

Create public API in `src/sql_analyser/__init__.py`:
- Import all domain classes from `.domain`
- Define `__all__` list with 9 exports

**Maps to**: TODO TASK-14

---

### Phase 3: Testing (4 tickets)

#### sa-1vk3: Write domain model construction tests
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-0nnp

Test basic construction of all domain classes:
- Enum construction
- QueriedColumn, QueriedTable, Relationship, DataModel construction
- Default value verification

**Coverage**: TC-DOMAIN-01
**Maps to**: TODO TASK-15

#### sa-c6my: Write JSON serialisation tests
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-0nnp

Test JSON serialisation:
- `model_dump()`, `model_dump_json()`
- `model_validate()`, `model_validate_json()` round-trips
- Set and enum serialisation

**Coverage**: TC-DOMAIN-02, TC-DOMAIN-03
**Maps to**: TODO TASK-16

#### sa-9ekc: Write computed property tests
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-0nnp

Test computed properties:
- `QueriedTable.qualified_name` with full/partial namespace
- `Relationship.canonical_key` symmetry and column sorting

**Coverage**: TC-DOMAIN-04 through TC-DOMAIN-07
**Maps to**: TODO TASK-17

#### sa-59aj: Write merge function tests
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-7tcf

Comprehensive merge tests:
- `merge_columns`: type specificity, usages, conflicts
- `merge_tables`: disjoint/overlapping columns, wildcards
- `merge_models`: table union, relationship deduplication

**Coverage**: TC-009-01 through TC-009-05, TC-DOMAIN-08, TC-DOMAIN-09
**Maps to**: TODO TASK-18 through TASK-20

---

### Phase 4: Validation (2 tickets)

#### sa-bofw: Run tests and validate coverage
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-59aj

Run validation:
- `pytest tests/test_domain_model.py -v`
- Coverage check (≥ 95%)
- `mypy` type checking
- Fix any failures

**Maps to**: TODO TASK-21, TASK-22

#### sa-45rz: Code review and documentation check
**Priority**: P0 | **Status**: Open | **Dependencies**: sa-bofw

Final review:
- Docstrings (Google style)
- Type hints
- Import organization
- Naming conventions
- Update AGENTS.md if needed

**Maps to**: TODO TASK-23, TASK-24

---

## Dependency Graph

```
sa-tlx0 (Epic)
├── sa-0hcc (Setup)
    └── sa-5a6p (Domain Classes)
        ├── sa-7tcf (Merge Logic)
        │   └── sa-59aj (Merge Tests)
        │       └── sa-bofw (Validation)
        │           └── sa-45rz (Code Review)
        └── sa-0nnp (Public API)
            ├── sa-1vk3 (Construction Tests)
            ├── sa-c6my (Serialisation Tests)
            └── sa-9ekc (Property Tests)
```

---

## Workflow

1. **Start with**: `tk start sa-0hcc` (Setup — no dependencies)
2. **Then**: `tk start sa-5a6p` (Domain Classes)
3. **Parallel tracks**:
   - **Implementation**: sa-7tcf → sa-0nnp
   - **Testing**: sa-1vk3, sa-c6my, sa-9ekc (can be done in parallel)
4. **After merge logic**: sa-59aj (Merge Tests)
5. **Finally**: sa-bofw (Validation) → sa-45rz (Code Review)

---

## Quick Commands

```bash
# See what's ready to work on
tk ready

# See what's blocked
tk blocked

# Start first task
tk start sa-0hcc

# View a ticket
tk show sa-0hcc

# Close a ticket when done
tk close sa-0hcc

# Check dependency tree
tk dep tree sa-tlx0
```

---

## Success Criteria (from Epic)

- [ ] All domain classes implemented in domain.py
- [ ] All merge functions working correctly
- [ ] Public API exports in __init__.py
- [ ] All tests passing with ≥95% coverage
- [ ] Type checking passes
- [ ] Docstrings on all public classes/functions
