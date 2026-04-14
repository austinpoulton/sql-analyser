# Contributing to SQL Analyser

Thank you for considering contributing to SQL Analyser! This document explains our development process and quality standards.

## Table of Contents

- [Development Setup](#development-setup)
- [CI/CD Workflows](#cicd-workflows)
- [Running Checks Locally](#running-checks-locally)
- [Pull Request Process](#pull-request-process)
- [Quality Gates](#quality-gates)
- [Feature Development](#feature-development)

## Development Setup

SQL Analyser uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management.

### Prerequisites

- Python 3.12 or 3.13
- uv (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/austinpoulton/sql-analyser.git
cd sql-analyser

# Install dependencies
uv sync --all-groups

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

## CI/CD Workflows

SQL Analyser uses GitHub Actions for continuous integration and deployment. All workflows are defined in `.github/workflows/`.

### CI Workflow (ci.yml)

**Triggers:** Push to any branch, pull requests to main

**Jobs:**
1. **Lint and Type Check** - Runs ruff and mypy
2. **Test Matrix** - Runs tests on Python 3.12/3.13 × Ubuntu/macOS/Windows
3. **Build Validation** - Builds package and runs smoke test

### Security Workflow (security.yml)

**Triggers:** Push to main, PR to main, weekly schedule (Monday 00:00 UTC), manual dispatch

**Jobs:**
1. **Dependency Scan** - pip-audit checks for known CVEs
2. **SAST** - Bandit scans for security anti-patterns
3. **License Scan** - Checks for copyleft/unknown licenses
4. **Trivy Scan** - Comprehensive vulnerability and secret detection

Results are uploaded to the GitHub Security tab via SARIF.

### Release Workflow (release.yml)

**Triggers:** Git tags matching `v*.*.*` (e.g., `v0.1.0`)

**Process:**
1. Validates version consistency across `pyproject.toml`, `CITATION.cff`, and git tag
2. Builds wheel and sdist with SHA256 checksums
3. Scans built artifacts for vulnerabilities
4. Tests installation on Python 3.12 and 3.13
5. Publishes to TestPyPI for validation
6. Publishes to PyPI (requires manual approval)
7. Creates GitHub Release with changelog and artifacts

See [RELEASING.md](RELEASING.md) for detailed release instructions.

## Running Checks Locally

Before submitting a PR, run all checks locally to ensure they pass in CI.

### Linting

```bash
# Check code style
uv run ruff check .

# Check formatting
uv run ruff format --check .

# Auto-fix issues
uv run ruff check --fix .
uv run ruff format .
```

### Type Checking

```bash
uv run mypy src/
```

### Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term --cov-report=html

# View coverage report
open htmlcov/index.html  # On macOS
# or
xdg-open htmlcov/index.html  # On Linux
```

### Build Validation

```bash
# Build the package
uv build

# Install in clean environment
uv venv .venv-test
source .venv-test/bin/activate
uv pip install dist/*.whl

# Run smoke test
python -c "import sql_analyser; from sql_analyser import DataModel; print('OK')"
```

### Pre-Commit Hooks

Feature branches have pre-commit hooks configured (see `.git/hooks/pre-commit`). These run automatically on commit and block if checks fail.

To bypass in emergencies (not recommended):
```bash
git commit --no-verify
```

## Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding conventions in [CLAUDE.md](CLAUDE.md)

3. **Run all checks locally** (see above)

4. **Commit your changes** with clear, descriptive messages:
   ```bash
   git add .
   git commit -m "feat: Add support for X"
   ```

5. **Push to GitHub**:
   ```bash
   git push -u origin feature/your-feature-name
   ```

6. **Create a pull request** to `main`
   - Provide a clear description of changes
   - Reference any related issues or tickets
   - Wait for CI checks to pass

7. **Address review feedback**

8. **Merge** once approved and all checks pass

## Quality Gates

PRs must pass these quality gates before merging:

| Gate | Tool | Severity | Blocking? |
|------|------|----------|-----------|
| Code linting | ruff check | Error | ✅ Yes |
| Code formatting | ruff format | Error | ✅ Yes |
| Type checking | mypy | Error | ✅ Yes |
| Tests pass (all platforms) | pytest | Error | ✅ Yes |
| Test coverage ≥ 80% | pytest-cov | Warning | ⚠️ No (initially) |
| Dependency vulnerabilities (HIGH/CRITICAL) | pip-audit | Error | ✅ Yes |
| Dependency vulnerabilities (MEDIUM) | pip-audit | Warning | ⚠️ No |
| SAST issues | Bandit | Warning | ⚠️ No (initially) |
| Build succeeds | uv build | Error | ✅ Yes |

### Overriding Quality Gates

In exceptional cases, maintainers may override non-blocking gates. Document the reason in the PR description.

Blocking gates cannot be overridden. If a blocking gate fails, the issue must be fixed.

## Feature Development

SQL Analyser uses a structured feature development process:

1. **Feature Specification**: Features are documented in `features/XX-feature-name/PRD.md`
2. **Task Breakdown**: Implementation tasks are detailed in `features/XX-feature-name/TODO.md`
3. **Ticket Tracking**: Tasks are tracked using the `tk` CLI tool (see `tk help`)
4. **Feature Branches**: Work happens in `feature/XX-feature-name` branches
5. **Pre-Commit Hooks**: Feature branches have git hooks to enforce quality

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

## Testing Guidelines

- **Unit tests** for all new functionality
- **Integration tests** for cross-module behavior
- **Edge case coverage**: self-joins, subqueries, CTEs, etc.
- **Use fixtures** in `conftest.py` for shared test data
- **Descriptive test names**: `test_<what>_<when>_<expected>`

Example:
```python
def test_join_extraction_with_cte_resolves_base_table():
    """Verify that JOIN relationships resolve CTE aliases to base tables."""
    # ... test implementation
```

## Coding Conventions

See [CLAUDE.md](CLAUDE.md) for comprehensive coding standards. Key points:

- **Type hints** on all public functions
- **Docstrings** (Google style) on all public classes and functions
- **Imports**: stdlib → third-party → local, separated by blank lines
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **No star imports** (`from x import *`)

## Security

- **Never commit secrets** (API keys, tokens, credentials)
- **Review Dependabot PRs** carefully before merging
- **Report vulnerabilities** via GitHub Security Advisories

See [SECURITY.md](SECURITY.md) for our security policy.

## Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: See [README.md](README.md) and [CLAUDE.md](CLAUDE.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
