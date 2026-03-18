---
id: sa-c6my
status: closed
deps: [sa-0nnp]
links: []
created: 2026-03-17T14:53:00Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [testing, serialisation, json]
---
# Write JSON serialisation tests

Write JSON serialisation tests:
- Test model_dump() for all domain classes
- Test model_dump_json() for all classes
- Test model_validate() round-trip
- Test model_validate_json() round-trip
- Test set[ColumnUsage] serialises as array
- Test StrEnum serialisation

Coverage: TC-DOMAIN-02, TC-DOMAIN-03, TC-009-03

## Acceptance Criteria

- All serialisation round-trips preserve data
- Sets serialise as JSON arrays
- Enums serialise as strings
- No data loss in round-trip

