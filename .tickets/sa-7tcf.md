---
id: sa-7tcf
status: open
deps: [sa-5a6p]
links: []
created: 2026-03-17T14:52:22Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [domain-model, merge-logic]
---
# Implement merge logic functions

Implement three merge functions in domain.py:

1. merge_columns(left, right) -> QueriedColumn
   - Validate names match
   - Union usages
   - Type specificity: non-varchar beats varchar
   - Conflicting non-varchar: warn, prefer left

2. merge_tables(left, right) -> QueriedTable
   - Validate qualified_name matches
   - Merge columns by name
   - OR has_wildcard flags

3. merge_models(left, right) -> DataModel
   - Union tables by qualified_name
   - Union relationships by canonical_key

Wire DataModel.merge() method to call merge_models().

## Acceptance Criteria

- merge_columns handles type specificity correctly
- merge_columns emits warnings for conflicting non-varchar types
- merge_tables merges columns and wildcard flags
- merge_models deduplicates relationships symmetrically
- DataModel.merge() delegates to merge_models()
- All functions have comprehensive docstrings with examples

