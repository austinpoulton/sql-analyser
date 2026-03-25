---
id: sa-efm4
status: open
deps: []
links: []
created: 2026-03-25T08:33:34Z
type: epic
priority: 0
assignee: Austin Poulton
---
# Epic: GitHub CI/CD Pipeline with Security Scanning

Establish a comprehensive GitHub Actions CI/CD pipeline for sql-analyser that automates testing, security scanning, package building, and distribution to PyPI.

## Goals
1. Automate quality assurance (linting, type checking, tests)
2. Detect security vulnerabilities in dependencies and code
3. Streamline releases via automated PyPI publishing
4. Multi-platform validation (Python 3.12+, Ubuntu/macOS/Windows)
5. Establish quality gates to prevent regressions

## References
- PRD: features/06-cicd-setup/PRD.md
- TODO: features/06-cicd-setup/TODO.md
- Feature branch: feature/06-cicd-setup

## Acceptance Criteria

- CI runs on every PR with quality gates enforced
- Security scans run weekly and on PRs
- Releases performed by creating git tag
- All workflows documented (CONTRIBUTING.md, RELEASING.md, SECURITY.md)
- First release published successfully via automated pipeline
- All P0 requirements (FR-001, FR-002, FR-003) complete

