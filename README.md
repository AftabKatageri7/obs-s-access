# GitHub Collaborator Manager

A Python CLI tool for managing GitHub repository collaborators using YAML-based team definitions. Designed for the observability-s organization to maintain consistent access control across multiple repositories.

## Features

- **YAML-Based Configuration**: Define teams and their repository access in simple YAML files
- **GitHub Projects V2 Support**: Manage collaborator access to organization and repository project boards
- **Unified Access Management**: Configure both repository and project permissions in a single YAML file
- **Conflict Resolution**: Automatic handling of overlapping permissions with alphabetical file precedence
- **Dry-Run Mode**: Preview changes before applying them
- **Validate-Only Mode**: Validate YAML configurations without connecting to GitHub
- **Comprehensive Audit Logging**: JSON-formatted logs with ISO 8601 timestamps
- **Rate Limit Handling**: Automatic retry with exponential backoff for GitHub API rate limits
- **Zero-Trust Security**: Explicit-only permissions with comprehensive audit trails

## Installation

### Prerequisites

- Python 3.8 or higher
- GitHub Personal Access Token with appropriate permissions
- Access to the target GitHub organization

### Recommended: Use a Virtual Environment

It is **strongly recommended** to use a Python virtual environment to isolate this project's dependencies from your system Python installation.

#### Create and Activate Virtual Environment

**Using `venv` (built into Python 3.3+):**

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

**Using `virtualenv`:**

```bash
# Install virtualenv if needed
pip install virtualenv

# Create virtual environment
virtualenv .venv

# Activate it (same commands as above)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

**Verify activation:**
```bash
which python  # Should show path to .venv/bin/python
```

**Deactivate when done:**
```bash
deactivate
```

### Install Dependencies

**After activating your virtual environment**, install the required dependencies:

```bash
pip install -r requirements.txt
```

### Development Installation

For development work (includes testing tools):

```bash
pip install -r requirements-dev.txt
pip install -e .
```

**Note**: The `.gitignore` file is already configured to exclude virtual environment directories (`.venv/`, `venv/`, `env/`, `ENV/`), so your virtual environment won't be committed to version control.

## Configuration

### Environment Variables

The tool automatically loads environment variables from a `.env` file in the project root if it exists. Create a `.env` file (see `.env.example`):

```bash
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_ORG=observability-s
LOG_LEVEL=INFO
```

**Note**: The `.env` file is automatically loaded when you run the CLI. You don't need to manually export these variables or use tools like `source` or `dotenv`.

Alternatively, you can set environment variables manually or pass them as command-line arguments:

```bash
# Using environment variables
export GITHUB_TOKEN=your_token
export GITHUB_ORG=observability-s
github-collab-manager --teams-dir ./teams

# Using command-line arguments
github-collab-manager --teams-dir ./teams --github-token your_token --github-org observability-s
```

### GitHub Token Permissions

**Important**: This tool requires a **fine-grained personal access token**. Classic tokens are not supported by the organization.

Your fine-grained token must have the following permissions:

**Repository Permissions** (for repository collaborator management):
- **Administration**: Read and write
- **Metadata**: Read

**Organization Permissions** (for GitHub Projects V2 management):
- **Projects**: Read and write

To create a fine-grained token:
1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set the token name and expiration
4. Under "Repository access", select the repositories you need to manage
5. Under "Repository permissions", set:
   - **Administration**: Read and write
   - **Metadata**: Read
6. Under "Organization permissions", set:
   - **Projects**: Read and write
7. Click "Generate token" and copy it securely

**Note**: If you only need repository management (not projects), the Projects permission is optional. The tool will skip project operations if the token lacks this scope.

### Team Configuration Files

Create YAML files in a directory (e.g., `examples/teams/`) with the following structure:

```yaml
team_name: backend-team
users:
  - alice
  - bob
  - charlie
roles:
  push:
    - api-service
    - data-processor
  pull:
    - frontend-app
  admin:
    - infrastructure-repo
projects:  # Optional: GitHub Projects V2 access
  org_projects:
    write:
      - 1    # Main development board
      - 5    # Backend sprint planning
    read:
      - 3    # Company-wide roadmap
  repo_projects:
    write:
      - repo: api-service
        project: 2    # API feature tracking
```

**Valid Roles:**
- `pull` - Read-only access
- `triage` - Read access + issue management
- `push` - Read/write access
- `maintain` - Push access + repository management (no admin)
- `admin` - Full administrative access

### YAML Schema Reference

#### Complete Schema

```yaml
# Required: Unique identifier for the team
team_name: string (required, unique across all YAML files)

# Required: List of GitHub usernames
users:
  - string (required, at least one user)
  - string
  # ... more users

# Required: Role-to-repository mappings
roles:
  # Each role is optional, but at least one role must be defined
  pull:      # Read-only access
    - string (repository name)
    - string
  triage:    # Read + issue management
    - string
  push:      # Read/write access
    - string
  maintain:  # Push + repository management
    - string
  admin:     # Full administrative access
    - string
```

#### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `team_name` | string | Yes | Unique identifier for the team. Used for logging and conflict resolution. |
| `users` | list[string] | Yes | List of GitHub usernames. Must contain at least one user. |
| `roles` | object | Yes | Mapping of permission levels to repository lists. At least one role must be defined. |
| `roles.pull` | list[string] | No | Repositories with read-only access. |
| `roles.triage` | list[string] | No | Repositories with read + issue management access. |
| `roles.push` | list[string] | No | Repositories with read/write access. |
| `roles.maintain` | list[string] | No | Repositories with push + repository management access (no admin). |
| `roles.admin` | list[string] | No | Repositories with full administrative access. |

#### Validation Rules

1. **team_name**: Must be unique across all YAML files in the teams directory
2. **users**: Must contain at least one valid GitHub username
3. **roles**: Must contain at least one role with at least one repository
4. **Repository names**: Must be valid GitHub repository names (no special characters except hyphens and underscores)
5. **Duplicate users**: Same user can appear in multiple team files (last file alphabetically wins for conflicts)
6. **Duplicate repositories**: Same repository can appear under multiple roles in the same file (highest permission wins)

#### Projects Section (Optional)

The `projects:` section allows you to manage GitHub Projects V2 access alongside repository permissions:

```yaml
projects:
  org_projects:      # Organization-level projects
    <permission>:    # read, write, or admin
      - <project-number>
      - <project-number>
  repo_projects:     # Repository-level projects
    <permission>:    # read, write, or admin
      - repo: <repository-name>
        project: <project-number>
```

**Project Numbers**: Find the project number in the project URL:
- Organization project: `https://github.com/orgs/observability-s/projects/1` → project number is `1`
- Repository project: `https://github.com/observability-s/repo-name/projects/2` → project number is `2`

**Valid Project Permissions**:
- `read` - View project and items
- `write` - Edit project items and settings
- `admin` - Full project administration

#### Conflict Resolution

When the same user appears in multiple team files with different permissions for the same repository or project:

1. **Alphabetical precedence**: Files are processed in alphabetical order
2. **Last-wins**: The last file processed (alphabetically) determines the final permission
3. **Audit trail**: All conflicts are logged with source file information

Example:
```
teams/a-backend.yaml:  alice → api-service (push), project 1 (read)
teams/b-security.yaml: alice → api-service (admin), project 1 (write)
Result: alice gets admin access to repository and write access to project (b-security.yaml wins)
```

## Usage

### Basic Usage

Apply team configurations to GitHub:

```bash
github-collab-manager --teams-dir examples/teams
```

### Validate Configurations Only

Check YAML syntax and schema without connecting to GitHub:

```bash
github-collab-manager --teams-dir examples/teams --validate-only
```

### Dry-Run Mode

Preview changes without applying them:

```bash
github-collab-manager --teams-dir examples/teams --dry-run
```

### Custom GitHub Credentials

Override environment variables with command-line arguments:

```bash
github-collab-manager \
  --teams-dir examples/teams \
  --github-token YOUR_TOKEN \
  --github-org YOUR_ORG
```

### Adjust Log Level

Control logging verbosity:

```bash
github-collab-manager --teams-dir examples/teams --log-level DEBUG
```

Available log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`

### Remove Stale Collaborators

Detect and remove collaborators not defined in any team configuration:

```bash
# Report stale collaborators without removing them
github-collab-manager --teams-dir examples/teams --report-stale

# Remove stale collaborators (excludes organization members)
github-collab-manager --teams-dir examples/teams --remove-stale

# Dry-run: preview stale collaborator removals
github-collab-manager --teams-dir examples/teams --remove-stale --dry-run
```

**Note**: Organization members are automatically excluded from stale collaborator detection and removal, as they have implicit access to repositories and projects.

### Manage GitHub Projects Access

Grant collaborators access to GitHub Projects (v2) boards:

```bash
# Apply project access defined in team YAML files
github-collab-manager --teams-dir examples/teams

# Dry-run: preview project access changes
github-collab-manager --teams-dir examples/teams --dry-run

# Report stale project collaborators
github-collab-manager --teams-dir examples/teams --report-stale

# Remove stale project collaborators
github-collab-manager --teams-dir examples/teams --remove-stale
```

**Note**: Project access management requires the `project` scope in your GitHub token. If the token lacks this scope, project operations will be skipped with a warning.

## Command-Line Options

```
usage: github-collab-manager [-h] --teams-dir TEAMS_DIR [--dry-run]
                             [--validate-only] [--remove-stale] [--report-stale]
                             [--github-token TOKEN] [--github-org ORG]
                             [--log-level LEVEL]

Manage GitHub repository collaborators using YAML team definitions

required arguments:
  --teams-dir TEAMS_DIR
                        Directory containing team YAML files

optional arguments:
  -h, --help            Show this help message and exit
  --dry-run             Preview changes without applying them
  --validate-only       Validate YAML files without connecting to GitHub
  --remove-stale        Remove collaborators not defined in any team configuration
  --report-stale        Report stale collaborators without removing them
  --github-token TOKEN  GitHub personal access token (overrides GITHUB_TOKEN env var)
  --github-org ORG      GitHub organization name (overrides GITHUB_ORG env var)
  --log-level LEVEL     Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
```

## How It Works

### 1. Configuration Loading

The tool scans the specified directory for YAML files and loads team configurations. Each file defines:
- Team name (for logging and reporting)
- List of GitHub usernames
- Role-to-repository mappings

### 2. Conflict Resolution

When multiple teams grant different permissions to the same user on the same repository:
- Files are processed in **alphabetical order**
- **Last file wins** (alphabetically last filename takes precedence)
- Example: `a-team.yaml` grants `pull`, `z-team.yaml` grants `push` → final permission is `push`

### 3. Change Detection

For each repository, the tool:
1. Fetches current collaborators and their permissions
2. Compares with desired state from YAML configurations
3. Categorizes changes as:
   - **Additions**: New collaborators to add
   - **Updates**: Existing collaborators with permission changes
   - **No-ops**: Collaborators with unchanged permissions (skipped)

### 4. Change Application

- **Normal Mode**: Applies all additions and updates via GitHub API
- **Dry-Run Mode**: Logs planned changes without applying them
- **Validate-Only Mode**: Validates YAML syntax and schema only

### 5. Audit Logging

All operations are logged in JSON format with:
- ISO 8601 timestamps with timezone
- Action type (add_collaborator, update_collaborator, skip, error)
- User, repository, and role information
- Operation result (success, failure, skipped)
- Source team and file for traceability

## Examples

### Example 1: Backend Team with Repository and Project Access

File: `examples/teams/backend-team.yaml`

```yaml
team_name: backend-team
users:
  - alice
  - bob
roles:
  push:
    - api-service
    - data-processor
  pull:
    - frontend-app
projects:
  org_projects:
    write:
      - 1    # Main development board
      - 5    # Backend sprint planning
    read:
      - 3    # Company-wide roadmap
  repo_projects:
    write:
      - repo: api-service
        project: 2    # API feature tracking
```

Result:
- `alice` and `bob` get `push` access to `api-service` and `data-processor`
- `alice` and `bob` get `pull` access to `frontend-app`
- `alice` and `bob` get `write` access to organization projects 1 and 5
- `alice` and `bob` get `read` access to organization project 3
- `alice` and `bob` get `write` access to the api-service repository project 2

### Example 2: DevOps Team

File: `examples/teams/devops-team.yaml`

```yaml
team_name: devops-team
users:
  - charlie
  - diana
roles:
  admin:
    - infrastructure-repo
    - deployment-scripts
  push:
    - api-service
    - frontend-app
```

Result:
- `charlie` and `diana` get `admin` access to infrastructure repositories
- `charlie` and `diana` get `push` access to application repositories

### Example 3: Conflict Resolution

File: `examples/teams/a-junior-team.yaml`
```yaml
team_name: junior-team
users:
  - eve
roles:
  pull:
    - api-service
```

File: `examples/teams/b-senior-team.yaml`
```yaml
team_name: senior-team
users:
  - eve
roles:
  push:
    - api-service
```

Result:
- `eve` gets `push` access to `api-service` (b-senior-team.yaml wins alphabetically)

### Example 6: Project Managers with Only Project Access

File: `examples/teams/project-managers.yaml`

```yaml
team_name: project-managers
users:
  - pm-alice
  - pm-bob
roles: {}    # No repository access needed
projects:
  org_projects:
    admin:
      - 1    # Main development board
      - 5    # Backend sprint planning
      - 6    # Frontend sprint planning
    write:
      - 3    # Company-wide roadmap
```

Result:
- `pm-alice` and `pm-bob` get `admin` access to sprint planning boards
- `pm-alice` and `pm-bob` get `write` access to the roadmap
- No repository access is granted (empty `roles:` section)

## Troubleshooting

### Authentication Errors

**Problem**: `Authentication failed: Bad credentials`

**Solution**:
1. Verify your GitHub token is valid and not expired
   ```bash
   # Test token validity
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```
2. Check token has required permissions (fine-grained tokens only)
   - Go to https://github.com/settings/tokens?type=beta
   - Click on your token to view permissions
   - Ensure **Administration** is set to "Read and write" and **Metadata** is set to "Read"
3. Ensure token is correctly set in environment or command-line
   ```bash
   echo $GITHUB_TOKEN  # Should show your token
   ```

### Repository Not Found

**Problem**: `Repository not found: repo-name`

**Solution**:
1. Verify repository exists in the specified organization
   ```bash
   # List all repos in organization
   curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/orgs/YOUR_ORG/repos
   ```
2. Check your token has access to the repository
   - Private repos require `repo` scope
   - Public repos require `public_repo` scope minimum
3. Ensure repository name is correct (case-sensitive)
   - Use exact repository name as shown on GitHub
   - Do not include organization name (e.g., use `api-service` not `org/api-service`)

### Rate Limit Exceeded

**Problem**: `Rate limit exceeded`

**Solution**:
- The tool automatically retries with exponential backoff (3 retries by default)
- Wait for rate limit to reset (check with `--log-level DEBUG`)
  ```bash
  # Check current rate limit status
  curl -H "Authorization: token YOUR_TOKEN" \
    https://api.github.com/rate_limit
  ```
- Consider using a token with higher rate limits:
  - Authenticated requests: 5,000 requests/hour
  - Unauthenticated: 60 requests/hour
- Reduce the number of operations per run by splitting team files

### Validation Errors

**Problem**: `Validation failed: Missing required field`

**Solution**:
1. Check YAML syntax is correct
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('team.yaml'))"
   ```
2. Ensure all required fields are present: `team_name`, `users`, `roles`
3. Verify role names are valid: `pull`, `triage`, `push`, `maintain`, `admin`
4. Use `--validate-only` to test configurations before applying
   ```bash
   github-collab-manager --teams-dir ./teams --validate-only
   ```

### Permission Denied (403 Forbidden)

**Problem**: `Permission denied: Cannot add <user> to <repository>. The GitHub token lacks 'admin' or 'maintain' permissions for this repository.`

**Root Cause**: The GitHub Personal Access Token being used doesn't have sufficient permissions to manage collaborators on the specific repository. This is the most common error when managing repository access.

**Solution**:

1. **Verify Repository-Level Permissions**
   
   The token owner must have **admin** or **maintain** permissions on the target repository:
   
   ```bash
   # Check your permission level on a repository
   curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/repos/ORGANIZATION/REPOSITORY/collaborators/YOUR_USERNAME/permission
   ```
   
   Expected response should show `"permission": "admin"` or `"permission": "maintain"`.

2. **Check Token Permissions**
   
   Your fine-grained GitHub token must have the required repository permissions:
   
   - Go to https://github.com/settings/tokens?type=beta
   - Click on your token to view its permissions
   - Ensure **Administration** is set to "Read and write" and **Metadata** is set to "Read"
   - If missing, regenerate the token with correct permissions

3. **Verify Organization Role**
   
   Your organization role affects repository access:
   
   - **Organization Owner**: Has admin access to all repositories
   - **Organization Member**: Needs explicit repository permissions
   - **Outside Collaborator**: Cannot manage other collaborators
   
   Check your role:
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/orgs/ORGANIZATION/memberships/YOUR_USERNAME
   ```

4. **Request Repository Admin Access**
   
   If you don't have admin/maintain permissions:
   
   - Contact a repository administrator or organization owner
   - Request admin or maintain access to the repositories you need to manage
   - Alternatively, have an admin run the tool with their credentials

5. **Organization Settings**
   
   Some organizations restrict collaborator management:
   
   - Go to Organization Settings → Member privileges
   - Check "Base permissions" and "Repository creation" settings
   - Ensure members can manage collaborators (if you're not an owner)

**Workaround for Multiple Repositories**:

If you encounter 403 errors on some repositories but not others:

1. The tool will continue processing other repositories (fail-safe behavior)
2. Check the audit logs to see which repositories succeeded/failed
3. Use `--dry-run` first to identify problematic repositories
4. Split team configurations to separate accessible vs. inaccessible repos
5. Request appropriate permissions for the failing repositories

**Example Error Message**:
```
ERROR: Permission denied: Cannot add carlosteaches to sysdig-terraform-modules.
The GitHub token lacks 'admin' or 'maintain' permissions for this repository.
Please verify the token has sufficient access rights.
```

**Verification Steps**:
```bash
# 1. Test token validity
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# 2. Check your permission on specific repository
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/observability-s/sysdig-terraform-modules/collaborators/YOUR_USERNAME/permission

# 3. List repositories you have admin access to
curl -H "Authorization: token YOUR_TOKEN" \
  "https://api.github.com/user/repos?affiliation=owner,collaborator&per_page=100" | \
  jq '.[] | select(.permissions.admin == true) | .full_name'
```

### YAML Parsing Errors

**Problem**: `YAML parsing error: mapping values are not allowed here`

**Solution**:
1. Check for proper indentation (use spaces, not tabs)
2. Ensure colons are followed by a space
3. Quote strings containing special characters
4. Validate YAML structure:
   ```yaml
   # Correct
   roles:
     push:
       - repo1
       - repo2
   
   # Incorrect (missing space after colon)
   roles:
     push:
       -repo1
   ```

### Stale Collaborator Issues

**Problem**: Organization members showing as stale collaborators

**Solution**:
- Organization members are automatically excluded from stale detection
- If you see org members in stale reports, check:
  1. User is actually an organization member (not just a collaborator)
  2. GitHub API is returning correct organization membership
  3. Use `--report-stale` first to verify before removing

### Network/Connectivity Issues

**Problem**: `Connection timeout` or `Network unreachable`

**Solution**:
1. Check internet connectivity
2. Verify GitHub API is accessible:
   ```bash
   curl https://api.github.com/
   ```
3. Check for proxy or firewall restrictions
4. Try with `--log-level DEBUG` to see detailed network logs
5. Verify DNS resolution:
   ```bash
   nslookup api.github.com
   ```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_config_loader.py

# Run with verbose output
pytest -v
```

### Project Structure

```
github-collab-manager/
├── src/
│   └── github_collab_manager/
│       ├── __init__.py
│       ├── models.py              # Data models
│       ├── audit_logger.py        # Audit logging
│       ├── config_loader.py       # YAML loading and validation
│       ├── github_client.py       # GitHub API client
│       ├── manager.py             # Collaborator management logic
│       └── cli.py                 # Command-line interface
├── tests/
│   ├── test_models.py
│   ├── test_audit_logger.py
│   ├── test_config_loader.py
│   ├── test_github_client.py
│   ├── test_manager.py
│   └── test_cli_integration.py
├── examples/
│   └── teams/                     # Example team configurations
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Development dependencies
├── setup.py                       # Package configuration
├── .env.example                   # Environment variable template
└── README.md                      # This file
```

### Code Style

The project follows Python best practices:
- PEP 8 style guide
- Type hints for function signatures
- Comprehensive docstrings
- Immutable data models using `@dataclass(frozen=True)`

## Security Considerations

### Zero-Trust Model

This tool implements a zero-trust security model as defined in the project constitution:
- **Default Deny**: No access granted unless explicitly defined in YAML configurations
- **Explicit Permissions**: All grants must be declared in YAML files - no implicit or wildcard permissions
- **Audit Trail**: Every operation is logged with full context (timestamp, user, repository, role, result)
- **No Implicit Trust**: Network location or prior authentication doesn't grant access
- **Principle of Least Privilege**: Grant only the minimum permissions necessary for each user's role

### Best Practices

#### 1. Token Security

**DO**:
- ✅ Use fine-grained personal access tokens (classic tokens are not supported)
- ✅ Grant only the required permissions: Administration (read and write), Metadata (read)
- ✅ Store tokens in environment variables or secure secret management systems
- ✅ Rotate tokens regularly (every 90 days recommended)
- ✅ Use separate tokens for different environments (dev, staging, prod)
- ✅ Revoke tokens immediately when no longer needed

**DON'T**:
- ❌ Commit tokens to version control (use `.env` files with `.gitignore`)
- ❌ Share tokens between team members
- ❌ Use tokens with broader permissions than necessary
- ❌ Store tokens in plain text files
- ❌ Use the same token across multiple tools or services

#### 2. Configuration Management

**DO**:
- ✅ Store team YAML files in version control (Git)
- ✅ Require pull request reviews for configuration changes
- ✅ Use branch protection rules for configuration repositories
- ✅ Implement approval workflows for production changes
- ✅ Maintain separate configuration directories for different environments
- ✅ Document the rationale for permission grants in commit messages

**DON'T**:
- ❌ Make direct changes to production configurations without review
- ❌ Grant admin access unless absolutely necessary
- ❌ Use wildcard or overly broad permissions
- ❌ Skip validation before applying changes

#### 3. Access Control

**DO**:
- ✅ Follow the principle of least privilege
- ✅ Grant the minimum role required for each user's responsibilities
- ✅ Use `pull` for read-only access
- ✅ Use `push` for developers who need write access
- ✅ Reserve `admin` for repository administrators only
- ✅ Regularly audit and remove stale collaborators
- ✅ Document why each user needs access to each repository

**DON'T**:
- ❌ Grant `admin` access by default
- ❌ Give everyone `push` access "just in case"
- ❌ Leave collaborators with access after they leave the team
- ❌ Grant access to repositories users don't actively work on

#### 4. Operational Security

**DO**:
- ✅ Always use `--dry-run` first to preview changes
- ✅ Use `--validate-only` to test configurations before applying
- ✅ Review audit logs after each operation
- ✅ Monitor for unexpected permission changes
- ✅ Set up alerts for failed operations
- ✅ Keep audit logs for compliance and incident investigation
- ✅ Test configuration changes in a non-production environment first

**DON'T**:
- ❌ Run the tool with production credentials on untested configurations
- ❌ Ignore validation warnings
- ❌ Skip dry-run mode for large changes
- ❌ Disable audit logging

#### 5. Incident Response

**Preparation**:
1. Document who has access to GitHub tokens
2. Maintain a list of all repositories managed by the tool
3. Keep audit logs in a secure, centralized location
4. Have a process for emergency token revocation

**If a token is compromised**:
1. Immediately revoke the compromised token on GitHub
2. Review audit logs for unauthorized operations
3. Generate a new token with fresh credentials
4. Audit all repositories for unexpected collaborators
5. Use `--report-stale` to identify unauthorized access
6. Document the incident and lessons learned

#### 6. Compliance and Auditing

**DO**:
- ✅ Retain audit logs for compliance requirements (typically 90 days minimum)
- ✅ Regularly review access grants against business needs
- ✅ Document access control policies and procedures
- ✅ Conduct periodic access reviews (quarterly recommended)
- ✅ Use `--report-stale` regularly to identify unused access
- ✅ Maintain an audit trail of who approved each configuration change

**DON'T**:
- ❌ Delete audit logs prematurely
- ❌ Skip regular access reviews
- ❌ Grant access without documented business justification

### Security Checklist

Before running in production:

- [ ] GitHub token is a fine-grained token with required permissions (Administration: read and write, Metadata: read)
- [ ] Token is stored securely (environment variable or secret manager)
- [ ] Team YAML files are in version control with review process
- [ ] Tested with `--validate-only` and `--dry-run`
- [ ] Audit logging is enabled and logs are being collected
- [ ] Access grants follow principle of least privilege
- [ ] Emergency token revocation process is documented
- [ ] Regular access review schedule is established
- [ ] Stale collaborator detection is configured (`--report-stale`)

### Secrets Management

**Never commit secrets to version control:**
- Use `.env` files (excluded by `.gitignore`)
- Use environment variables in CI/CD pipelines
- Consider using secret management tools (AWS Secrets Manager, HashiCorp Vault)

### Principle of Least Privilege

- Grant minimum permissions necessary for each role
- Use `pull` for read-only access
- Reserve `admin` for infrastructure and deployment repositories only
- Regularly review and audit access grants

## Exit Codes

- `0` - Success
- `1` - Validation error, API error, or general failure
- `130` - Keyboard interrupt (Ctrl+C)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## API Reference

### Command-Line Interface

#### `apply` Command

Apply collaborator changes to GitHub repositories.

```bash
github-collab-manager apply --config <path> [options]
```

**Options:**
- `--config PATH` (required): Path to YAML configuration file or directory
- `--dry-run`: Preview changes without applying them
- `--remove-stale`: Remove collaborators not defined in any configuration
- `--github-token TOKEN`: GitHub personal access token (or use `GITHUB_TOKEN` env var)
- `--org ORG`: GitHub organization name (or use `GITHUB_ORG` env var)
- `--audit-log PATH`: Path to audit log file (default: `audit.log`)

**Exit Codes:**
- `0`: Success - all operations completed successfully
- `1`: Failure - one or more operations failed
- `130`: Interrupted - user cancelled with Ctrl+C

**Examples:**

```bash
# Apply single configuration file
github-collab-manager apply --config teams/engineering.yaml

# Apply all configurations in directory
github-collab-manager apply --config teams/

# Preview changes without applying (dry-run)
github-collab-manager apply --config teams/ --dry-run

# Apply changes and remove stale collaborators
github-collab-manager apply --config teams/ --remove-stale

# Use custom audit log location
github-collab-manager apply --config teams/ --audit-log /var/log/github-collab.log
```

#### `validate` Command

Validate YAML configuration files without connecting to GitHub.

```bash
github-collab-manager validate --config <path>
```

**Options:**
- `--config PATH` (required): Path to YAML configuration file or directory

**Exit Codes:**
- `0`: Success - all configurations are valid
- `1`: Failure - one or more configurations are invalid

**Examples:**

```bash
# Validate single configuration file
github-collab-manager validate --config teams/engineering.yaml

# Validate all configurations in directory
github-collab-manager validate --config teams/

# Validate before applying
github-collab-manager validate --config teams/ && \
  github-collab-manager apply --config teams/
```

### Python API

#### ConfigLoader

Load and validate YAML configuration files.

```python
from github_collab_manager.config_loader import ConfigLoader

loader = ConfigLoader()
configs = loader.load_configs(["teams/engineering.yaml", "teams/operations.yaml"])
```

**Methods:**

- `load_configs(config_paths: List[str]) -> List[TeamConfig]`
  - Load and validate configuration files
  - Raises `ValueError` for invalid YAML or missing required fields
  - Returns list of `TeamConfig` objects

#### GitHubClient

Interact with GitHub API for collaborator management.

```python
from github_collab_manager.github_client import GitHubClient

client = GitHubClient(token="ghp_...", org="observability-s")
collaborators = client.get_repository_collaborators("observability-s/repo-name")
```

**Methods:**

- `get_repository_collaborators(repo: str) -> List[CollaboratorInfo]`
  - Get current collaborators for a repository
  - Returns list of `CollaboratorInfo` objects with username and permission

- `add_collaborator(repo: str, username: str, permission: str) -> None`
  - Add collaborator to repository with specified permission
  - Permission must be one of: `pull`, `push`, `admin`
  - Raises `Exception` on API errors

- `update_collaborator_permission(repo: str, username: str, permission: str) -> None`
  - Update existing collaborator's permission
  - Permission must be one of: `pull`, `push`, `admin`
  - Raises `Exception` on API errors

- `remove_collaborator(repo: str, username: str) -> None`
  - Remove collaborator from repository
  - Raises `Exception` on API errors

#### CollaboratorManager

High-level manager for planning and applying collaborator changes.

```python
from github_collab_manager.manager import CollaboratorManager
from github_collab_manager.audit_logger import AuditLogger

logger = AuditLogger("audit.log")
manager = CollaboratorManager(client, logger)

# Plan changes
plan = manager.plan_changes(configs, remove_stale=False)

# Apply changes
results = manager.apply_changes(plan)
```

**Methods:**

- `plan_changes(configs: List[TeamConfig], remove_stale: bool) -> ChangePlan`
  - Generate plan of changes needed to reach desired state
  - Compares desired state from configs with current GitHub state
  - Returns `ChangePlan` with additions, updates, and removals

- `apply_changes(plan: ChangePlan) -> List[OperationResult]`
  - Execute planned changes against GitHub API
  - Returns list of `OperationResult` objects with success/failure status
  - Continues on errors, returns all results

#### AuditLogger

Structured JSON logging for all operations.

```python
from github_collab_manager.audit_logger import AuditLogger

logger = AuditLogger("audit.log")
logger.log_operation(
    action="add_collaborator",
    repo="observability-s/repo-name",
    username="alice",
    permission="push",
    success=True
)
```

**Methods:**

- `log_operation(action: str, repo: str, username: str, permission: str, success: bool, error: str = None) -> None`
  - Log operation to audit file
  - Creates structured JSON entry with ISO 8601 timestamp
  - Includes all operation details and outcome

### Data Models

#### TeamConfig

Represents a team configuration from YAML.

```python
@dataclass
class TeamConfig:
    role_name: str
    members: List[str]
    repositories: List[RepositoryPermission]
```

#### RepositoryPermission

Represents repository access permission.

```python
@dataclass
class RepositoryPermission:
    repo: str
    permission: str  # "pull", "push", or "admin"
```

#### CollaboratorInfo

Represents current collaborator state from GitHub.

```python
@dataclass
class CollaboratorInfo:
    username: str
    permission: str  # "pull", "push", or "admin"
```

#### ChangePlan

Represents planned changes to be applied.

```python
@dataclass
class ChangePlan:
    additions: List[PlannedChange]
    updates: List[PlannedChange]
    removals: List[PlannedChange]
```

#### PlannedChange

Represents a single planned change.

```python
@dataclass
class PlannedChange:
    repo: str
    username: str
    permission: str
    reason: str  # Human-readable explanation
```

#### OperationResult

Represents the result of an applied change.

```python
@dataclass
class OperationResult:
    action: str  # "add_collaborator", "update_permission", "remove_collaborator", "no_change"
    repo: str
    username: str
    permission: str
    success: bool
    error: Optional[str] = None
```

### Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (required)
- `GITHUB_ORG`: GitHub organization name (required)

### Required GitHub Token Permissions

**Important**: Only fine-grained personal access tokens are supported.

Your fine-grained token must have the following **repository permissions**:

- **Administration**: Read and write
  - Required for managing repository collaborators
- **Metadata**: Read
  - Required for reading repository information

To create a fine-grained token:
1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set the token name and expiration
4. Under "Repository access", select the repositories you need to manage
5. Under "Repository permissions", set:
   - **Administration**: Read and write
   - **Metadata**: Read
6. Click "Generate token" and copy it securely

## License

[Add your license information here]

## Support

For issues, questions, or contributions, please [open an issue](https://github.com/observability-s/obs-s-access/issues) on GitHub.

---

**Made with Bob**
