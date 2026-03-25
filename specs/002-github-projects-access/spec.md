# Feature Specification: GitHub Projects Access Manager

**Feature Branch**: `002-github-projects-access`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User request: "Add GitHub Projects (v2) access management capability to manage collaborator permissions on organization and repository project boards using GraphQL API"

## Feature Overview

This feature extends the existing GitHub Collaborator Manager to support managing outside collaborator access to GitHub Projects (v2). GitHub Projects are organization-level or repository-level project boards with their own permission model (admin, write, read) that is separate from repository permissions. Since GitHub Projects v2 requires the GraphQL API (unlike the REST API used for repository collaborators), this feature adds GraphQL client capabilities while maintaining backward compatibility with existing repository management functionality.

## Clarifications

### Session 2026-03-24

- Q: Should project access management be integrated into existing team YAML files or use separate configuration files? → A: Integrated into existing team YAML files with a new `projects:` section alongside the existing `roles:` section for unified team access management
- Q: How should projects be identified in YAML configuration - by project number, project ID, or project title? → A: By project number (visible in project URL) as it's human-readable and stable, with validation against organization projects
- Q: Should the tool support both organization-level and repository-level projects? → A: Yes, support both with clear distinction in YAML configuration (org_projects vs repo_projects)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Project Access in Team Configuration (Priority: P1)

An organization administrator needs to grant outside collaborators access to GitHub Projects (project boards) in addition to repository access. They extend their existing team YAML files to include a `projects:` section that specifies which organization-level and repository-level projects team members should access and with what permissions (admin, write, read).

**Why this priority**: This establishes the configuration format for project access management, extending the existing YAML schema. Without this foundation, no project access can be managed. This is the data model that all other project functionality depends on.

**Independent Test**: Can be fully tested by creating YAML files with project definitions and validating that the extended schema is correct and parseable, without needing to interact with GitHub GraphQL API.

**Acceptance Scenarios**:

1. **Given** an existing team YAML file with repository roles, **When** administrator adds a `projects:` section with organization projects, **Then** the file follows the extended schema and can be parsed successfully
2. **Given** a team configuration with projects section, **When** the file is validated, **Then** all required fields (project numbers, permission levels) are present and properly formatted
3. **Given** a team definition with both repository roles and project permissions, **When** the configuration is reviewed, **Then** users can have different permission levels for repositories and projects independently

---

### User Story 2 - Apply Project Access Configuration to GitHub (Priority: P2)

An organization administrator runs the script to synchronize project access defined in YAML team configurations with actual GitHub Projects permissions. The script uses GitHub's GraphQL API to add or update outside collaborators' access to specified projects with their assigned permission levels (admin, write, read). All project access operations are logged to stdout in structured format alongside repository operations.

**Why this priority**: This is the core operational functionality that delivers value - automating project access management. It builds directly on P1's configuration format and integrates with existing repository management workflow.

**Independent Test**: Can be tested by running the script against a test organization with test projects, verifying that collaborators are granted correct project permissions, and confirming through GitHub's UI or GraphQL API that the changes were applied correctly.

**Acceptance Scenarios**:

1. **Given** a valid YAML team configuration with projects section and GitHub API credentials with project scope, **When** the script is executed, **Then** all users in the team are granted access to their assigned projects with the correct permission levels
2. **Given** a user already has project access with a different permission level, **When** the script runs with updated permission in YAML, **Then** the user's project permission is updated to match the YAML configuration
3. **Given** a team configuration with both repository roles and project permissions, **When** the script processes the file, **Then** both repository and project access are synchronized without conflicts
4. **Given** a YAML file specifying a non-existent project number, **When** the script processes the configuration, **Then** an error is reported for that project and processing continues for other valid projects
5. **Given** project access changes are made, **When** the script executes, **Then** structured log entries are written to stdout containing timestamp, action type, username, project identifier, permission level, and operation result

---

### User Story 3 - Validate Project Configuration Before Applying (Priority: P3)

An organization administrator wants to verify their project access configurations are correct before applying changes to GitHub. They run the script in dry-run mode which validates project numbers exist, checks current permissions, and reports what changes would be made to project access without actually making them.

**Why this priority**: This is a safety feature that prevents mistakes when managing project access. While valuable, the system can function without it - administrators can manually review configurations and check GitHub after applying changes.

**Independent Test**: Can be tested by running the script with --dry-run flag against various YAML configurations with project definitions and verifying that it reports planned project access changes correctly without making actual changes to GitHub.

**Acceptance Scenarios**:

1. **Given** a YAML configuration with invalid project numbers, **When** validation is run, **Then** the script reports which project numbers don't exist in the organization
2. **Given** a valid YAML configuration with projects, **When** dry-run mode is executed, **Then** the script reports what project access changes would be made (users to add, permissions to update) without actually modifying GitHub
3. **Given** a configuration with both repository and project access, **When** dry-run mode is executed, **Then** the script reports planned changes for both repositories and projects in a unified output

---

### User Story 4 - Remove Stale Project Collaborators (Priority: P4)

An organization administrator wants to ensure that collaborators who are no longer in any team configuration are removed from projects. The script can optionally detect collaborators who have project access but are not defined in any current YAML team file and either report them or remove them automatically.

**Why this priority**: This is an advanced cleanup feature for project access hygiene. However, it's not essential for core functionality and requires careful implementation to avoid accidentally removing legitimate project collaborators. Many organizations may prefer to handle project access removals manually.

**Independent Test**: Can be tested by setting up projects with existing collaborators, running the script with team configurations that don't include some of those collaborators, and verifying that the script correctly identifies or removes the stale project collaborators based on the chosen mode.

**Acceptance Scenarios**:

1. **Given** a project with collaborators not in any team YAML file, **When** the script runs in report mode, **Then** the script lists all project collaborators who would be removed without actually removing them
2. **Given** a project with collaborators not in any team YAML file, **When** the script runs in cleanup mode, **Then** those collaborators are removed from the project
3. **Given** a collaborator who is an organization member (not outside collaborator), **When** cleanup runs, **Then** the organization member's project access is not removed (only outside collaborators are managed)

---

### Edge Cases

- How does the script handle GraphQL API errors or rate limits when querying or updating project access?
- What happens when a project number in the YAML file doesn't exist or has been deleted?
- How does the system handle projects that the API token doesn't have permission to modify?
- What happens when a user doesn't have the required permissions to be added to a project?
- How does the script handle organization-level projects vs repository-level projects with the same project number?
- What happens when a repository-level project is specified but the repository doesn't exist?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extend existing YAML schema to support a `projects:` section alongside the existing `roles:` section
- **FR-002**: System MUST support organization-level projects specified with project numbers in an `org_projects:` subsection
- **FR-003**: System MUST support repository-level projects specified with repository name and project number in a `repo_projects:` subsection
- **FR-004**: System MUST support GitHub Projects v2 permission levels: read, write, and admin
- **FR-005**: System MUST authenticate to GitHub GraphQL API using the same Personal Access Token from GITHUB_TOKEN environment variable with `project` scope
- **FR-006**: System MUST add users as project collaborators if they don't already have access to the specified project
- **FR-007**: System MUST update existing project collaborator permissions when the YAML configuration specifies a different permission level than currently assigned
- **FR-008**: System MUST validate that specified project numbers exist in the organization before attempting to grant access
- **FR-009**: System MUST validate that specified repositories exist before attempting to access their repository-level projects
- **FR-010**: System MUST output structured log entries for project operations to stdout containing timestamp, action type (add/update/remove), username, project identifier, permission level, and operation result
- **FR-011**: System MUST handle GraphQL API errors gracefully and report which project operations failed
- **FR-012**: System MUST support dry-run mode for project access changes, reporting planned changes without executing them
- **FR-013**: System MUST allow a single user to have different permission levels across different projects within the same team configuration
- **FR-014**: System MUST process both repository roles and project permissions in a single execution
- **FR-015**: System MUST maintain backward compatibility with existing team YAML files that don't include a projects section
- **FR-016**: System MUST skip organization members and only manage outside collaborators for project access
- **FR-017**: System MUST implement retry logic with exponential backoff for GraphQL API rate limits
- **FR-018**: System MUST process team configuration files in alphabetical order for deterministic conflict resolution when a user-project combination appears in multiple files
- **FR-019**: System MUST report an error and skip processing for projects that don't exist, while continuing to process other valid projects
- **FR-020**: System MUST provide a summary at the end of execution listing all project-related errors encountered

### Non-Functional Requirements

- **NFR-001**: Project access audit logs MUST follow the same structured format as repository access logs for unified log analysis
- **NFR-002**: GraphQL API operations MUST complete within reasonable timeframes (under 5 seconds per project access operation under normal conditions)
- **NFR-003**: System MUST handle at least 50 project access grants across 10 projects without performance degradation

### Key Entities

- **Project Configuration**: Extension to team configuration that specifies project access. Contains organization-level projects and repository-level projects with their permission levels.
- **Organization Project**: A GitHub Project (v2) at the organization level, identified by project number. Accessible to all organization members and outside collaborators with appropriate permissions.
- **Repository Project**: A GitHub Project (v2) associated with a specific repository, identified by repository name and project number. Access is independent of repository permissions.
- **Project Permission**: The permission level granted to a user for a specific project. Must be one of: read, write, or admin (GitHub Projects v2 permission model).
- **Project Access Grant**: The combination of a user, project identifier, and permission level that represents a specific project permission assignment.
- **GraphQL Client**: New component that handles communication with GitHub's GraphQL API for Projects v2 operations, separate from the existing REST API client for repository operations.

## Extended YAML Configuration Format

### Schema Structure

The existing team configuration schema is extended with an optional `projects:` section:

```yaml
team_name: <string>           # Identifier for this team (for logging/reporting)
users:                        # List of GitHub usernames
  - <username1>
  - <username2>
roles:                        # Role-based repository groupings (existing)
  <role-name>:               # Role: read, triage, write, maintain, or admin
    - <repo-name-1>
    - <repo-name-2>
projects:                     # Project access configuration (NEW)
  org_projects:              # Organization-level projects
    <permission-level>:      # Permission: read, write, or admin
      - <project-number-1>
      - <project-number-2>
  repo_projects:             # Repository-level projects
    <permission-level>:      # Permission: read, write, or admin
      - repo: <repo-name>
        project: <project-number>
      - repo: <repo-name>
        project: <project-number>
```

**Valid Project Permissions**: `read`, `write`, `admin` (GitHub Projects v2 permission levels)

**Project Number**: The numeric identifier visible in the project URL (e.g., `https://github.com/orgs/observability-s/projects/1` → project number is `1`)

### Example 1: Team with Repository and Organization Project Access

File: `teams/backend-team.yaml`

```yaml
team_name: Backend Engineering Team
users:
  - alice-dev
  - bob-engineer
  - charlie-backend
roles:
  write:
    - observability-api
    - metrics-collector
  read:
    - shared-utils
projects:
  org_projects:
    write:
      - 1    # Main development board
      - 5    # Backend sprint planning
    read:
      - 3    # Company-wide roadmap
```

**Explanation**: This configuration grants three backend engineers write access to two repositories, read access to shared utilities, write access to two organization-level projects (development board and sprint planning), and read access to the company roadmap project.

### Example 2: Team with Repository-Level Project Access

File: `teams/frontend-team.yaml`

```yaml
team_name: Frontend Team
users:
  - diana-ui
  - evan-frontend
roles:
  write:
    - dashboard-app
  read:
    - shared-utils
projects:
  org_projects:
    read:
      - 1    # Main development board
  repo_projects:
    write:
      - repo: dashboard-app
        project: 2    # Dashboard feature tracking
    read:
      - repo: shared-utils
        project: 1    # Shared components roadmap
```

**Explanation**: Frontend team gets write access to their main repository, read access to shared utilities, read access to the organization's main development board, write access to the dashboard app's feature tracking project, and read access to the shared utilities roadmap project.

### Example 3: Team with Only Project Access (No Repository Access)

File: `teams/project-managers.yaml`

```yaml
team_name: Project Management Team
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

**Explanation**: Project managers don't need repository access but need admin access to sprint planning boards and write access to the roadmap. The empty `roles: {}` section is valid and indicates no repository permissions are granted.

### Example 4: Backward Compatible - Existing Configuration Without Projects

File: `teams/contractors.yaml`

```yaml
team_name: External Contractors
users:
  - contractor-jane
roles:
  write:
    - public-docs
```

**Explanation**: Existing team configurations without a `projects:` section remain valid and continue to work. The script processes repository access as before and skips project access management for this team.

### Example 5: Mixed Permission Levels Across Projects

File: `teams/devops-team.yaml`

```yaml
team_name: DevOps Team
users:
  - frank-ops
  - grace-sre
roles:
  admin:
    - observability-api
    - metrics-collector
  maintain:
    - infrastructure-config
projects:
  org_projects:
    admin:
      - 1    # Main development board (full control)
    write:
      - 5    # Backend sprint planning (can edit)
    read:
      - 3    # Company-wide roadmap (view only)
  repo_projects:
    admin:
      - repo: infrastructure-config
        project: 1    # Infrastructure planning board
```

**Explanation**: DevOps team has admin access to backend repositories and varying levels of project access - admin for development board and infrastructure planning, write for sprint planning, and read for roadmap. This demonstrates fine-grained permission control across different projects.

### Configuration Processing Rules

1. **Backward Compatibility**: Team files without `projects:` section are processed normally for repository access only
2. **Optional Sections**: Both `org_projects:` and `repo_projects:` are optional within the `projects:` section
3. **Empty Roles**: A team can have `roles: {}` (no repository access) and only project access
4. **Processing Order**: Files are processed in alphabetical order; project permissions from later files override earlier ones for the same user-project combination
5. **Validation**: Project numbers are validated against organization projects before attempting to grant access
6. **Error Handling**: Invalid project numbers are reported but don't stop processing of other valid projects
7. **Additive Access**: If a user appears in multiple files with permissions for different projects, all access grants are applied (access is cumulative across files)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrator can extend existing team YAML files with project access configuration in under 3 minutes
- **SC-002**: Script successfully processes and applies project access for at least 50 users across 10 projects without errors
- **SC-003**: Time to grant project access to a new outside collaborator across 5 projects is reduced from 5+ minutes (manual) to under 30 seconds (automated)
- **SC-004**: 100% of project access additions and permission updates are logged with timestamp, user, project identifier, and permission level for audit compliance
- **SC-005**: Dry-run mode accurately reports all planned project access changes with zero false positives or false negatives
- **SC-006**: Script completes execution for a typical team configuration (10 users, 3 repositories, 5 projects) in under 3 minutes
- **SC-007**: Configuration errors (invalid project numbers, non-existent repositories for repo projects) are detected and reported before any GraphQL API calls are made
- **SC-008**: Existing team configurations without project sections continue to work without modification (100% backward compatibility)
- **SC-009**: Script automatically recovers from GraphQL API rate limit errors and completes successfully without manual intervention
- **SC-010**: When conflicting project permission assignments exist across team files, the final applied permission is predictable and matches the last processed file in alphabetical order
- **SC-011**: Administrator can manage both repository and project access for a team in a single unified YAML file
- **SC-012**: Project access audit logs can be parsed by the same log analysis tools used for repository access logs without custom parsing logic

### Assumptions

- GitHub API token has the `project` scope in addition to repository management permissions
- GitHub Projects v2 API is available and stable (not the legacy Projects v1)
- Organization-level projects are accessible via the organization's GraphQL API endpoint
- Repository-level projects are accessible when the token has access to the parent repository
- Project numbers are stable identifiers that don't change when projects are renamed
- Outside collaborators can be granted project access independently of repository access
- The same user can have different permission levels for different projects
- GraphQL API rate limits are similar to REST API rate limits and can be handled with the same retry logic
- Project access changes take effect immediately (no propagation delay)
- The script operates on a single organization (observability-s) for both repository and project access
- Project numbers in YAML files refer to projects within the configured organization
- Repository-level project numbers are unique within each repository but may overlap across different repositories

### Out of Scope

- Managing GitHub Projects v1 (legacy project boards) - only Projects v2 is supported
- Creating or deleting projects
- Managing project settings, fields, or workflows
- Managing project items (issues, pull requests, draft items)
- Managing project views or automation rules
- Inviting users to projects (only managing permissions for existing collaborators)
- Managing project access for organization members (only outside collaborators)
- Managing team-level project access (only individual collaborator access)
- Real-time synchronization of project access changes
- Webhook-based project access updates
- Managing access to private projects that the API token cannot access
- Automatic project number discovery or project title-based identification
- Cross-organization project access management
- Managing project visibility settings (public/private)
- Handling project transfers between organizations or repositories

## Technical Considerations

### GraphQL API Integration

- **New Dependency**: Add GraphQL client library (e.g., `gql[requests]` or `python-graphql-client`)
- **Authentication**: Reuse existing GITHUB_TOKEN with additional `project` scope requirement
- **Query Structure**: Use GraphQL queries for:
  - Listing organization projects
  - Listing repository projects
  - Checking current project collaborator permissions
  - Adding/updating project collaborators
  - Removing project collaborators
- **Error Handling**: GraphQL errors have different structure than REST API errors; need appropriate parsing
- **Rate Limiting**: GraphQL has different rate limit model (cost-based); implement appropriate retry logic

### Architecture Changes

- **New Module**: `projects_client.py` - GraphQL client for Projects v2 operations (parallel to `github_client.py`)
- **Extended Models**: Add `ProjectConfig`, `ProjectAccessGrant` to `models.py`
- **Config Loader Extension**: Update `config_loader.py` to parse `projects:` section
- **Manager Integration**: Update `manager.py` to orchestrate both repository and project access operations
- **CLI Extension**: Update `cli.py` to support project-related flags and reporting

### Backward Compatibility

- **Schema Extension**: New `projects:` section is optional; existing files work unchanged
- **Graceful Degradation**: If GraphQL client fails to initialize, repository management continues to work
- **Token Scope**: Script detects if token lacks `project` scope and skips project operations with warning
- **Logging**: Project operations use same log format as repository operations for unified analysis

## Dependencies

### New Python Packages

- `gql[requests]>=3.0.0` - GraphQL client library
- OR `python-graphql-client>=0.4.3` - Alternative GraphQL client

### Updated Token Permissions

GitHub Personal Access Token must have:
- Existing: `repo` scope (for repository collaborator management)
- **New**: `project` scope (for Projects v2 access management)

### API Endpoints

- **GraphQL API**: `https://api.github.com/graphql` (for Projects v2 operations)
- **REST API**: `https://api.github.com` (existing, for repository operations)