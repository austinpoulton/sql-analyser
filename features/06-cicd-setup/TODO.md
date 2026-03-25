# TODO: GitHub CI/CD Pipeline with Security Scanning

**Feature ID:** 06-cicd-setup
**Status:** Planning → In Progress
**Author:** Austin Poulton
**Created:** 2026-03-25

---

## Overview

This TODO breaks down the PRD into actionable implementation tasks across 5 phases. Each phase builds on the previous one, following the dependency chain outlined in the PRD.

**Total Estimated Time:** 12-16 hours

---

## Phase 1: CI Workflow (FR-001) — Priority P0

**Goal:** Establish comprehensive CI pipeline for linting, type checking, testing, and build validation.

**Estimated Time:** 4-5 hours

### Task 1.1: Setup GitHub Actions Infrastructure
- [ ] Create `.github/workflows/` directory
- [ ] Create `.github/actions/` directory for reusable actions
- [ ] Create composite action `.github/actions/setup-uv/action.yml` for consistent uv setup across jobs
  - Include uv installation
  - Cache configuration for dependencies
  - Python version setup

**Dependencies:** None
**Acceptance Criteria:**
- Directory structure matches PRD technical spec
- Reusable action documented with inputs/outputs

---

### Task 1.2: Create Lint and Type Check Job
- [ ] Create `.github/workflows/ci.yml`
- [ ] Configure triggers: push to all branches, PR to main
- [ ] Implement job: `lint-and-type-check`
  - Run `ruff check .`
  - Run `ruff format --check .`
  - Run `mypy src/`
- [ ] Use composite setup-uv action
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 1.1
**Acceptance Criteria:**
- Job runs on every commit
- Fails on any linting/formatting/type errors
- Completes in < 1 minute

---

### Task 1.3: Create Test Matrix Job
- [ ] Add job: `test` in `ci.yml`
- [ ] Configure matrix:
  - Python versions: 3.12, 3.13
  - OS: ubuntu-latest, macos-latest, windows-latest
- [ ] Steps:
  - Checkout code
  - Use setup-uv action
  - Install dependencies: `uv sync --all-groups`
  - Run tests: `uv run pytest --cov=src --cov-report=xml --cov-report=term`
  - Upload coverage to artifacts (for future Codecov integration)
- [ ] Set job timeout: 10 minutes

**Dependencies:** Task 1.1
**Acceptance Criteria:**
- Tests run on 6 platform combinations (3 OS × 2 Python versions)
- Coverage report generated
- All tests must pass for job to succeed

---

### Task 1.4: Create Build Validation Job
- [ ] Add job: `build` in `ci.yml`
- [ ] Depends on: `lint-and-type-check`, `test` (must wait for both)
- [ ] Steps:
  - Build wheel and sdist: `uv build`
  - Create clean virtualenv
  - Install built wheel: `uv pip install dist/*.whl`
  - Run smoke test:
    ```python
    import sql_analyser
    from sql_analyser import DataModel, QueriedTable
    print(f"sql-analyser v{sql_analyser.__version__} smoke test passed")
    ```
  - Upload artifacts (wheel, sdist) with 30-day retention
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 1.3
**Acceptance Criteria:**
- Build succeeds without errors
- Wheel installs cleanly
- Smoke test imports all public API classes
- Artifacts stored and downloadable

---

### Task 1.5: Add Quality Gates and Status Checks
- [ ] Configure required status checks in GitHub repo settings:
  - `lint-and-type-check`
  - `test (matrix)`
  - `build`
- [ ] Add coverage threshold check (80%) — initially as warning, not blocking
- [ ] Document override process for exceptional cases

**Dependencies:** Tasks 1.2-1.4
**Acceptance Criteria:**
- PRs cannot be merged if required checks fail
- Coverage report visible in PR comments (if Codecov integrated)
- All gates documented in project README or CONTRIBUTING.md

---

### Task 1.6: Test and Validate CI Workflow
- [ ] Create test branch with intentional failures:
  - Linting error (unused import)
  - Type error (wrong annotation)
  - Test failure (assert False)
- [ ] Verify each failure blocks PR merge
- [ ] Fix issues and verify green checks
- [ ] Measure workflow execution time (target: < 5 min)

**Dependencies:** Task 1.5
**Acceptance Criteria:**
- All failure modes tested
- Workflow completes in target time
- Error messages are clear and actionable

---

## Phase 2: Security Scanning (FR-002) — Priority P0

**Goal:** Implement dependency and code security scanning with SARIF integration.

**Estimated Time:** 3-4 hours

### Task 2.1: Create Security Workflow File
- [ ] Create `.github/workflows/security.yml`
- [ ] Configure triggers:
  - Push to `main`
  - Pull requests to `main`
  - Schedule: `cron: '0 0 * * 1'` (Monday 00:00 UTC)
  - `workflow_dispatch` (manual trigger)
- [ ] Add workflow-level permissions:
  ```yaml
  permissions:
    contents: read
    security-events: write
  ```

**Dependencies:** Phase 1 complete
**Acceptance Criteria:**
- Workflow triggers correctly on all events
- Can be manually triggered from Actions tab
- Permissions scoped to least privilege

---

### Task 2.2: Implement Dependency Vulnerability Scan (pip-audit)
- [ ] Add job: `dependency-scan`
- [ ] Steps:
  - Checkout code
  - Setup Python 3.12
  - Install uv and dependencies
  - Install pip-audit: `uv tool install pip-audit`
  - Run scan with SARIF output:
    ```bash
    uv tool run pip-audit --format sarif --output pip-audit-report.sarif
    ```
  - Upload SARIF to GitHub Security tab
  - Fail on HIGH/CRITICAL vulnerabilities
  - Warn on MEDIUM vulnerabilities
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 2.1
**Acceptance Criteria:**
- Scan runs successfully
- SARIF report appears in Security tab > Code scanning alerts
- HIGH/CRITICAL vulnerabilities block workflow
- MEDIUM vulnerabilities logged but don't block

---

### Task 2.3: Implement SAST with Bandit
- [ ] Add job: `sast-scan`
- [ ] Steps:
  - Checkout code
  - Setup Python 3.12
  - Install bandit: `uv tool install bandit`
  - Run scan on src/ directory:
    ```bash
    uv tool run bandit -r src/ -f sarif -o bandit-report.sarif
    ```
  - Upload SARIF to GitHub Security tab
  - Initially warn on issues (don't block), upgrade to blocking after baseline established
- [ ] Set job timeout: 3 minutes

**Dependencies:** Task 2.1
**Acceptance Criteria:**
- Bandit scans all source code
- SARIF report appears in Security tab
- Common security anti-patterns detected (hardcoded secrets, SQL injection patterns)

---

### Task 2.4: Implement License Compliance Check
- [ ] Add job: `license-scan`
- [ ] Steps:
  - Install pip-licenses: `uv tool install pip-licenses`
  - Run scan:
    ```bash
    uv tool run pip-licenses --format=json --output-file=licenses.json
    ```
  - Parse JSON and flag:
    - GPL/AGPL licenses (copyleft concern)
    - Unknown licenses
  - Generate summary report
- [ ] Set job timeout: 2 minutes

**Dependencies:** Task 2.1
**Acceptance Criteria:**
- All dependencies have identified licenses
- Copyleft licenses flagged (if any)
- Report uploaded as artifact

---

### Task 2.5: Optional — Trivy Comprehensive Scan (P1)
- [ ] Add job: `trivy-scan` (can_fail: true initially)
- [ ] Steps:
  - Install Trivy
  - Scan for:
    - Vulnerabilities: `trivy fs --scanners vuln .`
    - Secrets: `trivy fs --scanners secret .`
    - Misconfigurations: `trivy fs --scanners config .`
  - Generate SARIF output
  - Upload to Security tab
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 2.1
**Acceptance Criteria:**
- Trivy installed via GitHub Action marketplace
- Multi-scanner mode enabled
- Results visible in Security tab

---

### Task 2.6: Test Security Workflows
- [ ] Trigger weekly scheduled scan manually
- [ ] Verify SARIF uploads appear in Security > Code scanning
- [ ] Test with intentional vulnerability:
  - Temporarily downgrade a dependency with known CVE
  - Verify pip-audit detects and fails
  - Remove test vulnerability
- [ ] Document security scan process in SECURITY.md

**Dependencies:** Tasks 2.2-2.5
**Acceptance Criteria:**
- All scans run successfully
- Security tab populated with results
- False positives documented with suppression strategy

---

## Phase 3: Release Automation (FR-003) — Priority P0

**Goal:** Automate package building, testing, and publishing to PyPI on version tags.

**Estimated Time:** 4-5 hours

### Task 3.1: Create Release Workflow File
- [ ] Create `.github/workflows/release.yml`
- [ ] Configure trigger:
  ```yaml
  on:
    push:
      tags:
        - 'v*.*.*'
  ```
- [ ] Add workflow-level permissions:
  ```yaml
  permissions:
    contents: write
    id-token: write  # For PyPI trusted publishing
  ```

**Dependencies:** Phase 2 complete
**Acceptance Criteria:**
- Workflow only triggers on version tags (e.g., v0.1.0)
- Permissions scoped appropriately

---

### Task 3.2: Implement Version Validation Job
- [ ] Add job: `validate-release`
- [ ] Steps:
  - Checkout code
  - Extract version from tag: `${GITHUB_REF#refs/tags/v}`
  - Read version from `pyproject.toml`: `grep version pyproject.toml`
  - Read version from `CITATION.cff`: `grep ^version CITATION.cff`
  - Compare all three versions
  - Fail if versions don't match
- [ ] Set job timeout: 2 minutes

**Dependencies:** Task 3.1
**Acceptance Criteria:**
- Detects version mismatches
- Clear error message if validation fails
- Extracts version correctly from all sources

---

### Task 3.3: Implement Package Build Job
- [ ] Add job: `build-packages`
- [ ] Depends on: `validate-release`
- [ ] Steps:
  - Checkout code
  - Setup uv
  - Build packages: `uv build`
  - Generate SHA256 checksums:
    ```bash
    cd dist
    sha256sum * > checksums.txt
    ```
  - Upload artifacts: wheel, sdist, checksums
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 3.2
**Acceptance Criteria:**
- Both wheel (.whl) and source dist (.tar.gz) built
- Checksums file includes both artifacts
- Artifacts uploaded with 90-day retention

---

### Task 3.4: Implement Security Scan of Built Artifacts
- [ ] Add job: `scan-artifacts`
- [ ] Depends on: `build-packages`
- [ ] Download build artifacts
- [ ] Install pip-audit
- [ ] Scan wheel file:
  ```bash
  pip-audit --file dist/*.whl
  ```
- [ ] Fail on HIGH/CRITICAL vulnerabilities
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 3.3
**Acceptance Criteria:**
- Scans built wheel (not just source dependencies)
- Blocks release if vulnerabilities found
- Clear error output

---

### Task 3.5: Implement Test Installation Job
- [ ] Add job: `test-installation`
- [ ] Depends on: `scan-artifacts`
- [ ] Matrix: Python 3.12, 3.13
- [ ] Steps:
  - Download artifacts
  - Create clean virtualenv
  - Install wheel: `uv pip install dist/*.whl`
  - Run integration tests (if any) or smoke test:
    ```python
    import sql_analyser
    import sqlglot

    sql = "SELECT * FROM orders"
    tree = sqlglot.parse_one(sql)
    result = sql_analyser.analyse(tree)
    assert len(result.data_model.tables) == 1
    print("Installation test passed!")
    ```
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 3.4
**Acceptance Criteria:**
- Installs cleanly on both Python versions
- All imports work
- Basic functionality verified

---

### Task 3.6: Implement TestPyPI Publication
- [ ] Add job: `publish-testpypi`
- [ ] Depends on: `test-installation`
- [ ] Steps:
  - Download artifacts
  - Publish to TestPyPI using trusted publisher (OIDC):
    ```yaml
    - uses: pypa/gh-action-pypi-publish@release/v1
      with:
        repository-url: https://test.pypi.org/legacy/
        skip-existing: true
    ```
  - Wait 30 seconds for package availability
  - Install from TestPyPI in clean env
  - Run smoke test
- [ ] Set job timeout: 10 minutes

**Dependencies:** Task 3.5
**Acceptance Criteria:**
- Package published to TestPyPI
- Can install from TestPyPI
- Smoke test passes

**Note:** Requires TestPyPI trusted publisher configuration (manual setup by maintainer)

---

### Task 3.7: Implement PyPI Publication with Approval Gate
- [ ] Create GitHub environment: `production`
  - Required reviewers: 1 (maintainer)
  - Deployment branches: Tags matching `v*`
- [ ] Add job: `publish-pypi`
- [ ] Depends on: `publish-testpypi`
- [ ] Environment: `production` (triggers manual approval)
- [ ] Steps:
  - Download artifacts
  - Publish to PyPI using trusted publisher:
    ```yaml
    - uses: pypa/gh-action-pypi-publish@release/v1
    ```
- [ ] Set job timeout: 10 minutes

**Dependencies:** Task 3.6
**Acceptance Criteria:**
- Workflow pauses for manual approval
- Only runs after approval granted
- Successfully publishes to PyPI

**Note:** Requires PyPI trusted publisher configuration (manual setup by maintainer)

---

### Task 3.8: Implement GitHub Release Creation
- [ ] Add job: `create-release`
- [ ] Depends on: `publish-pypi`
- [ ] Steps:
  - Download artifacts
  - Generate release notes from commits since last tag:
    ```bash
    git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --pretty=format:"- %s"
    ```
  - Create GitHub Release using `gh`:
    ```yaml
    - uses: actions/create-release@v1
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        body: <release notes>
        draft: false
        prerelease: false
    ```
  - Upload artifacts: wheel, sdist, checksums.txt
- [ ] Set job timeout: 5 minutes

**Dependencies:** Task 3.7
**Acceptance Criteria:**
- GitHub Release created with proper tag
- All artifacts attached to release
- Release notes include commit summaries
- Marked as latest release

---

### Task 3.9: Test Release Workflow End-to-End
- [ ] Create test tag on feature branch: `v0.1.0-test`
- [ ] Verify workflow triggers
- [ ] Test version validation (intentionally break it first)
- [ ] Test build process
- [ ] Verify TestPyPI publication (if configured)
- [ ] Document release process in RELEASING.md

**Dependencies:** Tasks 3.1-3.8
**Acceptance Criteria:**
- Full release workflow tested (except production PyPI publish)
- All error conditions tested
- Release process documented

---

## Phase 4: Dependabot Configuration (FR-004) — Priority P1

**Goal:** Automate dependency update PRs.

**Estimated Time:** 1 hour

### Task 4.1: Create Dependabot Configuration
- [ ] Create `.github/dependabot.yml`
- [ ] Configure pip ecosystem:
  - Directory: `/`
  - Schedule: weekly (Monday)
  - Groups:
    - `production`: sqlglot, pydantic, jinja2
    - `dev`: pytest, mypy, ruff, pytest-cov
  - Auto-create PRs for:
    - Security updates (all severities)
    - Minor and patch version updates
  - Ignore major version updates (require manual decision)

**Dependencies:** Phases 1-3 complete
**Acceptance Criteria:**
- Dependabot configuration file valid
- Groups configured correctly
- Schedule set to weekly

---

### Task 4.2: Configure Dependabot PR Settings
- [ ] Add `.github/dependabot.yml` labels:
  - `dependencies` for all PRs
  - `security` for security updates
- [ ] Set commit message prefix: `chore(deps):`
- [ ] Configure PR title format: `chore(deps): bump <package> from X to Y`

**Dependencies:** Task 4.1
**Acceptance Criteria:**
- Dependabot PRs have consistent formatting
- Labels applied automatically
- Easy to identify security vs. routine updates

---

### Task 4.3: Test Dependabot Integration
- [ ] Enable Dependabot in repository settings
- [ ] Manually trigger check for updates
- [ ] Verify CI runs on Dependabot PRs
- [ ] Review and merge a test Dependabot PR
- [ ] Document Dependabot review process

**Dependencies:** Task 4.2
**Acceptance Criteria:**
- Dependabot PRs trigger CI workflows
- All security checks run
- Merge process documented

---

## Phase 5: Optimizations and Enhancements (FR-005) — Priority P2

**Goal:** Performance optimizations and optional security enhancements.

**Estimated Time:** 2-3 hours

### Task 5.1: Implement Dependency Caching
- [ ] Update `.github/actions/setup-uv/action.yml` to cache:
  - uv cache directory: `~/.cache/uv`
  - Cache key: `${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}`
  - Restore keys: `${{ runner.os }}-uv-`
- [ ] Add pip-audit database caching:
  - Cache key: `${{ runner.os }}-pip-audit-${{ steps.date.outputs.date }}`
  - Daily refresh

**Dependencies:** Phase 1 complete
**Acceptance Criteria:**
- Cache hit rate > 80% for repeat runs
- CI execution time reduced by 30-50%
- Cache size reasonable (< 500 MB)

---

### Task 5.2: Generate Software Bill of Materials (SBOM)
- [ ] Add job to `release.yml`: `generate-sbom`
- [ ] Use CycloneDX format (better Python support than SPDX)
- [ ] Install cyclonedx-bom:
  ```bash
  uv tool install cyclonedx-bom
  uv tool run cyclonedx-py --format json --output sbom.json
  ```
- [ ] Upload SBOM as release artifact

**Dependencies:** Phase 3 complete
**Acceptance Criteria:**
- SBOM generated in CycloneDX format
- Includes all production dependencies
- Attached to GitHub Release
- Valid against CycloneDX schema

---

### Task 5.3: Implement Sigstore Package Signing (Optional P1)
- [ ] Add step to `release.yml` after PyPI publish
- [ ] Use sigstore action:
  ```yaml
  - uses: sigstore/gh-action-sigstore-python@v1
    with:
      inputs: dist/*.whl dist/*.tar.gz
  ```
- [ ] Upload signatures (.sigstore) to GitHub Release
- [ ] Document verification process in README

**Dependencies:** Task 3.8
**Acceptance Criteria:**
- Artifacts signed with Sigstore
- Signatures verifiable using `sigstore verify`
- Verification instructions documented

---

### Task 5.4: Configure Coverage Tracking (Optional)
- [ ] Sign up for Codecov (free for open source)
- [ ] Add `CODECOV_TOKEN` to repository secrets
- [ ] Update `ci.yml` test job:
  ```yaml
  - uses: codecov/codecov-action@v3
    with:
      files: ./coverage.xml
      flags: unittests
      fail_ci_if_error: false  # Don't block on Codecov outages
  ```
- [ ] Add coverage badge to README

**Dependencies:** Task 1.3
**Acceptance Criteria:**
- Coverage reports uploaded to Codecov
- Historical coverage trends visible
- Badge shows current coverage percentage

---

### Task 5.5: Add CodeQL Advanced Security (Optional)
- [ ] Create `.github/workflows/codeql.yml`
- [ ] Configure for Python
- [ ] Schedule: weekly
- [ ] Upload results to Security tab

**Dependencies:** Phase 2 complete
**Acceptance Criteria:**
- CodeQL scans run weekly
- Results integrated with GitHub Security
- No false positive noise

---

## Phase 6: Documentation and Finalization

**Goal:** Complete documentation and cleanup.

**Estimated Time:** 1-2 hours

### Task 6.1: Create CONTRIBUTING.md
- [ ] Document CI/CD workflows
- [ ] Explain how to run checks locally
- [ ] Describe PR process and quality gates
- [ ] Link to security scanning documentation

**Dependencies:** Phases 1-4 complete
**Acceptance Criteria:**
- Contributors understand CI requirements
- Local testing instructions clear
- Quality gate expectations documented

---

### Task 6.2: Create RELEASING.md
- [ ] Document release process step-by-step
- [ ] Explain version bumping in pyproject.toml and CITATION.cff
- [ ] Describe tag creation and push
- [ ] Explain approval process for PyPI publication
- [ ] Document rollback process

**Dependencies:** Phase 3 complete
**Acceptance Criteria:**
- Any maintainer can perform a release following docs
- Emergency rollback procedure documented
- TestPyPI vs. PyPI differences explained

---

### Task 6.3: Create or Update SECURITY.md
- [ ] Document security scanning processes
- [ ] Explain vulnerability disclosure process
- [ ] Link to GitHub Security tab
- [ ] Describe Dependabot workflow
- [ ] List supported versions

**Dependencies:** Phase 2 complete
**Acceptance Criteria:**
- Security policy clear for users
- Vulnerability reporting process defined
- Aligns with GitHub Security tab

---

### Task 6.4: Update README.md
- [ ] Add badges:
  - CI status
  - Security scan status
  - PyPI version
  - Python version support
  - License
  - Coverage (if Codecov configured)
- [ ] Link to CONTRIBUTING.md, SECURITY.md, RELEASING.md
- [ ] Mention PyPI trusted publishing

**Dependencies:** All phases complete
**Acceptance Criteria:**
- Badges functional and accurate
- README reflects CI/CD capabilities
- Documentation cross-linked

---

### Task 6.5: Final Testing and Validation
- [ ] Run full CI pipeline on feature branch
- [ ] Verify all workflows pass
- [ ] Check GitHub Security tab population
- [ ] Test manual workflow dispatch triggers
- [ ] Review all workflow logs for warnings
- [ ] Measure total execution time vs. targets

**Dependencies:** All implementation tasks complete
**Acceptance Criteria:**
- All workflows green
- No workflow warnings or errors
- Execution times within targets (PR CI < 5 min)
- Security tab properly populated

---

### Task 6.6: Create Pull Request to Main
- [ ] Ensure feature branch up to date with main
- [ ] Create PR with comprehensive description:
  - Summary of CI/CD capabilities
  - Link to PRD
  - Screenshot of successful workflow runs
  - Security scan results
- [ ] Request review from maintainer
- [ ] Address review feedback
- [ ] Merge to main after approval

**Dependencies:** Task 6.5
**Acceptance Criteria:**
- PR description comprehensive
- All CI checks pass on PR
- Approved by maintainer
- Merged with squash commit or merge commit (per project convention)

---

## External Setup Requirements

**These tasks must be performed manually by the repository maintainer:**

### PyPI Trusted Publisher Configuration
1. Log in to PyPI
2. Navigate to sql-analyser project settings
3. Add trusted publisher:
   - Owner: `austinpoulton` (or organization)
   - Repository: `sql-analyser`
   - Workflow: `release.yml`
   - Environment: `production`

### TestPyPI Trusted Publisher Configuration
1. Repeat above steps for test.pypi.org
2. Use same workflow and environment names

### GitHub Environment Configuration
1. Navigate to repository Settings > Environments
2. Create environment: `production`
3. Add protection rules:
   - Required reviewers: 1
   - Deployment branches: Tags only, pattern `v*`

### Dependabot Enablement
1. Navigate to repository Settings > Code security and analysis
2. Enable Dependabot alerts
3. Enable Dependabot security updates
4. Dependabot configuration file (`.github/dependabot.yml`) will be read automatically

### GitHub Actions Permissions
1. Navigate to Settings > Actions > General
2. Set Workflow permissions: "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests" (for Dependabot)

---

## Success Criteria Summary

This feature is complete when:

- ✅ All P0 tasks (Phases 1-3) are complete and tested
- ✅ CI runs on every PR and enforces quality gates
- ✅ Security scans run weekly and on PRs
- ✅ Release can be performed by creating a git tag
- ✅ All workflows documented
- ✅ PR to main merged successfully
- ✅ First release published via automated pipeline

**P1/P2 tasks** (Phase 4-5 optimizations) can be completed in follow-up PRs if time-constrained.

---

## Estimated Timeline

| Phase | Priority | Estimated Time | Cumulative |
|-------|----------|----------------|------------|
| Phase 1: CI Workflow | P0 | 4-5 hours | 5 hours |
| Phase 2: Security Scanning | P0 | 3-4 hours | 9 hours |
| Phase 3: Release Automation | P0 | 4-5 hours | 14 hours |
| Phase 4: Dependabot | P1 | 1 hour | 15 hours |
| Phase 5: Optimizations | P2 | 2-3 hours | 18 hours |
| Phase 6: Documentation | P0 | 1-2 hours | 20 hours |

**Total: 12-20 hours** (P0 only: ~12 hours, with P1/P2: ~20 hours)

---

## Notes

- **Testing Strategy:** Each phase should be tested incrementally. Don't wait until the end to test all workflows together.
- **Git Workflow:** Follow feature branch workflow per CLAUDE.md. Set up pre-commit hooks on feature branch.
- **Ticket Management:** Create tickets for each task using `tk` CLI. Update status as work progresses.
- **Security:** Never commit secrets or tokens. Use GitHub OIDC trusted publishing, not API tokens.
- **Rollback Plan:** If workflows fail in production, manual release process should be documented as fallback.

---

## Open Questions Resolved

Per PRD Appendix:

1. **Code coverage target:** Yes, enforce 80% as warning (not blocking initially)
2. **Auto-merge Dependabot:** No, manual review for first few months
3. **Artifact signing:** P1 priority, implement in Phase 5
4. **SBOM format:** CycloneDX (Phase 5)
