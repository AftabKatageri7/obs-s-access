# Implementation Plan: GitHub Collaborator Manager

**Feature**: GitHub Collaborator Manager  
**Branch**: `001-github-collab-manager`  
**Created**: 2026-03-06  
**Status**: In Planning

---

## Technical Context

### Technology Stack

- **Language**: Python 3.8+
- **Core Libraries**:
  - `PyYAML` - YAML parsing and validation
  - `PyGithub` - GitHub API client library
  - `requests` - HTTP client for API calls (used by PyGithub)
  - `python-dotenv` - Environment variable management (optional, for development)
- **Standard Library**:
  - `pathlib` - File system operations
  - `logging` - Structured logging to stdout
  - `argparse` - Command-line argument parsing
  - `json` - JSON formatting for structured logs
  - `time` - Timestamp generation and retry delays
  - `sys` - Exit codes and stdout/stderr handling
  - `os` - Environment variable access

### Architecture Pattern

**Command-Line Application with Layered Architecture**:

1. **CLI Layer** (`cli.py`): Argument parsing, mode selection (apply/dry-run/validate), orchestration
2. **Configuration Layer** (`config.py`): YAML loading, parsing, validation, schema enforcement
3. **GitHub Integration Layer** (`github_client.py`): API authentication, rate limit handling, collaborator operations
4. **Business Logic Layer** (`manager.py`): Conflict resolution, change detection, operation planning
5. **Logging Layer** (`audit_logger.py`): Structured audit log generation, stdout formatting

### Project Structure

```
obs-s-access/
├── src/
│   └── github_collab_manager/
│       ├── __init__.py
│       ├── cli.py                    # Entry point, argument parsing
│       ├── config.py                 # YAML loading and validation
│       ├── github_client.py          # GitHub API wrapper
│       ├── manager.py                # Core business logic
│       ├── audit_logger.py           # Structured logging
│       └── models.py                 # Data classes (TeamConfig, AccessGrant, etc.)
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_github_client.py
│   ├── test_manager.py
│   ├── test_audit_logger.py
│   └── fixtures/
│       └── sample_teams/             # Sample YAML files for testing
├── examples/
│   └── teams/                        # Example team configurations
│       ├── backend-team.yaml
│       ├── frontend-team.yaml
│       └── devops-team.yaml
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Development dependencies (pytest, etc.)
├── setup.py                          # Package installation
├── README.md                         # Usage documentation
└── .env.example                      # Example environment variables

```

### Key Dependencies

- **PyGithub** (v2.1+): Official GitHub API library with built-in rate limit handling
- **PyYAML** (v6.0+): Safe YAML parsing with schema validation support
- **pytest** (v7.0+, dev): Testing framework
- **pytest-mock** (v3.10+, dev): Mocking for GitHub API calls in tests

### Integration Points

- **GitHub REST API v3**: Collaborator management endpoints
  - `GET /repos/{owner}/{repo}/collaborators` - List collaborators
  - `PUT /repos/{owner}/{repo}/collaborators/{username}` - Add/update collaborator
  - `DELETE /repos/{owner}/{repo}/collaborators/{username}` - Remove collaborator
  - `GET /repos/{owner}/{repo}` - Verify repository exists
  - `GET /users/{username}` - Verify user exists (optional validation)
- **Environment Variables**: `GITHUB_TOKEN` for API authentication
- **File System**: Read YAML files from specified directory
- **Standard Output**: Structured JSON logs for audit trail

### Configuration Management

- **Team Configuration Files**: YAML files in a directory (default: `./teams/`)
- **Environment Variables**:
  - `GITHUB_TOKEN` (required): Personal Access Token with repo admin permissions
  - `GITHUB_ORG` (optional): Organization name (default: `observability-s`)
  - `LOG_LEVEL` (optional): Logging verbosity (default: `INFO`)

### Error Handling Strategy

- **Validation Errors**: Fail fast before any API calls (YAML syntax, schema, required fields)
- **API Errors**: Graceful degradation with detailed error reporting
  - Repository not found: Log error, skip repository, continue processing
  - User not found: Log warning, skip user, continue processing
  - Permission denied: Log error, skip operation, continue processing
  - Rate limit: Automatic retry with exponential backoff
  - Network timeout: Retry with exponential backoff (max 3 attempts)
- **Conflict Resolution**: Deterministic (alphabetical file order, last wins)
- **Exit Codes**:
  - `0`: Success (all operations completed)
  - `1`: Validation errors (invalid YAML, missing required fields)
  - `2`: Authentication failure (invalid or missing GITHUB_TOKEN)
  - `3`: Partial failure (some operations failed, see logs)

---

## Constitution Check

### Principle 1: Security-First

**Alignment**: ✅ **COMPLIANT**

- **Default deny-all**: System only grants access explicitly defined in YAML configurations
- **Zero-trust**: No implicit permissions; every access grant requires explicit YAML entry
- **Audit logging**: All operations (add/update/remove) logged with full context (timestamp, user, repo, role, result)
- **Explicit permissions**: YAML schema requires explicit role assignment for each repository

**Implementation**:
- Configuration parser validates that all access grants are explicitly declared
- No wildcard or implicit role inheritance
- Audit logger captures every API operation with structured output
- Dry-run mode allows verification before applying changes

### Principle 2: Principle of Least Privilege

**Alignment**: ✅ **COMPLIANT**

- **Minimal scope**: Each user-repository pair has exactly one role (read, triage, write, maintain, admin)
- **Regular access reviews**: YAML-based configuration enables version-controlled access reviews
- **RBAC**: Role-based grouping in YAML (users inherit roles for repository groups)

**Implementation**:
- YAML schema enforces single role per user-repository combination
- Conflict resolution (last file wins) ensures deterministic role assignment
- Configuration files in version control enable audit trail and review process
- Script supports removal of stale collaborators (P4) for access hygiene

**Note**: Time-bound permissions are not implemented in this phase but can be added via external scheduling (e.g., temporary team files that are removed after expiration).

### Principle 3: Clear Authorization Model

**Alignment**: ✅ **COMPLIANT**

- **Declarative policies**: YAML files define "what" access (user → role → repositories), not "how"
- **Policy-as-code**: YAML files stored in version control, reviewable via pull requests
- **Testable rules**: Dry-run mode validates policies without applying changes; unit tests verify parsing and conflict resolution
- **Documented decision logic**: YAML schema documented in spec; conflict resolution rules explicit (alphabetical order, last wins)
- **Transparent evaluation**: Structured logs show every decision (add/update/skip) with reasoning

**Implementation**:
- YAML schema is well-documented with examples
- Dry-run mode reports planned changes before execution
- Structured logs include action type, affected entities, and result
- Configuration validation happens before any API calls
- Error messages reference specific YAML files and line numbers where possible

### Gate Evaluation

**Status**: ✅ **PASS** - All constitutional principles are satisfied by the design.

**Justification**: The GitHub Collaborator Manager implements a declarative, auditable access control system that aligns with all three constitutional principles. The YAML-based configuration provides explicit, version-controlled policy definitions. Structured audit logging ensures accountability. The role-based model enforces least privilege. No constitutional conflicts exist.

---

## Phase 0: Research & Clarification Resolution

### Research Tasks

All technical unknowns have been resolved through the clarification process. No additional research required.

**Resolved Clarifications**:
1. ✅ Authentication: Personal Access Token from `GITHUB_TOKEN` environment variable
2. ✅ Rate limiting: Exponential backoff with Retry-After header respect
3. ✅ Conflict resolution: Last processed file wins (alphabetical filename order)
4. ✅ Non-existent repositories: Report error, skip repository, continue processing
5. ✅ Audit logging: Structured logging to stdout with timestamp, action, user, repository, role, result

### Technology Decisions

**Decision**: Use PyGithub library for GitHub API interactions  
**Rationale**: Official Python library with built-in rate limit handling, authentication, and retry logic. Reduces boilerplate code and provides type-safe API access.  
**Alternatives Considered**: 
- `requests` library with manual API calls: More control but requires implementing rate limiting, pagination, and error handling
- `github3.py`: Alternative GitHub library, but PyGithub has better documentation and community support

**Decision**: Use PyYAML for configuration parsing  
**Rationale**: Standard Python YAML library with safe loading and schema validation support. Well-tested and widely used.  
**Alternatives Considered**:
- `ruamel.yaml`: Better round-trip preservation, but unnecessary for read-only configuration
- `strictyaml`: Stricter validation, but PyYAML's safe_load is sufficient for our schema

**Decision**: Use JSON format for structured logs  
**Rationale**: Machine-parseable, widely supported by log aggregation tools, easy to parse with standard libraries.  
**Alternatives Considered**:
- Key-value pairs: Less structured, harder to parse nested data
- Plain text: Not machine-parseable, defeats audit requirements

**Decision**: Use argparse for CLI argument parsing  
**Rationale**: Standard library, no external dependencies, sufficient for our needs.  
**Alternatives Considered**:
- `click`: More features but adds dependency
- `typer`: Modern alternative but requires Python 3.6+ and adds dependency

---

## Phase 1: Design Artifacts

### Data Model

See [`data-model.md`](./data-model.md) for complete entity definitions and relationships.

**Core Entities**:
- `TeamConfig`: Represents a YAML team configuration file
- `AccessGrant`: Represents a user-repository-role assignment
- `AuditLogEntry`: Represents a logged operation
- `OperationResult`: Represents the outcome of an API operation

### API Contracts

See [`contracts/`](./contracts/) directory for OpenAPI specifications.

**Key Operations**:
- `load_team_configs(directory: Path) -> List[TeamConfig]`
- `validate_config(config: TeamConfig) -> ValidationResult`
- `apply_access_grants(grants: List[AccessGrant], dry_run: bool) -> List[OperationResult]`
- `remove_stale_collaborators(repos: List[str], dry_run: bool) -> List[OperationResult]`

### Quickstart Guide

See [`quickstart.md`](./quickstart.md) for setup and usage instructions.

---

## Phase 2: Implementation Phases

### Phase 2.1: Project Setup & Core Models

**Objective**: Establish project structure, dependencies, and data models.

**Deliverables**:
- Project directory structure
- `requirements.txt` with PyGithub, PyYAML
- `setup.py` for package installation
- `models.py` with data classes (TeamConfig, AccessGrant, AuditLogEntry, OperationResult)
- Basic README with installation instructions

**Validation**: Can install package and import models without errors.

### Phase 2.2: Configuration Loading & Validation

**Objective**: Implement YAML parsing and schema validation.

**Deliverables**:
- `config.py` with YAML loading logic
- Schema validation for required fields (team_name, users, roles)
- Role name validation (read, triage, write, maintain, admin)
- Error reporting with file names and line numbers
- Unit tests for valid and invalid YAML files

**Validation**: Can load valid YAML files and reject invalid ones with clear error messages.

### Phase 2.3: GitHub API Client

**Objective**: Implement GitHub API wrapper with authentication and rate limiting.

**Deliverables**:
- `github_client.py` with PyGithub integration
- Authentication via GITHUB_TOKEN environment variable
- Rate limit handling with exponential backoff
- Repository existence validation
- Collaborator listing, adding, updating, removing
- Unit tests with mocked API responses

**Validation**: Can authenticate to GitHub and perform basic operations (with mocked API in tests).

### Phase 2.4: Business Logic & Conflict Resolution

**Objective**: Implement core logic for processing team configurations.

**Deliverables**:
- `manager.py` with conflict resolution logic
- Alphabetical file processing order
- Last-wins conflict resolution for duplicate user-repo pairs
- Change detection (add vs. update vs. no-op)
- Dry-run mode support
- Unit tests for conflict scenarios

**Validation**: Can process multiple team files and resolve conflicts deterministically.

### Phase 2.5: Audit Logging

**Objective**: Implement structured logging to stdout.

**Deliverables**:
- `audit_logger.py` with JSON log formatting
- ISO 8601 timestamps with timezone
- Log entries for all operations (add, update, skip, error)
- Configurable log levels (INFO, DEBUG, ERROR)
- Unit tests for log format validation

**Validation**: Logs are machine-parseable JSON with all required fields.

### Phase 2.6: CLI Interface

**Objective**: Implement command-line interface with argument parsing.

**Deliverables**:
- `cli.py` with argparse setup
- Modes: apply, dry-run, validate
- Arguments: --teams-dir, --org, --dry-run, --validate-only
- Exit codes for different failure scenarios
- Help text and usage examples

**Validation**: Can run script with different modes and arguments.

### Phase 2.7: Integration & End-to-End Testing

**Objective**: Integrate all components and test complete workflows.

**Deliverables**:
- Integration tests with sample team configurations
- End-to-end test against test GitHub organization (manual)
- Error handling verification
- Performance testing (50 users, 20 repos)
- Documentation updates

**Validation**: Script successfully processes real team configurations and applies changes to GitHub.

### Phase 2.8: Advanced Features (P3, P4)

**Objective**: Implement validation mode and stale collaborator removal.

**Deliverables**:
- Validation mode (--validate-only flag)
- Repository existence checks
- User existence checks (optional)
- Stale collaborator detection and removal
- Conflict reporting in dry-run mode

**Validation**: Validation mode reports issues without contacting GitHub API. Stale collaborator removal works correctly.

---

## Phase 3: Testing Strategy

### Unit Tests

- **config.py**: YAML parsing, schema validation, error handling
- **github_client.py**: API operations with mocked responses, rate limit handling
- **manager.py**: Conflict resolution, change detection, file processing order
- **audit_logger.py**: Log format, timestamp generation, field validation
- **models.py**: Data class validation, serialization

### Integration Tests

- **End-to-end workflow**: Load configs → validate → apply changes → verify logs
- **Conflict scenarios**: Multiple files with overlapping users/repos
- **Error scenarios**: Invalid YAML, non-existent repos, API failures
- **Dry-run mode**: Verify no changes made to GitHub

### Manual Testing

- **Real GitHub organization**: Test against observability-s with test repositories
- **Performance**: 50 users, 20 repositories, measure execution time
- **Rate limiting**: Trigger rate limit and verify exponential backoff
- **Audit logs**: Verify logs are parseable by standard tools (jq, log aggregators)

---

## Phase 4: Documentation

### User Documentation

- **README.md**: Installation, configuration, usage examples
- **YAML Schema**: Detailed schema documentation with examples
- **Troubleshooting**: Common errors and solutions
- **Security**: Token permissions, best practices

### Developer Documentation

- **Architecture**: Component diagram, data flow
- **API Reference**: Function signatures, parameters, return values
- **Testing**: How to run tests, add new tests
- **Contributing**: Code style, PR process

---

## Phase 5: Deployment & Operations

### Deployment

- **Package Distribution**: PyPI package or GitHub releases
- **Installation**: `pip install github-collab-manager`
- **Configuration**: Environment variables, YAML directory setup

### Operations

- **Scheduling**: Cron job or GitHub Actions workflow for periodic sync
- **Monitoring**: Log aggregation, error alerting
- **Backup**: Version control for YAML configurations
- **Access Reviews**: Periodic review of team configurations

---

## Risk Assessment

### High Risk

- **API Rate Limiting**: Mitigated by exponential backoff and Retry-After header respect
- **Token Permissions**: Mitigated by clear documentation and validation
- **Conflict Resolution**: Mitigated by deterministic alphabetical ordering and dry-run mode

### Medium Risk

- **Large-Scale Operations**: Mitigated by performance testing and batch processing
- **Network Failures**: Mitigated by retry logic and graceful error handling
- **Configuration Errors**: Mitigated by validation mode and schema enforcement

### Low Risk

- **YAML Parsing**: Mitigated by using well-tested PyYAML library
- **Logging Overhead**: Mitigated by efficient JSON serialization

---

## Success Metrics

- ✅ All constitutional principles satisfied
- ✅ All functional requirements (FR-001 to FR-020) addressed
- ✅ All non-functional requirements (NFR-001 to NFR-003) addressed
- ✅ All success criteria (SC-001 to SC-012) achievable
- ✅ All user stories (P1-P4) implementable with clear acceptance scenarios

---

## Next Steps

1. ✅ Implementation plan created
2. **Next**: Run `/bobkit.tasks` to generate actionable task breakdown
3. **Then**: Run `/bobkit.checklist` to create quality validation checklist
4. **Then**: Run `/bobkit.implement` to begin implementation

---

**Plan Version**: 1.0  
**Last Updated**: 2026-03-06