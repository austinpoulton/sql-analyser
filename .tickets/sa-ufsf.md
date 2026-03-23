---
id: sa-ufsf
status: closed
deps: [sa-ymba, sa-btbd, sa-78mb]
links: []
created: 2026-03-23T06:17:34Z
type: feature
priority: 2
assignee: Austin Poulton
---
# Integration testing and validation

Verify metrics are correctly integrated into full analysis pipeline. Run complete test suite to ensure no regressions.

## Acceptance Criteria

- Integration test calls analyse() directly
- Verify AnalysisResult.metrics is populated
- Verify metrics are JSON-serializable
- All existing tests still pass (run full test suite)
- Test coverage ≥95% for metrics.py

