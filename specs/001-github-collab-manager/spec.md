# Feature Specification: GitHub Collaborator Manager

**Feature Branch**: `001-github-collab-manager`  
**Created**: 2026-03-06  
**Status**: Draft  
**Input**: User description: "Create a Python script for managing GitHub repository collaborators within the observability-s organization using YAML-based team definitions, where each team configuration file specifies users and their repository access levels across multiple repositories, with support for assigning different roles per repository since GitHub Teams cannot be used for outside collaborators, implementing functionality to read team definitions from YAML files that contain team names, user lists, and nested role-to-repository mappings allowing a single team to grant users write access to certain repositories and different access levels to other repositories, with the script handling authentication to the GitHub API, parsing the YAML team configurations, and programmatically adding or updating outside collaborators with their specified roles across all repositories defined in each team's configuration"

## Clarifications

### Session 2026-03-06

- Q: How should the script authenticate to GitHub API? → A: Personal Access Token (PAT) from environment variable (e.g., GITHUB_TOKEN)
- Q: How should the script handle GitHub API rate limits when processing many repositories and users? → A: Implement exponential backoff with automatic retry (respect Retry-After header)
- Q: What should happen when a user is specified in multiple team files with conflicting roles for the same repository? → A: Last processed file wins (alphabetical filename order)
- Q: What should happen when a YAML file specifies a repository that doesn't exist in the organization? → A: Report error and skip that repository, continue processing other repositories
- Q: How should audit logging be implemented for tracking collaborator changes? → A: Structured logging to stdout with timestamp, action, user, repository, role, and result

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Team Access Configuration (Priority: P1)

An organization administrator needs to define which outside collaborators should have access to which repositories and with what permissions. They create a YAML file that specifies a team name, lists the GitHub usernames of team members, and maps different access levels (read, write, maintain, admin) to specific repositories.

**Why this priority**: This is the foundation of the entire system. Without the ability to define team configurations, no access management can occur. This represents the core data model and configuration format that all other functionality depends on.

**Independent Test**: Can be fully tested by creating a YAML file with team definitions and validating that the file structure is correct and parseable, without needing to interact with GitHub API.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** administrator creates a YAML file with team name, user list, and repository-role mappings, **Then** the file follows the expected schema and can be parsed successfully
2. **Given** a YAML team definition file, **When** the file is validated, **Then** all required fields (team name, users, repositories with roles) are present and properly formatted
3. **Given** a team definition with multiple repositories, **When** the configuration is reviewed, **Then** each repository can have a different role assigned (e.g., write access to repo-a, read access to repo-b)

---

### User Story 2 - Apply Team Configuration to GitHub (Priority: P2)

An organization administrator runs the script to synchronize the YAML team definitions with actual GitHub repository collaborator settings. The script authenticates with GitHub using a Personal Access Token from the GITHUB_TOKEN environment variable, reads the team configuration files, and adds or updates outside collaborators with their specified roles across all defined repositories. All actions are logged to stdout in structured format with timestamps.

**Why this priority**: This is the primary operational functionality that delivers the core value - automating the tedious manual process of adding collaborators to multiple repositories. It builds directly on P1's configuration format.

**Independent Test**: Can be tested by running the script against a test organization with test repositories, verifying that collaborators are added with correct permissions, and confirming through GitHub's UI or API that the changes were applied correctly.

**Acceptance Scenarios**:

1. **Given** a valid YAML team configuration and GitHub API credentials, **When** the script is executed, **Then** all users in the team are added as outside collaborators to their assigned repositories with the correct roles
2. **Given** a user already exists as a collaborator with a different role, **When** the script runs with updated role in YAML, **Then** the user's role is updated to match the YAML configuration
3. **Given** multiple team configuration files in a directory, **When** the script processes all files, **Then** all teams are synchronized without conflicts or errors
4. **Given** invalid GitHub credentials, **When** the script attempts to authenticate, **Then** a clear error message is displayed and the script exits gracefully
5. **Given** a user specified in multiple team files with different roles for the same repository, **When** the script processes files in alphabetical order, **Then** the role from the last processed file is applied
6. **Given** a YAML file specifying a non-existent repository, **When** the script processes the configuration, **Then** an error is reported for that repository and processing continues for other valid repositories
7. **Given** collaborator changes are made, **When** the script executes, **Then** structured log entries are written to stdout containing timestamp, action type, username, repository, role, and operation result

---

### User Story 3 - Validate Configuration Before Applying (Priority: P3)

An organization administrator wants to verify their YAML team configurations are correct before applying changes to GitHub. They run the script in a dry-run or validation mode that checks the configuration files for errors, validates that specified users and repositories exist, and reports what changes would be made without actually making them.

**Why this priority**: This is a safety and usability feature that prevents mistakes and provides confidence before making changes. While valuable, the system can function without it - administrators can manually review YAML files and check GitHub after applying changes.

**Independent Test**: Can be tested by running the script with a --dry-run flag against various YAML configurations (valid, invalid, with non-existent users/repos) and verifying that it reports issues correctly without making any actual changes to GitHub.

**Acceptance Scenarios**:

1. **Given** a YAML configuration with syntax errors, **When** validation is run, **Then** specific syntax errors are reported with line numbers and the script exits without contacting GitHub
2. **Given** a valid YAML configuration, **When** dry-run mode is executed, **Then** the script reports what changes would be made (users to add, roles to update) without actually modifying GitHub
3. **Given** a configuration referencing non-existent repositories, **When** validation checks GitHub, **Then** the script reports which repositories don't exist in the organization
4. **Given** conflicting role assignments across multiple team files, **When** dry-run mode is executed, **Then** the script reports which role will be applied based on alphabetical file processing order

---

### User Story 4 - Remove Stale Collaborators (Priority: P4)

An organization administrator wants to ensure that collaborators who are no longer in any team configuration are removed from repositories. The script can optionally detect collaborators who exist in GitHub but are not defined in any current YAML team file and either report them or remove them automatically.

**Why this priority**: This is an advanced cleanup feature that helps maintain security hygiene. However, it's not essential for the core functionality and requires careful implementation to avoid accidentally removing legitimate collaborators. Many organizations may prefer to handle removals manually.

**Independent Test**: Can be tested by setting up repositories with existing collaborators, running the script with team configurations that don't include some of those collaborators, and verifying that the script correctly identifies or removes the stale collaborators based on the chosen mode.

**Acceptance Scenarios**:

1. **Given** a repository with collaborators not in any team YAML file, **When** the script runs in report mode, **Then** the script lists all collaborators who would be removed without actually removing them
2. **Given** a repository with collaborators not in any team YAML file, **When** the script runs in cleanup mode, **Then** those collaborators are removed from the repository
3. **Given** a collaborator who is an organization member (not outside collaborator), **When** cleanup runs, **Then** the organization member is not removed (only outside collaborators are managed)

---

### Edge Cases

- How does the script handle network failures or GitHub API timeouts during execution?
- What happens when a GitHub username in the YAML file doesn't exist or has been deleted?
- How does the system handle repositories that the API token doesn't have permission to modify?
- What happens when a YAML file is malformed or contains invalid role names?
- How does the script handle very large team files (hundreds of users or repositories)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read team configuration from YAML files in a specified directory
- **FR-002**: System MUST parse YAML files containing team name, list of GitHub usernames, and nested mappings of repository names to access roles
- **FR-003**: System MUST support standard GitHub repository roles: read, triage, write, maintain, and admin
- **FR-004**: System MUST authenticate to GitHub API using a Personal Access Token read from the GITHUB_TOKEN environment variable
- **FR-005**: System MUST add users as outside collaborators to repositories if they don't already have access
- **FR-006**: System MUST update existing collaborator roles when the YAML configuration specifies a different role than currently assigned
- **FR-007**: System MUST handle multiple team configuration files in a single execution
- **FR-008**: System MUST validate YAML syntax and structure before attempting to contact GitHub API
- **FR-009**: System MUST provide clear error messages when YAML files are malformed or missing required fields
- **FR-010**: System MUST output structured log entries to stdout containing timestamp, action type (add/update/remove), username, repository name, role, and operation result (success/failure)
- **FR-011**: System MUST handle GitHub API errors gracefully and report which operations failed
- **FR-012**: System MUST support a dry-run mode that reports planned changes without executing them
- **FR-013**: System MUST verify that specified repositories exist in the organization before attempting to add collaborators
- **FR-014**: System MUST allow a single user to have different roles across different repositories within the same team configuration
- **FR-015**: System MUST skip organization members and only manage outside collaborators
- **FR-016**: System MUST implement exponential backoff with automatic retry when GitHub API rate limits are encountered, respecting the Retry-After header
- **FR-017**: System MUST process team configuration files in alphabetical order by filename to ensure deterministic conflict resolution
- **FR-018**: System MUST apply the role from the last processed file when a user-repository combination appears in multiple team files
- **FR-019**: System MUST report an error and skip processing for repositories that don't exist in the organization, while continuing to process other valid repositories
- **FR-020**: System MUST provide a summary at the end of execution listing all errors encountered (non-existent repositories, failed operations, etc.)

### Non-Functional Requirements

- **NFR-001**: Audit logs MUST be machine-parseable (structured format such as JSON or key-value pairs)
- **NFR-002**: Log entries MUST include ISO 8601 formatted timestamps with timezone information
- **NFR-003**: Logs MUST be written to stdout to enable flexible capture and redirection by the execution environment

### Key Entities

- **Team Configuration**: Represents a logical grouping of users with their repository access definitions. Contains team name (for identification), list of GitHub usernames, and a mapping of repositories to roles. Each team is defined in a separate YAML file.
- **User**: A GitHub username (outside collaborator) who should be granted access to repositories. The same user can appear in multiple team configurations.
- **Repository**: A GitHub repository within the observability-s organization that collaborators need access to. Identified by repository name (not full path, since organization is fixed).
- **Role**: The permission level granted to a user for a specific repository. Must be one of GitHub's standard collaborator roles (read, triage, write, maintain, admin).
- **Access Grant**: The combination of a user, repository, and role that represents a specific permission assignment. Multiple access grants can exist for the same user across different repositories.
- **Audit Log Entry**: A structured record of an action taken by the script, including timestamp, action type, affected user, repository, role, and result status.

## YAML Configuration Format

### Schema Structure

Each team configuration file follows this structure:

```yaml
team_name: <string>           # Identifier for this team (for logging/reporting)
users:                        # List of GitHub usernames
  - <username1>
  - <username2>
  - <username3>
roles:                        # Role-based repository groupings
  <role-name>:               # Role: read, triage, write, maintain, or admin
    - <repo-name-1>
    - <repo-name-2>
    - <repo-name-3>
  <another-role>:
    - <repo-name-4>
    - <repo-name-5>
```

**Valid Roles**: `read`, `triage`, `write`, `maintain`, `admin` (GitHub's standard collaborator permission levels)

### Example 1: Basic Team Configuration

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
  maintain:
    - log-processor
  read:
    - shared-utils
```

**Explanation**: This configuration grants three users (`alice-dev`, `bob-engineer`, `charlie-backend`) access to four repositories. All three users get `write` access to `observability-api` and `metrics-collector`, `maintain` access to `log-processor`, and `read` access to `shared-utils`. Repositories are grouped by their permission level for clarity.

### Example 2: Multiple Teams with Different Access Patterns

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
    - observability-api
```

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
    - log-processor
  maintain:
    - infrastructure-config
  read:
    - dashboard-app
```

**Explanation**: The frontend team gets `write` access to their main application but only `read` access to backend services. The DevOps team gets `admin` access to three backend services for operational control, `maintain` access to infrastructure configuration, and `read` access to the frontend application. Grouping by role makes it easy to see which repositories have the same permission level.

### Example 3: Overlapping Users Across Teams

File: `teams/security-team.yaml`

```yaml
team_name: Security Team
users:
  - alice-dev          # Also in backend-team
  - helen-security
roles:
  admin:
    - observability-api
    - metrics-collector
  maintain:
    - security-scanner
```

**Explanation**: User `alice-dev` appears in both `backend-team.yaml` and `security-team.yaml`. When files are processed alphabetically:
- `backend-team.yaml` processes first: alice-dev gets `write` to observability-api
- `security-team.yaml` processes second: alice-dev's role is **updated** to `admin` for observability-api (last file wins)

Final result: alice-dev has `admin` access to observability-api (from security-team), `write` to metrics-collector (from backend-team), and `maintain` to security-scanner (from security-team).

### Example 4: Single Role Configuration

File: `teams/contractors.yaml`

```yaml
team_name: External Contractors
users:
  - contractor-jane
roles:
  write:
    - public-docs
```

**Explanation**: Simplest valid configuration - one user, one role, one repository. Even with a single role, the role-based structure is used for consistency.

### Example 5: Team with Multiple Roles

File: `teams/data-team.yaml`

```yaml
team_name: Data Analytics Team
users:
  - data-analyst-1
  - data-analyst-2
  - data-engineer-1
roles:
  write:
    - analytics-dashboard
    - data-pipeline
    - reporting-service
  read:
    - observability-api
    - metrics-collector
    - log-processor
    - user-service
    - payment-service
```

**Explanation**: This demonstrates the benefit of role-based grouping. The data team needs `write` access to 3 repositories they maintain and `read` access to 5 repositories they consume data from. Grouping by role makes this immediately clear and easy to maintain.

### Configuration Processing Rules

1. **File Discovery**: Script processes all `.yaml` or `.yml` files in the specified directory
2. **Processing Order**: Files are processed in **alphabetical order** by filename
3. **Conflict Resolution**: If a user appears in multiple files with different roles for the same repository, the **last processed file wins**
4. **Additive Access**: If a user appears in multiple files with roles for **different** repositories, all access grants are applied (access is cumulative across files)
5. **Validation**: Each file is validated for required fields (`team_name`, `users`, `repositories`) before processing
6. **Error Handling**: Invalid files are reported but don't stop processing of other valid files

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrator can define a team configuration in under 5 minutes by creating a YAML file with team name, users, and repository-role mappings
- **SC-002**: Script successfully processes and applies team configurations for at least 50 users across 20 repositories without errors
- **SC-003**: Time to grant access to a new outside collaborator across 10 repositories is reduced from 10+ minutes (manual) to under 30 seconds (automated)
- **SC-004**: 100% of collaborator additions and role updates are logged with timestamp, user, repository, and role for audit compliance
- **SC-005**: Dry-run mode accurately reports all planned changes with zero false positives or false negatives
- **SC-006**: Script completes execution for a typical team configuration (10 users, 5 repositories) in under 2 minutes
- **SC-007**: Configuration errors (invalid YAML, missing fields, non-existent repositories) are detected and reported before any GitHub API calls are made
- **SC-008**: Administrator can understand what changes will be made by reviewing the dry-run output without needing to check GitHub directly
- **SC-009**: Script automatically recovers from GitHub API rate limit errors and completes successfully without manual intervention
- **SC-010**: When conflicting role assignments exist across team files, the final applied role is predictable and matches the last processed file in alphabetical order
- **SC-011**: When a configuration references non-existent repositories, the script processes all valid repositories successfully and provides a clear summary of failures
- **SC-012**: Audit logs can be parsed programmatically by standard log analysis tools without custom parsing logic

### Assumptions

- The observability-s organization exists and the administrator has appropriate permissions to manage outside collaborators
- GitHub API token has sufficient permissions (admin or maintain level) on all repositories that need to be managed and is provided via the GITHUB_TOKEN environment variable
- Outside collaborators have already accepted their invitation to the organization or will be invited separately (this script manages permissions, not invitations)
- YAML files follow a consistent schema that will be documented (schema definition is part of implementation)
- The script will be run manually or via scheduled automation (e.g., cron job, GitHub Actions) - scheduling mechanism is outside scope
- Network connectivity to GitHub API is available when the script runs
- Python 3.8 or higher is available in the execution environment
- Standard Python libraries for YAML parsing and HTTP requests are acceptable dependencies
- Repository names in YAML files are unique within the organization (no need to handle name collisions)
- The script operates on a single organization (observability-s) - multi-organization support is not required
- Role names in YAML files match GitHub's standard role names exactly (case-sensitive)
- Team configuration filenames can be chosen by administrators to control processing order when conflicts exist
- Non-existent repositories in YAML files are typically configuration errors (typos, outdated configs) rather than intentional
- Stdout is available for logging output and can be redirected or captured by the execution environment

### Out of Scope

- Managing organization members (only outside collaborators are managed)
- Creating or deleting repositories
- Managing GitHub Teams (the script is specifically for outside collaborators who cannot be added to Teams)
- Sending invitation emails to new collaborators
- Managing repository settings beyond collaborator access (branch protection, webhooks, etc.)
- User interface or web dashboard (command-line script only)
- Real-time synchronization or webhook-based updates (manual or scheduled execution only)
- Managing access to organization-level resources (only repository-level access)
- Handling GitHub Enterprise Server (GitHub.com only)
- Managing fine-grained personal access tokens or repository-specific tokens
- Automated conflict resolution beyond deterministic file processing order
- Automatic repository creation when referenced repositories don't exist
- Log aggregation, storage, or analysis infrastructure (script only outputs logs)
- Log rotation or retention policies (handled by execution environment)