# PRD: GitHub CI/CD Pipeline with Security Scanning

**Feature ID:** 06-cicd-setup
**Status:** Planning
**Author:** Austin Poulton
**Created:** 2026-03-24
**Updated:** 2026-03-24

---

## Executive Summary

Establish a comprehensive GitHub Actions CI/CD pipeline for sql-analyser that automates testing, security scanning, package building, and distribution to PyPI. The pipeline will enforce quality gates, detect vulnerabilities in dependencies and code, and streamline the release process while maintaining high security standards.

---

## Problem Statement

Currently, sql-analyser lacks automated CI/CD infrastructure, which creates several risks and inefficiencies:

1. **Quality Risk**: No automated testing on pull requests increases the risk of regressions reaching main
2. **Security Risk**: No vulnerability scanning of dependencies or code exposes users to known CVEs
3. **Manual Overhead**: Manual building and publishing of packages is error-prone and time-consuming
4. **Platform Coverage**: No guarantee that code works across Python versions (3.12, 3.13) and operating systems
5. **Release Friction**: Manual release processes slow down distribution of fixes and features
6. **Supply Chain Risk**: No verification of package integrity or provenance

---

## Goals

### Primary Goals

1. **Automate quality assurance** — Run linting, type checking, and tests on every commit
2. **Detect security vulnerabilities** — Scan dependencies and code for known CVEs and security issues
3. **Streamline releases** — Automate package building, signing, and publishing to PyPI
4. **Multi-platform validation** — Ensure compatibility across Python 3.12+ and major operating systems
5. **Establish quality gates** — Prevent merging code that fails tests or has critical security issues

### Secondary Goals

1. Track test coverage trends
2. Generate Software Bill of Materials (SBOM)
3. Automate dependency updates via Dependabot
4. Provide release artifacts with checksums and signatures

---

## Non-Goals

- **Container image building** — sql-analyser is a pure Python library, not a containerized application
- **Deployment to production infrastructure** — This is a library published to PyPI, not a deployed service
- **Performance benchmarking** — Out of scope for this feature (could be future work)
- **Documentation deployment** — No docs site to deploy (README-based documentation)

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CI execution time (PR check) | < 5 minutes | GitHub Actions duration |
| Security scan coverage | 100% of dependencies | pip-audit + Bandit scan all deps |
| Release automation success rate | > 95% | Successful automated releases / total releases |
| Critical vulnerability detection time | < 24 hours | Time from CVE publication to detection |
| Platform test coverage | 3 OS × 2 Python versions | Matrix test execution |

---

## User Stories

### US-1: Developer submitting a pull request
**As a** contributor
**I want** automated tests and security scans to run on my PR
**So that** I know my changes are safe and correct before requesting review

**Acceptance Criteria:**
- CI runs automatically on PR creation and updates
- Linting, type checking, and tests run on all target platforms
- Security scan results are visible in PR checks
- PR cannot be merged if critical checks fail

---

### US-2: Maintainer releasing a new version
**As a** maintainer
**I want** to publish a new release by creating a git tag
**So that** the package is automatically built, tested, and published to PyPI

**Acceptance Criteria:**
- Pushing a `v*.*.*` tag triggers release workflow
- Version consistency is validated (pyproject.toml, CITATION.cff, git tag)
- Package is built, scanned for vulnerabilities, and published
- GitHub Release is created with artifacts and checksums
- TestPyPI is used for validation before PyPI publication

---

### US-3: Security-conscious user
**As a** user of sql-analyser
**I want** to verify the integrity of published packages
**So that** I can trust the package hasn't been tampered with

**Acceptance Criteria:**
- Published packages include SHA256 checksums
- Artifacts are signed using Sigstore (optional, if implemented)
- SBOM is generated and published with release
- PyPI provenance attestations are enabled

---

### US-4: Maintainer monitoring dependencies
**As a** maintainer
**I want** automated alerts for vulnerable dependencies
**So that** I can update dependencies before security issues affect users

**Acceptance Criteria:**
- Dependabot creates PRs for dependency updates
- Security scans run weekly on a schedule
- GitHub Security tab shows vulnerability alerts
- Critical vulnerabilities fail CI immediately

---

## Functional Requirements

### FR-001: Continuous Integration Workflow

**Priority:** P0 (Critical)

The system shall execute a comprehensive CI workflow on every push to branches and pull requests.

**Specifications:**
- **Trigger events:**
  - Push to any branch
  - Pull request opened, synchronized, or reopened
- **Jobs:**
  1. **Lint and Type Check**
     - Run `ruff check` for code quality
     - Run `ruff format --check` for formatting
     - Run `mypy` for type safety
  2. **Test Suite**
     - Matrix: Python 3.12, 3.13 × Ubuntu, macOS, Windows
     - Execute `uv run pytest` with coverage
     - Upload coverage reports to Codecov (optional)
  3. **Build Validation**
     - Build wheel and sdist using `hatchling`
     - Install built package in clean virtualenv
     - Run smoke test (import sql_analyser, instantiate classes)
     - Store artifacts for 30 days

**Quality Gates:**
- All linting must pass (zero violations)
- Type checking must pass (zero errors)
- Test coverage ≥ 80%
- All tests must pass on all platforms
- Build must succeed without errors

---

### FR-002: Security Scanning Workflow

**Priority:** P0 (Critical)

The system shall scan dependencies and code for security vulnerabilities.

**Specifications:**
- **Trigger events:**
  - Push to `main` branch
  - Pull requests to `main`
  - Weekly schedule (every Monday 00:00 UTC)
  - Manual workflow dispatch
- **Jobs:**
  1. **Dependency Vulnerability Scan**
     - Use `pip-audit` to check for known CVEs
     - Generate SARIF report
     - Upload to GitHub Security tab
     - **Fail on:** HIGH or CRITICAL vulnerabilities
     - **Warn on:** MEDIUM vulnerabilities
  2. **Static Application Security Testing (SAST)**
     - Run `bandit` on `src/` directory
     - Check for common security anti-patterns
     - Report: hardcoded secrets, SQL injection, command injection
  3. **License Compliance**
     - Scan dependency licenses with `pip-licenses`
     - Flag GPL/AGPL licenses (copyleft concern)
     - Report unknown licenses
  4. **Supply Chain Security** (Optional - P1)
     - Scan with Trivy for comprehensive vulnerability detection
     - Check for dependency confusion attacks

**Quality Gates:**
- Zero HIGH/CRITICAL vulnerabilities in dependencies
- Zero security issues from Bandit
- All dependencies have approved licenses

---

### FR-003: Release and Publish Workflow

**Priority:** P0 (Critical)

The system shall automate package building and publishing when a version tag is created.

**Specifications:**
- **Trigger events:**
  - Push tags matching `v*.*.*` (e.g., `v0.1.0`, `v1.2.3`)
- **Jobs:**
  1. **Validate Release**
     - Extract version from tag (strip leading `v`)
     - Verify `pyproject.toml` version matches tag
     - Verify `CITATION.cff` version matches tag
     - Fail if versions are inconsistent
  2. **Build Packages**
     - Build wheel (`.whl`) and source distribution (`.tar.gz`)
     - Generate SHA256 checksums for all artifacts
     - Store build artifacts
  3. **Security Scan Artifacts**
     - Run `pip-audit` on built wheel
     - Run Trivy scan (if implemented)
     - Fail on HIGH/CRITICAL vulnerabilities
  4. **Test Installation**
     - Matrix: Python 3.12, 3.13
     - Install from built wheel in clean virtualenv
     - Run integration tests
     - Verify `import sql_analyser` works
  5. **Publish to TestPyPI**
     - Upload to TestPyPI using trusted publisher (OIDC)
     - Install from TestPyPI in clean environment
     - Run smoke tests
  6. **Publish to PyPI**
     - Requires: All previous jobs successful
     - Use GitHub environment: `production` (manual approval gate)
     - Upload to PyPI using trusted publisher (OIDC)
  7. **Create GitHub Release**
     - Generate release notes from commits since last tag
     - Upload wheel, sdist, and SHA256 checksums
     - Tag as latest release
     - Include SBOM (if generated)

**Quality Gates:**
- Version consistency across all files
- All tests pass
- Zero HIGH/CRITICAL vulnerabilities
- Successful installation from TestPyPI
- Manual approval before PyPI publication

---

### FR-004: Automated Dependency Updates

**Priority:** P1 (Important)

The system shall automatically create pull requests for dependency updates.

**Specifications:**
- **Dependabot configuration:**
  - Package ecosystem: `pip`
  - Schedule: Weekly
  - Grouping: Development dependencies grouped together
  - Auto-create PRs for:
    - Security updates (all severities)
    - Version updates (minor and patch)
  - Dependency groups:
    - `production`: sqlglot, pydantic, jinja2
    - `dev`: pytest, mypy, ruff, pytest-cov

**Behavior:**
- Dependabot opens PR with dependency updates
- CI workflow runs automatically on Dependabot PRs
- Maintainer reviews and merges if CI passes

---

### FR-005: Caching and Performance Optimization

**Priority:** P2 (Nice to have)

The system shall cache dependencies and build artifacts to improve workflow performance.

**Specifications:**
- **Cache strategies:**
  - `uv` dependencies cache (key: OS + lock file hash)
  - pip-audit vulnerability database cache (key: date)
  - Build artifacts cache (for re-use across jobs)

**Expected Impact:**
- Reduce CI execution time by 30-50%
- Reduce GitHub Actions minutes usage

---

## Technical Specifications

### Workflow File Structure

```
.github/
├── workflows/
│   ├── ci.yml                    # FR-001: Main CI pipeline
│   ├── security.yml              # FR-002: Security scanning
│   ├── release.yml               # FR-003: Release automation
│   └── codeql.yml                # Optional: Advanced security
├── dependabot.yml                # FR-004: Dependency updates
└── actions/                      # Reusable composite actions
    └── setup-uv/action.yml       # Custom uv setup action
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| CI/CD Platform | GitHub Actions | Workflow orchestration |
| Package Manager | `uv` | Fast, reliable dependency management |
| Build Backend | `hatchling` | PEP 517 compliant build |
| Linter | `ruff` | Fast Python linter and formatter |
| Type Checker | `mypy` | Static type analysis |
| Test Framework | `pytest` | Unit and integration testing |
| CVE Scanner | `pip-audit` | PyPA official vulnerability scanner |
| SAST | `bandit` | Python security linter |
| Comprehensive Scanner | `trivy` (optional) | Multi-purpose security scanner |
| Publishing | PyPI Trusted Publishers | OIDC-based authentication |

### Security Tools Detail

#### pip-audit
- **Purpose:** Scan Python dependencies for known CVEs
- **Database:** PyPA Advisory Database + OSV
- **Output:** SARIF format for GitHub Security tab integration
- **Failure threshold:** HIGH and CRITICAL vulnerabilities

#### Bandit
- **Purpose:** Static analysis for common security issues
- **Rules:** B1xx series (injection, hardcoded secrets, etc.)
- **Output:** SARIF format
- **Failure threshold:** MEDIUM and above

#### Trivy (Optional P1)
- **Purpose:** Comprehensive vulnerability and misconfiguration detection
- **Capabilities:**
  - Dependency scanning
  - Secret detection
  - License scanning
  - SBOM generation

### PyPI Publishing Configuration

**Trusted Publisher Setup** (OIDC-based, no API tokens):

1. Configure on PyPI:
   - Project: `sql-analyser`
   - Owner: `austinpoulton`
   - Workflow: `release.yml`
   - Environment: `production`

2. GitHub secrets: None required (OIDC handles authentication)

3. Environment protection rules:
   - `production` environment
   - Required reviewers: 1 (maintainer approval)
   - Deployment branches: Tags matching `v*.*.*`

---

## User Experience

### Developer Flow: Creating a PR

1. Developer pushes commits to feature branch
2. GitHub Actions automatically starts:
   - Linting and type checking (completes in ~30s)
   - Test matrix across platforms (completes in ~3-4 min)
   - Security scan (completes in ~1 min)
3. PR shows check status badges
4. If checks fail:
   - Developer sees detailed error logs
   - Fix issues and push again
   - CI re-runs automatically
5. When checks pass:
   - Green checkmarks on PR
   - Ready for maintainer review

### Maintainer Flow: Releasing a Version

1. Update version in `pyproject.toml` and `CITATION.cff`
2. Commit with message: `chore: Bump version to 0.2.0`
3. Create and push tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
4. GitHub Actions automatically:
   - Validates version consistency
   - Builds packages
   - Scans for vulnerabilities
   - Tests installation
   - Publishes to TestPyPI
   - Waits for manual approval
5. Maintainer approves production deployment
6. GitHub Actions:
   - Publishes to PyPI
   - Creates GitHub Release
   - Uploads artifacts

Total time: ~10 minutes (mostly automated)

---

## Dependencies

### External Services

- **GitHub Actions** — CI/CD platform (free for public repos)
- **PyPI** — Package distribution (free)
- **TestPyPI** — Pre-release validation (free)
- **Codecov** (Optional) — Coverage tracking (free for open source)

### Required Setup

1. PyPI Trusted Publisher configuration (maintainer action)
2. GitHub environment protection rules for `production`
3. Dependabot enablement in repository settings

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GitHub Actions outage | CI blocked | Low | Document manual release process as fallback |
| False positive security alerts | Developer friction | Medium | Configure allowlist for known false positives |
| PyPI publish failure | Release blocked | Low | Use TestPyPI validation step; manual fallback documented |
| Flaky tests on Windows | CI unreliable | Medium | Platform-specific test isolation; retry logic |
| Supply chain attack in dependencies | Security compromise | Low | Pin dependencies; review Dependabot PRs carefully |

---

## Open Questions

1. **Code coverage target:** Should we enforce a minimum coverage threshold (e.g., 80%) as a required check?
   - **Recommendation:** Yes, set to 80% with ability to override in exceptional cases

2. **Auto-merge Dependabot PRs?** Should we enable auto-merge for patch-level updates?
   - **Recommendation:** Not initially; review manually for first few months

3. **Artifact signing:** Should we implement Sigstore signing for packages?
   - **Recommendation:** P1 priority, implement after core workflows are stable

4. **SBOM format:** CycloneDX vs SPDX?
   - **Recommendation:** CycloneDX (better Python ecosystem support)

---

## Implementation Plan

See `TODO.md` for detailed implementation breakdown.

**Phases:**
1. **Phase 1:** CI workflow (FR-001)
2. **Phase 2:** Security scanning (FR-002)
3. **Phase 3:** Release automation (FR-003)
4. **Phase 4:** Dependabot configuration (FR-004)
5. **Phase 5:** Optimizations (FR-005, SBOM, signing)

---

## Appendix A: Example Workflow Triggers

### CI Workflow
```yaml
on:
  push:
    branches: ['**']
  pull_request:
    branches: [main]
```

### Security Workflow
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'  # Weekly, Monday 00:00 UTC
  workflow_dispatch:
```

### Release Workflow
```yaml
on:
  push:
    tags:
      - 'v*.*.*'
```

---

## Appendix B: Quality Gate Summary

| Gate | Enforced At | Severity | Blocking |
|------|-------------|----------|----------|
| Linting (ruff) | PR | Error | Yes |
| Type checking (mypy) | PR | Error | Yes |
| Tests pass (all platforms) | PR | Error | Yes |
| Test coverage ≥ 80% | PR | Warning | No (initially) |
| CVE scan (HIGH/CRITICAL) | PR, Release | Error | Yes |
| CVE scan (MEDIUM) | PR | Warning | No |
| SAST (Bandit) issues | PR | Warning | No (initially) |
| Version consistency | Release | Error | Yes |
| TestPyPI validation | Release | Error | Yes |
| Manual approval | Release | N/A | Yes |

---

## Appendix C: Estimated GitHub Actions Usage

For a public repository (free unlimited Actions minutes):

| Event | Frequency | Duration | Minutes/Month |
|-------|-----------|----------|---------------|
| PR checks | ~20/month | 5 min | 100 |
| Main branch push | ~30/month | 5 min | 150 |
| Security scans | 4/month (weekly) | 2 min | 8 |
| Releases | 2/month | 10 min | 20 |
| **Total** | | | **~280 min/month** |

**Cost:** $0 (public repository)

---

## References

- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [pip-audit documentation](https://github.com/pypa/pip-audit)
- [Bandit documentation](https://bandit.readthedocs.io/)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides)
- [SLSA Framework](https://slsa.dev/) (supply chain security levels)
