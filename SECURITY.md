# Security Policy

## Supported Versions

SQL Analyser follows semantic versioning. Security updates are provided for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

We recommend always using the latest release to ensure you have the latest security patches.

## Security Scanning

SQL Analyser employs automated security scanning to detect vulnerabilities before they reach users.

### Dependency Vulnerability Scanning

**Tool:** [pip-audit](https://github.com/pypa/pip-audit)
**Frequency:** Weekly (Monday 00:00 UTC) + on every PR
**Database:** PyPA Advisory Database + OSV

All Python dependencies are scanned for known CVEs (Common Vulnerabilities and Exposures). Results are uploaded to the [GitHub Security tab](../../security/code-scanning) in SARIF format.

**Quality Gates:**
- **HIGH/CRITICAL vulnerabilities**: Block PR merges and releases
- **MEDIUM vulnerabilities**: Warning only (manual review required)
- **LOW vulnerabilities**: Informational

### Static Application Security Testing (SAST)

**Tool:** [Bandit](https://bandit.readthedocs.io/)
**Frequency:** Weekly + on every PR
**Coverage:** All source code in `src/`

Bandit scans for common Python security anti-patterns, including:
- Hardcoded secrets or passwords
- SQL injection vulnerabilities
- Use of insecure functions (e.g., `eval`, `exec`)
- Weak cryptographic practices

Currently in **warning mode** - issues are reported but don't block merges while we establish a baseline.

### License Compliance

**Tool:** [pip-licenses](https://github.com/raimon49/pip-licenses)
**Frequency:** Weekly + on every PR

All dependencies are scanned for license information. The following licenses are flagged:
- **GPL/AGPL/LGPL**: Copyleft licenses that may restrict usage
- **Unknown**: Packages without clear license information

### Comprehensive Scanning (Optional)

**Tool:** [Trivy](https://github.com/aquasecurity/trivy)
**Frequency:** Weekly
**Coverage:** Vulnerabilities, secrets, misconfigurations

Trivy provides additional scanning for:
- Infrastructure-as-Code misconfigurations
- Secrets accidentally committed to the repository
- Container vulnerabilities (if applicable in future)

Results are visible in the [GitHub Security tab](../../security/code-scanning).

## Viewing Security Scan Results

### GitHub Security Tab

1. Navigate to the repository [Security tab](../../security)
2. Click **Code scanning alerts**
3. Filter by tool:
   - `dependency-scan` - pip-audit results
   - `sast-bandit` - Bandit SAST results
   - `trivy-scan` - Trivy comprehensive scan

### Pull Request Checks

Security scans run automatically on all pull requests. Results appear as:
- **Check runs** in the PR "Checks" tab
- **SARIF annotations** on the "Files changed" tab (if issues found)
- **Status checks** that must pass before merging

### Workflow Runs

View detailed scan output in GitHub Actions:
1. Navigate to [Actions](../../actions)
2. Select the **Security Scanning** workflow
3. Click a workflow run to see detailed logs

## Reporting a Vulnerability

If you discover a security vulnerability in SQL Analyser, please report it responsibly.

### Reporting Process

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, use one of these methods:

#### Option 1: GitHub Security Advisories (Preferred)

1. Navigate to the [Security tab](../../security)
2. Click **Advisories** → **Report a vulnerability**
3. Fill out the advisory form with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

#### Option 2: Private Email

Email the maintainer directly at: [security contact to be added]

Include:
- **Subject**: "SQL Analyser Security Vulnerability"
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Your contact information for follow-up

### What to Expect

1. **Acknowledgment**: We will acknowledge receipt within **48 hours**

2. **Assessment**: We will assess the vulnerability and determine:
   - Severity (Critical, High, Medium, Low)
   - Affected versions
   - Mitigation strategy

3. **Fix Development**: We will develop a fix on a private security branch

4. **Testing**: The fix will be tested to ensure it resolves the issue without introducing regressions

5. **Disclosure**: We will coordinate disclosure with you:
   - **Embargo period**: Typically 7-14 days to allow users to update
   - **Public disclosure**: After the fix is released
   - **Credit**: We will credit you in the security advisory (if desired)

6. **Release**: A patch release will be published with the security fix

### Severity Levels

We use the [CVSS v3.1](https://www.first.org/cvss/calculator/3.1) scoring system:

- **Critical** (9.0-10.0): Immediate patch release
- **High** (7.0-8.9): Patch release within 7 days
- **Medium** (4.0-6.9): Patch release within 30 days
- **Low** (0.1-3.9): Fixed in next regular release

## Dependabot

SQL Analyser uses [Dependabot](https://docs.github.com/en/code-security/dependabot) for automated dependency updates.

### Configuration

Dependabot is configured in `.github/dependabot.yml`:
- **Schedule**: Weekly (Monday)
- **Ecosystems**: Python (pip)
- **Auto-creates PRs** for:
  - Security updates (all severities)
  - Minor and patch version updates
- **Ignores**: Major version updates (manual review required)

### Handling Dependabot PRs

When Dependabot creates a PR:

1. **Review the changelog** for the updated dependency
2. **Check CI results** - all tests must pass
3. **Review security scan results** - no new vulnerabilities
4. **Merge** if everything looks good

**For security updates:**
- Prioritize merging within 7 days
- Test locally if making significant changes

**For version updates:**
- Review for breaking changes
- Coordinate with planned releases

## Security Best Practices for Contributors

### Do Not Commit Secrets

- **Never** commit API keys, tokens, passwords, or credentials
- Use environment variables for sensitive configuration
- Review changes before committing: `git diff --staged`

### Verify Dependencies

- Only add dependencies from trusted sources (PyPI)
- Check dependency licenses before adding
- Review dependency security advisories

### Code Review

- Review security implications of code changes
- Check for SQL injection risks (even though we use sqlglot AST, not string concatenation)
- Verify input validation for user-supplied data

### Local Security Testing

Before submitting a PR, run security scans locally:

```bash
# Install security tools
uv tool install pip-audit
uv tool install bandit

# Scan dependencies
uv tool run pip-audit

# Scan source code
uv tool run bandit -r src/
```

## Supply Chain Security

### PyPI Trusted Publishing

SQL Analyser uses PyPI's [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) feature for secure, tokenless publishing.

**Benefits:**
- No long-lived API tokens
- OIDC-based authentication
- Audit trail of all releases
- Reduced risk of token compromise

### Package Signing

Releases include:
- **SHA256 checksums** for all artifacts
- **Provenance attestations** (future: Sigstore signing)

Verify package integrity:

```bash
# Download checksums from GitHub Release
wget https://github.com/austinpoulton/sql-analyser/releases/download/v0.1.0/checksums.txt

# Verify wheel
sha256sum --check checksums.txt
```

### Software Bill of Materials (SBOM)

Future releases will include a CycloneDX SBOM listing all dependencies.

## Security Monitoring

### Continuous Monitoring

- **Dependabot alerts**: Enabled for dependency vulnerabilities
- **Code scanning alerts**: Enabled for SAST findings
- **Secret scanning**: Enabled to detect accidentally committed secrets

### Maintainer Notifications

Maintainers receive email notifications for:
- New security advisories
- Dependabot alerts
- Code scanning findings

## Security Contacts

- **GitHub Security Advisories**: [Report a vulnerability](../../security/advisories/new)
- **Maintainer**: Austin Poulton (GitHub: @austinpoulton)

## Changelog

| Date       | Change                                    |
|------------|-------------------------------------------|
| 2026-04-14 | Initial security policy                   |
| 2026-04-14 | Added automated security scanning details |

## Acknowledgments

We thank the security researchers and contributors who help keep SQL Analyser secure.

## References

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PyPA Security](https://www.pypa.io/en/latest/specifications/security/)
- [NIST NVD](https://nvd.nist.gov/)
