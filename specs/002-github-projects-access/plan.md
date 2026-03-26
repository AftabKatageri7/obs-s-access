# Implementation Plan: GitHub Projects Access Manager

**Feature**: GitHub Projects (v2) Access Management  
**Branch**: `002-github-projects-access`  
**Created**: 2026-03-24  
**Status**: Planning

## Executive Summary

This implementation extends the existing GitHub Collaborator Manager to support managing outside collaborator access to GitHub Projects (v2) using the GraphQL API. The feature adds project access management capabilities while maintaining full backward compatibility with existing repository management functionality.

**Key Deliverables**:
- GraphQL client for GitHub Projects v2 API
- Extended YAML schema supporting project access configuration
- Project access synchronization alongside repository access
- Comprehensive audit logging for project operations
- Dry-run validation for project access changes

## Technical Context

### Technology Stack

- **Language**: Python 3.8+
- **Existing Dependencies**: 
  - `PyGithub` (REST API client for repository operations)
  - `PyYAML` (YAML configuration parsing)
  - `click` (CLI framework)
- **New Dependencies**: 
  - `gql[requests]>=3.0.0` (GraphQL client for Projects v2 API)
  - `requests-toolbelt` (for GraphQL multipart requests if needed)

### Architecture Overview

**Current Architecture** (Repository Management):
```
CLI (cli.py)
  ↓
Manager (manager.py) ← Config Loader (config_loader.py)
  ↓
GitHub REST Client (github_client.py)
  ↓
Audit Logger (audit_logger.py)
```

**Extended Architecture** (Repository + Project Management):
```
CLI (cli.py)
  ↓
Manager (manager.py) ← Config Loader (config_loader.py)
  ↓                      ↓
  ↓                   Models (models.py)
  ↓                      ↓
  ├─→ GitHub REST Client (github_client.py)
  └─→ Projects GraphQL Client (projects_client.py) [NEW]
  ↓
Audit Logger (audit_logger.py)
```

### Integration Points

- **GitHub REST API**: Existing integration for repository collaborator management (unchanged)
- **GitHub GraphQL API**: New integration for Projects v2 operations
- **YAML Configuration**: Extended schema with backward compatibility
- **Audit Logging**: Unified log format for both repository and project operations
- **CLI Interface**: Extended with project-specific flags and reporting

### Key Design Decisions

1. **Separate GraphQL Client**: Create dedicated `projects_client.py` module parallel to `github_client.py` for clear separation of concerns
2. **Schema Extension**: Add optional `projects:` section to existing YAML schema for backward compatibility
3. **Unified Processing**: Process both repository and project access in single execution for operational efficiency
4. **Explicit Permissions**: Follow zero-trust model - no implicit project access based on repository permissions
5. **Project Number Identification**: Use project numbers (from URLs) as stable, human-readable identifiers
6. **Alphabetical Processing**: Process team files alphabetically for deterministic conflict resolution

### External Dependencies

- **GitHub GraphQL API**: `https://api.github.com/graphql`
- **GitHub Token Scopes**: Requires both `repo` and `project` scopes
- **GitHub Projects v2**: Feature must be enabled for the organization
- **Network Connectivity**: Requires outbound HTTPS access to GitHub API

### Constraints & Limitations

- **API Rate Limits**: GraphQL API has cost-based rate limiting (different from REST API)
- **Token Permissions**: Users must update tokens to include `project` scope
- **Projects v2 Only**: Does not support legacy Projects v1
- **Outside Collaborators Only**: Does not manage project access for organization members
- **Single Organization**: Operates on one organization at a time (observability-s)

## Constitution Check

### Principle 1: Security-First ✅

**Alignment**: This feature follows zero-trust security model with explicit permissions only.

**Evidence**:
- FR-001 to FR-004: Project access must be explicitly declared in YAML configuration
- FR-005: Authentication via secure token with explicit `project` scope
- FR-010: Comprehensive audit logging for all project operations
- FR-016: Only manages outside collaborators (explicit access grants)
- No implicit permissions based on repository access or organization membership

**Compliance**: PASS - All project access requires explicit YAML configuration and token authorization. Audit logging captures every operation.

### Principle 2: Principle of Least Privilege ✅

**Alignment**: Access grants provide minimum permissions necessary.

**Evidence**:
- FR-004: Supports granular permission levels (read, write, admin) per project
- FR-013: Users can have different permissions across different projects
- FR-007: Updates permissions when configuration changes (supports permission reduction)
- Extended YAML schema allows fine-grained control per project
- No wildcard or broad access patterns

**Compliance**: PASS - System enforces minimal scope with per-project permission control and supports permission updates/reductions.

### Principle 3: Clear Authorization Model ✅

**Alignment**: Authorization policies are declarative, testable, and documented.

**Evidence**:
- FR-001 to FR-003: Declarative YAML schema defines "what" access is allowed
- Extended YAML format is version-controlled and reviewable
- FR-012: Dry-run mode enables testing without applying changes
- FR-008, FR-009: Validation before execution ensures testability
- Comprehensive documentation in spec.md with examples

**Compliance**: PASS - YAML-based declarative policies with validation, dry-run testing, and full documentation.

### Overall Assessment

**Status**: ✅ PASS - All constitutional principles are satisfied

**Justification**: This feature extends the existing access control system while maintaining all security principles. Project access follows the same zero-trust, least-privilege, declarative model as repository access. The GraphQL integration adds new capabilities without compromising security or clarity.

## Phase 0: Research & Clarification

### Research Tasks

#### R001: GitHub Projects v2 GraphQL API Patterns
**Decision**: Use `gql` library with `requests` transport for GraphQL operations

**Rationale**: 
- `gql` provides type-safe GraphQL queries with validation
- Well-maintained with active community support
- Integrates cleanly with existing `requests`-based architecture
- Supports query composition and fragments for complex operations

**Alternatives Considered**:
- `python-graphql-client`: Simpler but less type safety
- Direct `requests` with GraphQL: More manual error handling required
- `sgqlc`: Code generation overhead not needed for this use case

**Implementation Notes**:
- Use `gql.transport.requests.RequestsHTTPTransport` for consistency
- Implement retry logic with exponential backoff for rate limits
- Cache organization/repository project lists to minimize API calls

#### R002: GraphQL Query Structure for Projects v2
**Decision**: Use separate queries for organization and repository projects

**Rationale**:
- Organization projects: Query via `organization.projectsV2`
- Repository projects: Query via `repository.projectsV2`
- Different node types require different query structures
- Enables parallel processing of org vs repo projects

**Query Patterns**:
```graphql
# List organization projects
query($org: String!) {
  organization(login: $org) {
    projectsV2(first: 100) {
      nodes {
        id
        number
        title
      }
    }
  }
}

# Add project collaborator
mutation($projectId: ID!, $userId: ID!, $role: ProjectV2Roles!) {
  updateProjectV2Collaborators(
    input: {
      projectId: $projectId
      collaborators: [{userId: $userId, role: $role}]
    }
  ) {
    collaborators {
      userId
      role
    }
  }
}
```

#### R003: Error Handling for GraphQL API
**Decision**: Implement structured error handling with specific error types

**Rationale**:
- GraphQL returns errors in `errors` array alongside data
- Need to distinguish between network errors, auth errors, and business logic errors
- Rate limit errors require retry with backoff
- Invalid project numbers should skip and continue processing

**Error Categories**:
1. **Network Errors**: Retry with exponential backoff
2. **Authentication Errors**: Fail fast with clear message about token scopes
3. **Not Found Errors**: Log warning and skip (invalid project number)
4. **Permission Errors**: Log error and skip (token lacks access)
5. **Rate Limit Errors**: Implement retry with backoff (respect `Retry-After` header)

#### R004: YAML Schema Extension Strategy
**Decision**: Add optional `projects:` section at same level as `roles:`

**Rationale**:
- Maintains backward compatibility (existing files work unchanged)
- Logical grouping: `roles:` for repositories, `projects:` for projects
- Clear separation of concerns in configuration
- Easy to validate and parse independently

**Schema Validation**:
- Use `pydantic` models for type-safe validation
- Validate project numbers are integers
- Validate permission levels against allowed values
- Validate repository names exist before processing repo projects

#### R005: Audit Logging Format Consistency
**Decision**: Extend existing structured log format with project-specific fields

**Rationale**:
- Maintain compatibility with existing log analysis tools
- Add `resource_type` field to distinguish repository vs project operations
- Use same timestamp, action, user, result structure

**Log Format**:
```json
{
  "timestamp": "2026-03-24T19:00:00Z",
  "resource_type": "project",  // NEW: "repository" or "project"
  "action": "add_collaborator",
  "project_type": "organization",  // NEW: "organization" or "repository"
  "project_number": 1,  // NEW
  "repository": null,  // NEW: for repo projects
  "username": "alice-dev",
  "permission": "write",
  "result": "success",
  "error": null
}
```

### Clarifications Resolved

All technical unknowns have been resolved through research. No blocking clarifications remain.

## Phase 1: Design Artifacts

### Data Model

See [`data-model.md`](./data-model.md) for complete entity definitions and relationships.

**Key Entities**:
- `ProjectConfig`: Container for project access configuration
- `OrganizationProject`: Organization-level project with number and permissions
- `RepositoryProject`: Repository-level project with repo name, number, and permissions
- `ProjectAccessGrant`: Combination of user, project identifier, and permission level
- `ProjectPermission`: Enum of read, write, admin

### API Contracts

See [`contracts/`](./contracts/) directory for GraphQL schema definitions.

**Key Operations**:
- `listOrganizationProjects.graphql`: Query organization projects
- `listRepositoryProjects.graphql`: Query repository projects
- `getProjectCollaborators.graphql`: List current project collaborators
- `addProjectCollaborator.graphql`: Grant project access
- `updateProjectCollaborator.graphql`: Update project permission
- `removeProjectCollaborator.graphql`: Revoke project access

### Quickstart Guide

See [`quickstart.md`](./quickstart.md) for setup and usage instructions.

## Phase 2: Implementation Structure

### File Structure

```
src/github_collab_manager/
├── __init__.py                 # Package initialization
├── cli.py                      # CLI interface (EXTEND)
├── manager.py                  # Orchestration logic (EXTEND)
├── config_loader.py            # YAML parsing (EXTEND)
├── models.py                   # Data models (EXTEND)
├── github_client.py            # REST API client (UNCHANGED)
├── projects_client.py          # GraphQL API client (NEW)
└── audit_logger.py             # Logging (EXTEND)

specs/002-github-projects-access/
├── spec.md                     # Feature specification
├── plan.md                     # This file
├── tasks.md                    # Task breakdown (generated next)
├── data-model.md               # Entity definitions (NEW)
├── quickstart.md               # Setup guide (NEW)
├── research.md                 # Research findings (NEW)
└── contracts/                  # GraphQL schemas (NEW)
    ├── listOrganizationProjects.graphql
    ├── listRepositoryProjects.graphql
    ├── getProjectCollaborators.graphql
    ├── addProjectCollaborator.graphql
    ├── updateProjectCollaborator.graphql
    └── removeProjectCollaborator.graphql

tests/
├── test_projects_client.py     # GraphQL client tests (NEW)
├── test_config_loader.py       # Extended schema tests (EXTEND)
├── test_manager.py             # Project operations tests (EXTEND)
└── fixtures/
    └── sample_teams/
        └── team-with-projects.yaml  # Test fixture (NEW)
```

### Module Responsibilities

#### `projects_client.py` (NEW)
- Initialize GraphQL client with GitHub token
- Execute GraphQL queries and mutations for Projects v2
- Handle GraphQL-specific errors and rate limits
- Validate project existence before operations
- Map GraphQL responses to internal models

#### `models.py` (EXTEND)
- Add `ProjectConfig` dataclass
- Add `OrganizationProject` dataclass
- Add `RepositoryProject` dataclass
- Add `ProjectAccessGrant` dataclass
- Add `ProjectPermission` enum

#### `config_loader.py` (EXTEND)
- Parse `projects:` section from YAML
- Validate project configuration schema
- Support backward compatibility (missing projects section)
- Validate permission levels and project numbers

#### `manager.py` (EXTEND)
- Orchestrate both repository and project operations
- Process project access grants after repository access
- Handle dry-run mode for project operations
- Collect and report project-related errors
- Generate summary of project operations

#### `cli.py` (EXTEND)
- Add project-specific output formatting
- Display project operation results
- Show project validation errors
- Include project stats in summary

#### `audit_logger.py` (EXTEND)
- Add `resource_type` field to log entries
- Add project-specific fields (project_type, project_number, repository)
- Maintain backward compatibility with existing log format

### Dependencies Update

**requirements.txt**:
```
PyGithub>=2.1.1
PyYAML>=6.0
click>=8.1.0
gql[requests]>=3.5.0  # NEW
requests>=2.31.0
pydantic>=2.0.0  # NEW (for schema validation)
```

**requirements-dev.txt**:
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
responses>=0.23.0
vcrpy>=5.1.0  # NEW (for GraphQL response recording)
```

## Phase 3: Implementation Phases

Implementation will be organized by user story priority (P1 → P4), with each story independently testable.

### Phase 3: User Story 1 - Configuration Schema (P1)
**Goal**: Extend YAML schema to support project access configuration

**Components**:
- Extended `models.py` with project entities
- Extended `config_loader.py` with project parsing
- Schema validation for project configuration
- Backward compatibility tests

**Deliverables**:
- Project data models
- YAML parsing for projects section
- Validation logic
- Unit tests for schema parsing

### Phase 4: User Story 2 - Project Access Synchronization (P2)
**Goal**: Apply project access configuration to GitHub

**Components**:
- `projects_client.py` GraphQL client
- Extended `manager.py` with project operations
- Extended `audit_logger.py` with project logging
- Integration with existing workflow

**Deliverables**:
- GraphQL client implementation
- Project access grant/update logic
- Audit logging for projects
- Integration tests

### Phase 5: User Story 3 - Dry-Run Validation (P3)
**Goal**: Validate project configuration before applying

**Components**:
- Dry-run mode for project operations
- Project existence validation
- Permission change reporting
- Extended CLI output

**Deliverables**:
- Dry-run implementation
- Validation logic
- Reporting functionality
- CLI tests

### Phase 6: User Story 4 - Stale Collaborator Cleanup (P4)
**Goal**: Remove project collaborators not in configuration

**Components**:
- Project collaborator listing
- Stale collaborator detection
- Cleanup mode implementation
- Safety checks (org members)

**Deliverables**:
- Collaborator detection logic
- Cleanup implementation
- Safety validations
- End-to-end tests

### Phase 7: Polish & Cross-Cutting Concerns
**Goal**: Finalize documentation, error handling, and edge cases

**Components**:
- Comprehensive error messages
- Edge case handling
- Performance optimization
- Documentation updates

**Deliverables**:
- Updated README
- API documentation
- Performance tests
- Edge case tests

## Testing Strategy

### Unit Tests
- Project data model validation
- YAML schema parsing with projects section
- GraphQL query construction
- Error handling for GraphQL responses
- Permission level validation

### Integration Tests
- GraphQL client with mocked responses
- Project access grant workflow
- Project access update workflow
- Dry-run mode validation
- Audit logging output

### End-to-End Tests
- Full workflow with test organization
- Repository + project access in single run
- Backward compatibility with existing configs
- Error recovery and retry logic
- Performance with multiple projects

### Test Fixtures
- Sample YAML files with project configurations
- Recorded GraphQL responses (using VCR.py)
- Mock GitHub organization with test projects
- Various permission scenarios

## Deployment Considerations

### Prerequisites
- GitHub token with `project` scope added
- Python 3.8+ environment
- Network access to GitHub GraphQL API
- Organization with Projects v2 enabled

### Migration Path
1. Update dependencies: `pip install -r requirements.txt`
2. Update GitHub token to include `project` scope
3. Existing YAML files work unchanged (backward compatible)
4. Add `projects:` section to team files as needed
5. Test with dry-run mode before applying changes

### Rollback Plan
- Remove `projects:` sections from YAML files
- Revert to previous version if needed
- Repository management continues to work independently
- Manual project access cleanup if necessary

## Risk Assessment

### Technical Risks

**Risk**: GraphQL API rate limits differ from REST API
- **Mitigation**: Implement cost-aware retry logic with exponential backoff
- **Impact**: Medium - Could slow down execution but won't cause failures

**Risk**: Token lacks `project` scope
- **Mitigation**: Detect missing scope and provide clear error message
- **Impact**: Low - Easy to fix by updating token

**Risk**: Project numbers change or projects deleted
- **Mitigation**: Validate project existence before operations, skip invalid projects
- **Impact**: Low - Configuration error, not system failure

### Operational Risks

**Risk**: Conflicting project permissions across team files
- **Mitigation**: Alphabetical processing order with clear documentation
- **Impact**: Low - Deterministic behavior, documented in spec

**Risk**: Accidental removal of legitimate project collaborators
- **Mitigation**: Dry-run mode, explicit cleanup flag, org member protection
- **Impact**: Medium - Requires careful configuration review

## Success Metrics

- ✅ All 4 user stories implemented and tested
- ✅ 100% backward compatibility with existing configurations
- ✅ GraphQL operations complete within 5 seconds per project
- ✅ Comprehensive audit logging for all project operations
- ✅ Zero breaking changes to existing repository management
- ✅ Documentation complete with examples and migration guide

## Next Steps

1. ✅ Implementation plan created successfully
2. **Next**: Run `/bobkit.tasks` to generate actionable task breakdown
3. Then: Run `/bobkit.implement` to begin development
4. Finally: Run `/bobkit.check` for validation before PR

---

**Plan Version**: 1.0  
**Last Updated**: 2026-03-24  
**Status**: Ready for task generation