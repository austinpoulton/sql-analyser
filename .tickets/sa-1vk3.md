---
id: sa-1vk3
status: open
deps: [sa-0nnp]
links: []
created: 2026-03-17T14:52:59Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [testing, construction]
---
# Write domain model construction tests

Write tests for basic construction in tests/test_domain_model.py:
- Test ColumnUsage and ColumnClassification enum construction
- Test QueriedColumn with defaults
- Test QueriedTable construction with all namespace parts
- Test Relationship construction
- Test DataModel construction

Coverage: TC-DOMAIN-01

## Acceptance Criteria

- All basic construction tests pass
- Tests verify default values work
- Tests verify type validation

