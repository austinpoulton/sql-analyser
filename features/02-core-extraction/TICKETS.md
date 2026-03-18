# Phase 2 Tickets Summary

## Epic Tickets

### Phase 2A: Basic Scope Traversal & Table Registry (sa-kx08)
**Priority:** P0
**Status:** Open
**Children:**
- sa-11ii: Setup analyser.py module structure
- sa-2uo3: Implement table registration loop
- sa-no13: Setup test infrastructure (conftest + test_source_data_model)
- sa-xvv7: Write Phase 2A tests (TC-001-01, TC-001-02)

### Phase 2B: Column Extraction from All Clauses (sa-vji0)
**Priority:** P0
**Status:** Open
**Dependencies:** Phase 2A completion
**Children:**
- sa-5fwj: Implement column extraction helpers
- sa-vgh8: Implement all-clause column extraction
- sa-26na: Test multiple usages and verify Phase 2B

### Phase 2C: CTE & Subquery Handling (sa-i2w1)
**Priority:** P0
**Status:** Open
**Dependencies:** Phase 2B completion
**Children:**
- sa-vtdu: Implement CTE/subquery handling
- sa-0kit: Add CTE and subquery tests

### Phase 2D: Wildcard Detection (sa-5gn6)
**Priority:** P0
**Status:** Open
**Dependencies:** Phase 2C completion
**Children:**
- sa-qdjl: Implement wildcard detection
- sa-gkyx: Add wildcard tests

### Phase 2E: Edge Cases & Finalization (sa-2j56)
**Priority:** P0
**Status:** Open
**Dependencies:** Phase 2D completion
**Children:**
- sa-xabo: Handle edge cases (self-join, UNION)
- sa-p7wb: Add error handling and logging
- sa-rfd5: Finalize public API and run full test suite
- sa-sev6: Write integration test and update AGENTS.md

### Phase 2F: Documentation & Cleanup (sa-3g3r)
**Priority:** P1
**Status:** Open
**Dependencies:** Phase 2E completion
**Children:**
- sa-vytn: Add docstrings and type hints
- sa-cckm: Code review, refactoring, and final cleanup

## Task Dependency Chain

```
sa-11ii (Setup module) 
    → sa-2uo3 (Table registration)
        → sa-xvv7 (Phase 2A tests)
            → sa-5fwj (Extraction helpers)
                → sa-vgh8 (Clause extraction)
                    → sa-26na (Phase 2B tests)
                        → sa-vtdu (CTE handling)
                            → sa-0kit (CTE tests)
                                → sa-qdjl (Wildcard impl)
                                    → sa-gkyx (Wildcard tests)
                                        → sa-xabo (Edge cases)
                                            → sa-p7wb (Error handling)
                                                → sa-rfd5 (API finalization)
                                                    → sa-sev6 (Integration test)
                                                        → sa-vytn (Docstrings)
                                                            → sa-cckm (Final cleanup)

sa-no13 (Test setup) → sa-xvv7 (Phase 2A tests)
```

## Ready to Start

The following tickets have no dependencies and can be started immediately:
- **sa-11ii**: Setup analyser.py module structure
- **sa-no13**: Setup test infrastructure (conftest + test_source_data_model)

## Phase 2 Test Coverage

### FR-001: Source Data Model Extraction
- TC-001-01: Single table SELECT
- TC-001-02: Multi-table join with aliases
- TC-001-03: WHERE clause columns
- TC-001-04: GROUP BY clause columns
- TC-001-05: HAVING clause columns
- TC-001-06: ORDER BY clause columns
- TC-001-07: Simple CTE
- TC-001-08: Nested CTE (3 levels)
- TC-001-09: Subquery in FROM
- TC-001-10: Self-join

### FR-008: Wildcard Handling
- TC-008-01: Unqualified SELECT *
- TC-008-02: Qualified table.*
- TC-008-03: Wildcard with explicit columns

## Estimated Timeline

- **Phase 2A:** ~2.5 hours
- **Phase 2B:** ~4.5 hours
- **Phase 2C:** ~2.5 hours
- **Phase 2D:** ~1.5 hours
- **Phase 2E:** ~4 hours
- **Phase 2F:** ~2 hours

**Total:** ~17 hours (spread over multiple sessions)
