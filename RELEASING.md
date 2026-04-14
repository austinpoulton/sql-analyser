# Release Process

This document describes the automated release process for SQL Analyser.

## Overview

SQL Analyser uses an automated release workflow that builds, tests, and publishes packages to PyPI when a version tag is created. The process is fully automated after manual approval.

## Prerequisites

### One-Time Setup (Maintainers Only)

#### 1. PyPI Trusted Publisher Configuration

Configure trusted publishing on both PyPI and TestPyPI to enable OIDC-based authentication (no API tokens required).

**PyPI:**
1. Log in to [pypi.org](https://pypi.org)
2. Navigate to sql-analyser project settings
3. Go to "Publishing" → "Add a new publisher"
4. Configure:
   - **Owner**: `austinpoulton`
   - **Repository name**: `sql-analyser`
   - **Workflow name**: `release.yml`
   - **Environment name**: `production`

**TestPyPI:**
1. Repeat above steps on [test.pypi.org](https://test.pypi.org)
2. Use identical configuration

#### 2. GitHub Environment Configuration

1. Navigate to repository **Settings** → **Environments**
2. Create environment: `production`
3. Add protection rules:
   - **Required reviewers**: 1 (select maintainer)
   - **Deployment branches**: Select "Protected branches" or add rule for tags `v*`

#### 3. Enable Dependabot

1. Navigate to **Settings** → **Code security and analysis**
2. Enable **Dependabot alerts**
3. Enable **Dependabot security updates**
4. The `.github/dependabot.yml` configuration will be used automatically

## Release Workflow

### Step 1: Prepare the Release

#### 1.1 Update Version Numbers

Update the version in **three** locations (they must match):

**pyproject.toml:**
```toml
[project]
name = "sql-analyser"
version = "0.2.0"  # Update this
```

**CITATION.cff:**
```yaml
version: "0.2.0"  # Update this
date-released: "2026-04-14"  # Update to release date
```

**Git tag:**
Will be created in Step 2.

#### 1.2 Update Changelog (if applicable)

If you maintain a CHANGELOG.md, update it with:
- New features
- Bug fixes
- Breaking changes
- Deprecations

#### 1.3 Commit Version Bump

```bash
git add pyproject.toml CITATION.cff CHANGELOG.md
git commit -m "chore: Bump version to 0.2.0"
git push origin main
```

### Step 2: Create and Push Version Tag

```bash
# Ensure you're on the latest main branch
git checkout main
git pull origin main

# Create the version tag (include 'v' prefix)
git tag v0.2.0

# Push the tag to trigger the release workflow
git push origin v0.2.0
```

**Important:** The tag must match the version in `pyproject.toml` and `CITATION.cff` exactly (except for the `v` prefix).

### Step 3: Monitor the Release Workflow

The release workflow will start automatically when the tag is pushed.

#### 3.1 Watch Workflow Progress

```bash
# View workflow runs
gh run list --workflow=release.yml --limit 5

# Watch the latest run
gh run watch
```

Or visit: https://github.com/austinpoulton/sql-analyser/actions/workflows/release.yml

#### 3.2 Workflow Stages

The workflow executes these stages sequentially:

1. **Validate Release** (~5 seconds)
   - Extracts version from tag
   - Verifies `pyproject.toml` version matches
   - Verifies `CITATION.cff` version matches
   - **Fails if versions don't match**

2. **Build Packages** (~1 minute)
   - Builds wheel (`.whl`) and source distribution (`.tar.gz`)
   - Generates SHA256 checksums
   - Uploads artifacts

3. **Security Scan Artifacts** (~30 seconds)
   - Scans built wheel with pip-audit
   - **Fails if HIGH/CRITICAL vulnerabilities found**

4. **Test Installation** (~1 minute)
   - Tests installation on Python 3.12 and 3.13
   - Runs smoke test
   - Verifies basic functionality

5. **Publish to TestPyPI** (~1 minute)
   - Publishes package to test.pypi.org
   - Waits 30 seconds for availability
   - Installs from TestPyPI
   - Runs verification test

6. **Publish to PyPI** (~1 minute + approval time)
   - **Pauses for manual approval** (production environment protection)
   - After approval, publishes to pypi.org using OIDC trusted publisher

7. **Create GitHub Release** (~10 seconds)
   - Generates changelog from commits since last tag
   - Creates GitHub Release
   - Attaches wheel, sdist, and checksums

### Step 4: Approve PyPI Publication

After TestPyPI publication succeeds, the workflow will pause for approval.

#### 4.1 Review TestPyPI Package

Before approving, verify the TestPyPI package:

```bash
# Install from TestPyPI in a clean environment
uv venv .venv-testpypi
source .venv-testpypi/bin/activate

uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ sql-analyser==0.2.0

# Test basic functionality
python -c "import sql_analyser; print(sql_analyser.__version__)"
```

#### 4.2 Approve in GitHub

1. Navigate to the workflow run: https://github.com/austinpoulton/sql-analyser/actions/workflows/release.yml
2. Click the paused **publish-pypi** job
3. Review the deployment details
4. Click **Review deployments**
5. Select **production** environment
6. Click **Approve and deploy**

The workflow will continue and publish to PyPI within ~1 minute.

### Step 5: Verify Publication

#### 5.1 Check PyPI

Visit https://pypi.org/project/sql-analyser/ and verify:
- Version number is correct
- Package description renders properly
- Release date is shown

#### 5.2 Test Installation from PyPI

```bash
# Clean install from PyPI
uv venv .venv-pypi
source .venv-pypi/bin/activate

uv pip install sql-analyser==0.2.0

# Verify installation
python -c "
import sql_analyser
import sqlglot

print(f'Installed sql-analyser v{sql_analyser.__version__}')

# Quick functional test
sql = 'SELECT id, name FROM users WHERE active = 1'
tree = sqlglot.parse_one(sql)
result = sql_analyser.analyse(tree)
print(f'Tables: {[t.name for t in result.data_model.tables]}')
"
```

#### 5.3 Check GitHub Release

Visit https://github.com/austinpoulton/sql-analyser/releases and verify:
- Release is created with correct tag
- Changelog includes all commits
- Artifacts are attached (wheel, sdist, checksums)

## Troubleshooting

### Version Mismatch Error

**Error:**
```
Version mismatch detected!
Tag version (0.2.0) does not match pyproject.toml (0.1.0) or CITATION.cff (0.1.0)
```

**Solution:**
1. Delete the tag: `git tag -d v0.2.0 && git push origin :refs/tags/v0.2.0`
2. Update `pyproject.toml` and `CITATION.cff` to match the intended version
3. Commit the changes
4. Create the tag again

### Security Scan Fails

**Error:**
```
Found 2 vulnerabilities in dependencies
```

**Solution:**
1. Review the vulnerability report in the workflow logs
2. Update vulnerable dependencies in `pyproject.toml`
3. Run `uv lock` to update `uv.lock`
4. Test locally: `uv sync && uv run pytest`
5. Commit and push changes
6. Delete and recreate the tag

### TestPyPI Verification Fails

**Error:**
```
Installation from TestPyPI failed
```

**Solution:**
1. Check if the package was actually published to TestPyPI
2. Verify network connectivity to test.pypi.org
3. Check for name conflicts with existing packages
4. Review TestPyPI logs for upload errors

### PyPI Publication Fails

**Error:**
```
Trusted publisher verification failed
```

**Solution:**
1. Verify PyPI trusted publisher configuration (see Prerequisites)
2. Check that:
   - Owner is `austinpoulton`
   - Repository is `sql-analyser`
   - Workflow is `release.yml`
   - Environment is `production`
3. Re-save the trusted publisher configuration on PyPI
4. Delete and recreate the tag

## Rollback Procedure

### Yanking a Release from PyPI

If a release has critical issues:

```bash
# Yank the release (package remains installable if version is pinned, but won't be discovered)
uv tool install twine
twine yank sql-analyser --version 0.2.0 --reason "Critical bug in version 0.2.0"
```

### Deleting a GitHub Release

```bash
# Delete the release
gh release delete v0.2.0 --yes

# Delete the tag
git tag -d v0.2.0
git push origin :refs/tags/v0.2.0
```

### Publishing a Hotfix

After yanking or fixing issues:

1. Create a new patch version (e.g., `0.2.1`)
2. Fix the issue
3. Follow the normal release process

## Manual Release (Emergency Fallback)

If GitHub Actions is unavailable, release manually:

### Build Locally

```bash
# Ensure clean state
git checkout main
git pull origin main

# Build packages
uv build

# Verify checksums
cd dist
sha256sum * > checksums.txt
```

### Publish to PyPI

Using API token (if trusted publishing unavailable):

```bash
uv tool install twine

# Publish to TestPyPI first
twine upload --repository testpypi dist/*

# After verification, publish to PyPI
twine upload dist/*
```

### Create GitHub Release Manually

```bash
# Create release with artifacts
gh release create v0.2.0 \
  --title "Release v0.2.0" \
  --notes "$(git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --pretty=format:'- %s (%h)')" \
  dist/*.whl \
  dist/*.tar.gz \
  dist/checksums.txt
```

## Release Checklist

Use this checklist for each release:

- [ ] All tests passing on main branch
- [ ] Version updated in `pyproject.toml`
- [ ] Version updated in `CITATION.cff`
- [ ] `CITATION.cff` date updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Version bump committed and pushed
- [ ] Tag created and pushed
- [ ] Workflow monitored until TestPyPI publication
- [ ] TestPyPI package verified
- [ ] PyPI publication approved
- [ ] PyPI package verified
- [ ] GitHub Release verified
- [ ] Announcement posted (if applicable)

## Release Cadence

- **Patch releases** (0.1.x): Bug fixes, security updates - as needed
- **Minor releases** (0.x.0): New features, non-breaking changes - monthly or as needed
- **Major releases** (x.0.0): Breaking changes - planned in advance

## Questions?

For questions about the release process, open a GitHub Discussion or contact the maintainer.
