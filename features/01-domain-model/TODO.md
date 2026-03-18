# TODO: Domain Model & Serialisation (FR-009)

## Overview

Implementation checklist for Feature 01: Domain Model & Serialisation. This feature establishes the core Pydantic domain model classes with JSON serialisation and merge capabilities.

## Dependencies

- Python ≥ 3.12
- pydantic ≥ 2.0
- pytest

## Task Breakdown

### Phase 1: Project Setup & Structure

- [ ] **TASK-01**: Create module structure
  - Create `src/sql_analyser/` directory
  - Create `src/sql_analyser/__init__.py` (empty initially)
  - Create `src/sql_analyser/domain.py` (empty initially)
  - Create `tests/` directory
  - Create `tests/test_domain_model.py` (empty initially)
  - **Estimated time**: 5 minutes
  - **Dependencies**: None

### Phase 2: Domain Model Implementation

- [ ] **TASK-02**: Implement enums in `domain.py`
  - Add imports: `from enum import StrEnum`
  - Implement `ColumnUsage` enum with 6 values
  - Implement `ColumnClassification` enum with 3 values
  - Add docstrings
  - **Estimated time**: 10 minutes
  - **Dependencies**: TASK-01
  - **Test coverage**: TC-DOMAIN-01

- [ ] **TASK-03**: Implement `QueriedColumn` model
  - Add imports: `from pydantic import BaseModel, Field`
  - Implement `QueriedColumn` class with 3 fields
  - Add type hints and defaults
  - Add docstring
  - **Estimated time**: 15 minutes
  - **Dependencies**: TASK-02
  - **Test coverage**: TC-DOMAIN-01, TC-DOMAIN-02

- [ ] **TASK-04**: Implement `QueriedTable` model with `qualified_name` property
  - Implement `QueriedTable` class with 5 fields
  - Implement `qualified_name` property (joins non-empty parts)
  - Add docstring explaining namespace structure
  - **Estimated time**: 20 minutes
  - **Dependencies**: TASK-03
  - **Test coverage**: TC-DOMAIN-04, TC-DOMAIN-05

- [ ] **TASK-05**: Implement `Relationship` model with `canonical_key` property
  - Implement `Relationship` class with 4 fields
  - Implement `canonical_key` property (sorted tuple for symmetry)
  - Add docstring explaining deduplication logic
  - **Estimated time**: 25 minutes
  - **Dependencies**: TASK-02
  - **Test coverage**: TC-DOMAIN-06, TC-DOMAIN-07

- [ ] **TASK-06**: Implement `DataModel` class (without merge method)
  - Implement `DataModel` class with 2 fields
  - Add placeholder for `merge` method
  - Add docstring
  - **Estimated time**: 10 minutes
  - **Dependencies**: TASK-04, TASK-05

- [ ] **TASK-07**: Implement `OutputColumn` model
  - Implement `OutputColumn` class with 5 fields
  - Add type hints with Optional types
  - Add docstring
  - **Estimated time**: 10 minutes
  - **Dependencies**: TASK-02

- [ ] **TASK-08**: Implement `ComplexityMetrics` model
  - Implement `ComplexityMetrics` class with 3 fields
  - Add docstring
  - **Estimated time**: 10 minutes
  - **Dependencies**: None

- [ ] **TASK-09**: Implement `AnalysisResult` model
  - Implement `AnalysisResult` class with 3 fields
  - Add type hints with Optional types
  - Add docstring
  - **Estimated time**: 10 minutes
  - **Dependencies**: TASK-06, TASK-07, TASK-08

### Phase 3: Merge Logic Implementation

- [ ] **TASK-10**: Implement `merge_columns` function
  - Add imports: `import warnings`
  - Implement column name validation
  - Implement usage union logic
  - Implement type specificity rules:
    - Both varchar → varchar
    - One varchar → non-varchar wins
    - Both non-varchar and different → warn, prefer left
  - Add comprehensive docstring with examples
  - **Estimated time**: 30 minutes
  - **Dependencies**: TASK-03
  - **Test coverage**: TC-009-03, TC-009-04, TC-DOMAIN-08

- [ ] **TASK-11**: Implement `merge_tables` function
  - Implement qualified_name validation
  - Build column index by name
  - Call `merge_columns` for overlapping columns
  - Implement wildcard OR logic
  - Add comprehensive docstring
  - **Estimated time**: 25 minutes
  - **Dependencies**: TASK-04, TASK-10
  - **Test coverage**: TC-009-02, TC-DOMAIN-09

- [ ] **TASK-12**: Implement `merge_models` function
  - Build table index by qualified_name
  - Call `merge_tables` for overlapping tables
  - Deduplicate relationships using canonical_key
  - Add comprehensive docstring
  - **Estimated time**: 30 minutes
  - **Dependencies**: TASK-11
  - **Test coverage**: TC-009-01, TC-009-05

- [ ] **TASK-13**: Wire `DataModel.merge` method to `merge_models`
  - Update `DataModel.merge` to call `merge_models(self, other)`
  - Update docstring
  - **Estimated time**: 5 minutes
  - **Dependencies**: TASK-12

### Phase 4: Public API

- [ ] **TASK-14**: Implement public API in `__init__.py`
  - Import all domain classes from `.domain`
  - Define `__all__` list with 9 exports
  - **Estimated time**: 10 minutes
  - **Dependencies**: TASK-09

### Phase 5: Test Implementation

- [ ] **TASK-15**: Write basic construction tests
  - Test `ColumnUsage` enum construction
  - Test `ColumnClassification` enum construction
  - Test `QueriedColumn` with defaults
  - Test `QueriedTable` with all namespace parts
  - Test `Relationship` construction
  - Test `DataModel` construction
  - **Estimated time**: 30 minutes
  - **Dependencies**: TASK-14
  - **Coverage**: TC-DOMAIN-01

- [ ] **TASK-16**: Write JSON serialisation tests
  - Test `model_dump()` for all classes
  - Test `model_dump_json()` for all classes
  - Test `model_validate()` round-trip
  - Test `model_validate_json()` round-trip
  - Test set and enum serialisation
  - **Estimated time**: 45 minutes
  - **Dependencies**: TASK-14
  - **Coverage**: TC-DOMAIN-02, TC-DOMAIN-03, TC-009-03 (JSON aspect)

- [ ] **TASK-17**: Write computed property tests
  - Test `QueriedTable.qualified_name` with full namespace
  - Test `QueriedTable.qualified_name` with schema.name only
  - Test `QueriedTable.qualified_name` with name only
  - Test `Relationship.canonical_key` symmetry
  - Test `Relationship.canonical_key` with multi-column joins
  - Test `Relationship.canonical_key` column sorting
  - **Estimated time**: 30 minutes
  - **Dependencies**: TASK-14
  - **Coverage**: TC-DOMAIN-04, TC-DOMAIN-05, TC-DOMAIN-06, TC-DOMAIN-07

- [ ] **TASK-18**: Write merge column tests
  - Test merge with same name and type
  - Test merge with usage union
  - Test merge with varchar vs int (int wins)
  - Test merge with int vs varchar (int wins)
  - Test merge with int vs bigint (left wins, warning)
  - Test merge with mismatched names (raises ValueError)
  - **Estimated time**: 35 minutes
  - **Dependencies**: TASK-13
  - **Coverage**: TC-009-03, TC-009-04, TC-DOMAIN-08

- [ ] **TASK-19**: Write merge table tests
  - Test merge with same table, disjoint columns
  - Test merge with same table, overlapping columns
  - Test merge with wildcard: False OR False = False
  - Test merge with wildcard: True OR False = True
  - Test merge with wildcard: True OR True = True
  - Test merge with mismatched qualified_name (raises ValueError)
  - **Estimated time**: 35 minutes
  - **Dependencies**: TASK-13
  - **Coverage**: TC-009-02, TC-DOMAIN-09

- [ ] **TASK-20**: Write merge model tests
  - Test merge with disjoint tables
  - Test merge with disjoint relationships
  - Test merge with overlapping tables and columns
  - Test merge with duplicate relationships (canonical_key dedup)
  - Test merge with symmetric relationships: (A→B) and (B→A)
  - Test merge with multiple tables and relationships
  - **Estimated time**: 45 minutes
  - **Dependencies**: TASK-13
  - **Coverage**: TC-009-01, TC-009-02, TC-009-05

### Phase 6: Validation & Documentation

- [ ] **TASK-21**: Run tests and verify coverage
  - Run `uv run pytest tests/test_domain_model.py -v`
  - Run `uv run pytest tests/test_domain_model.py --cov=src/sql_analyser/domain --cov-report=term-missing`
  - Verify coverage ≥ 95%
  - Fix any failing tests
  - **Estimated time**: 20 minutes
  - **Dependencies**: TASK-20

- [ ] **TASK-22**: Type checking
  - Run `uv run mypy src/sql_analyser/domain.py`
  - Fix any type errors
  - **Estimated time**: 15 minutes
  - **Dependencies**: TASK-14

- [ ] **TASK-23**: Code review checklist
  - Verify all functions have docstrings (Google style)
  - Verify all type hints are present
  - Verify imports are organized (stdlib → third-party → local)
  - Verify no star imports
  - Verify snake_case for functions, PascalCase for classes
  - **Estimated time**: 15 minutes
  - **Dependencies**: TASK-22

- [ ] **TASK-24**: Update AGENTS.md if needed
  - Verify module layout in AGENTS.md matches implementation
  - Update if any deviations from plan
  - **Estimated time**: 10 minutes
  - **Dependencies**: TASK-23

## Test Case Mapping

| Test Case | Tasks | Description |
|-----------|-------|-------------|
| TC-DOMAIN-01 | TASK-15 | Basic construction of all classes |
| TC-DOMAIN-02 | TASK-16 | JSON dict serialisation round-trip |
| TC-DOMAIN-03 | TASK-16 | JSON string serialisation round-trip |
| TC-DOMAIN-04 | TASK-17 | qualified_name with full namespace |
| TC-DOMAIN-05 | TASK-17 | qualified_name with partial namespace |
| TC-DOMAIN-06 | TASK-17 | canonical_key symmetry |
| TC-DOMAIN-07 | TASK-17 | canonical_key multi-column sorting |
| TC-DOMAIN-08 | TASK-18 | Merge columns with usage union |
| TC-DOMAIN-09 | TASK-19 | Merge tables with wildcard OR |
| TC-009-01 | TASK-20 | Merge disjoint DataModels |
| TC-009-02 | TASK-19, TASK-20 | Merge overlapping tables/columns |
| TC-009-03 | TASK-18 | Type specificity (varchar vs non-varchar) |
| TC-009-04 | TASK-18 | Conflicting non-varchar types |
| TC-009-05 | TASK-20 | Relationship deduplication |

## Estimated Total Time

- Phase 1 (Setup): 5 minutes
- Phase 2 (Domain Models): 2 hours
- Phase 3 (Merge Logic): 1.5 hours
- Phase 4 (Public API): 10 minutes
- Phase 5 (Tests): 4 hours
- Phase 6 (Validation): 1 hour

**Total: ~9 hours** (includes test writing)

## Success Criteria

All tasks completed ✓
- [ ] All 24 tasks completed
- [ ] All tests pass (`pytest tests/test_domain_model.py`)
- [ ] Test coverage ≥ 95% for `domain.py`
- [ ] Type checking passes (`mypy`)
- [ ] Code style compliant (docstrings, type hints, naming)
- [ ] Public API exports working (`from sql_analyser import QueriedTable`)

## Notes

- Tasks should be completed in order due to dependencies
- Each task includes estimated time for planning purposes
- Test tasks (TASK-15 through TASK-20) can be parallelized somewhat, but merge tests depend on merge logic implementation
- All merge functions should emit warnings (not errors) for conflicting types per spec
