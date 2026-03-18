---
id: sa-9ekc
status: closed
deps: [sa-0nnp]
links: []
created: 2026-03-17T14:53:00Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [testing, properties]
---
# Write computed property tests

Write tests for computed properties:
- QueriedTable.qualified_name with full namespace (catalog.schema.name)
- QueriedTable.qualified_name with partial namespace (schema.name, name only)
- Relationship.canonical_key symmetry: (A→B) == (B→A)
- Relationship.canonical_key with multi-column joins
- Relationship.canonical_key column sorting

Coverage: TC-DOMAIN-04, TC-DOMAIN-05, TC-DOMAIN-06, TC-DOMAIN-07

## Acceptance Criteria

- qualified_name joins non-empty parts correctly
- qualified_name handles all namespace combinations
- canonical_key is symmetric for relationship deduplication
- canonical_key sorts columns within each side

