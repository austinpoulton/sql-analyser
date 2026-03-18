---
id: sa-59aj
status: closed
deps: [sa-7tcf]
links: []
created: 2026-03-17T14:53:00Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [testing, merge-logic]
---
# Write merge function tests

Write comprehensive merge tests:

merge_columns:
- Same name and type
- Usage union
- varchar vs int (int wins)
- int vs varchar (int wins)
- int vs bigint (left wins with warning)
- Mismatched names (raises ValueError)

merge_tables:
- Disjoint columns
- Overlapping columns
- Wildcard OR logic (all combinations)
- Mismatched qualified_name (raises ValueError)

merge_models:
- Disjoint tables and relationships
- Overlapping tables
- Symmetric relationships: (A→B) and (B→A) deduplicate
- Multiple tables and relationships

Coverage: TC-009-01 through TC-009-05, TC-DOMAIN-08, TC-DOMAIN-09

## Acceptance Criteria

- All merge scenarios tested
- Type specificity rules verified
- Warnings emitted for conflicting types
- Relationship deduplication works
- ValueError raised for invalid merges

