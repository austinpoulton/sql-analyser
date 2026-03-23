---
id: sa-jq0w
status: closed
deps: [sa-06ql]
links: []
created: 2026-03-23T09:40:32Z
type: task
priority: 1
assignee: Austin Poulton
tags: [rendering, templates, fr-003]
---
# FR-003: Create Jinja2 templates for rendering

Create Jinja2 templates for Mermaid ERD, DBML, and markdown report rendering. Set up template loading infrastructure using importlib.resources

## Acceptance Criteria

templates/ directory created with __init__.py
mermaid_erd.j2 template created and tested
dbml.j2 template created and tested
markdown_report.j2 template created and tested
_load_template() helper function implemented
Templates work in both dev and installed package modes

