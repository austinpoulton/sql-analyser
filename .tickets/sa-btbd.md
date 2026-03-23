---
id: sa-btbd
status: closed
deps: [sa-ymba]
links: []
created: 2026-03-23T06:17:18Z
type: feature
priority: 2
assignee: Austin Poulton
---
# Integrate metrics into analyser.py

Modify src/sql_analyser/analyser.py to compute and populate metrics field in AnalysisResult. Add metrics computation after data model extraction.

## Acceptance Criteria

- Import compute_metrics from .metrics
- Call metrics = compute_metrics(expression) in analyse() function
- Pass metrics to AnalysisResult constructor
- Existing tests still pass (no regression)
- Metrics are populated in returned AnalysisResult

