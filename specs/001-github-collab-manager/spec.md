# Feature Specification: GitHub Collaborator Manager

**Feature Branch**: `001-github-collab-manager`  
**Created**: 2026-03-06  
**Status**: Draft  
**Input**: User description: "Create a Python script for managing GitHub repository collaborators within the observability-s organization using YAML-based team definitions, where each team configuration file specifies users and their repository access levels across multiple repositories, with support for assigning different roles per repository since GitHub Teams cannot be used for outside collaborators, implementing functionality to read team definitions from YAML files that contain team names, user lists, and nested role-to-repository mappings allowing a single team to grant users write access to certain repositories and different access levels to other repositories, with the script handling authentication to the GitHub API, parsing the YAML team configurations, and programmatically adding or updating outside collaborators with their specified roles across all repositories defined in each team's configuration"

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

An organization administrator runs the script to synchronize the YAML team definitions with actual GitHub repository collaborator settings. The script authenticates with GitHub, reads the team configuration files, and adds or updates outside collaborators with their specified roles across all defined repositories.

**Why this priority**: This is the primary operational functionality that delivers the core value - automating the tedious manual process of adding collaborators to multiple repositories. It builds directly on P1's configuration format.

**Independent Test**: Can be tested by running the script against a test organization with test repositories, verifying that collaborators are added with correct permissions, and confirming through GitHub's UI or API that the changes were applied correctly.

**Acceptance Scenarios**:

1. **Given** a valid YAML team configuration and GitHub API credentials, **When** the script is executed, **Then** all users in the team are added as outside collaborators to their assigned repositories with the correct roles
2. **Given** a user already exists as a collaborator with a different role, **When** the script runs with updated role in YAML, **Then** the user's role is updated to match the YAML configuration
3. **Given** multiple team configuration files in a directory, **When** the script processes all files, **Then** all teams are synchronized without conflicts or errors
4. **Given** invalid GitHub credentials, **When** the script attempts to authenticate, **Then** a clear error message is displayed and the script exits gracefully

---

### User Story 3 - Validate Configuration Before Applying (Priority: P3)

An organization administrator wants to verify their YAML team configurations are correct before applying changes to GitHub. They run the script in a dry-run or validation mode that checks the configuration files for errors, validates that specified users and repositories exist, and reports what changes would be made without actually making them.

**Why this priority**: This is a safety and usability feature that prevents mistakes and provides confidence before making changes. While valuable, the system can function without it - administrators can manually review YAML files and check GitHub after applying changes.

**Independent Test**: Can be tested by running the script with a --dry-run flag against various YAML configurations (valid, invalid, with non-existent users/repos) and verifying that it reports issues correctly without making any actual changes to GitHub.

**Acceptance Scenarios**:

1. **Given** a YAML configuration with syntax errors, **When** validation is run, **Then** specific syntax errors are reported with line numbers and the script exits without contacting GitHub
2. **Given** a valid YAML configuration, **When** dry-run mode is executed, **Then** the script reports what changes would be made (users to add, roles to update) without actually modifying GitHub
3. **Given** a configuration referencing non-existent repositories, **When** validation checks GitHub, **Then** the script reports which repositories don't exist in the organization

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

- What happens when a YAML file specifies a repository that doesn't exist in the organization?
- How does the system handle GitHub API rate limits when processing many repositories and users?
- What happens when a user is specified in multiple team files with conflicting roles for the same repository?
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
- **FR-004**: System MUST authenticate to GitHub API using a personal access token or GitHub App credentials
- **FR-005**: System MUST add users as outside collaborators to repositories if they don't already have access
- **FR-006**: System MUST update existing collaborator roles when the YAML configuration specifies a different role than currently assigned
- **FR-007**: System MUST handle multiple team configuration files in a single execution
- **FR-008**: System MUST validate YAML syntax and structure before attempting to contact GitHub API
- **FR-009**: System MUST provide clear error messages when YAML files are malformed or missing required fields
- **FR-010**: System MUST log all actions taken (collaborators added, roles updated) for audit purposes
- **FR-011**: System MUST handle GitHub API errors gracefully and report which operations failed
- **FR-012**: System MUST support a dry-run mode that reports planned changes without executing them
- **FR-013**: System MUST verify that specified repositories exist in the organization before attempting to add collaborators
- **FR-014**: System MUST allow a single user to have different roles across different repositories within the same team configuration
- **FR-015**: System MUST skip organization members and only manage outside collaborators

### Key Entities

- **Team Configuration**: Represents a logical grouping of users with their repository access definitions. Contains team name (for identification), list of GitHub usernames, and a mapping of repositories to roles. Each team is defined in a separate YAML file.
- **User**: A GitHub username (outside collaborator) who should be granted access to repositories. The same user can appear in multiple team configurations.
- **Repository**: A GitHub repository within the observability-s organization that collaborators need access to. Identified by repository name (not full path, since organization is fixed).
- **Role**: The permission level granted to a user for a specific repository. Must be one of GitHub's standard collaborator roles (read, triage, write, maintain, admin).
- **Access Grant**: The combination of a user, repository, and role that represents a specific permission assignment. Multiple access grants can exist for the same user across different repositories.

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

### Assumptions

- The observability-s organization exists and the administrator has appropriate permissions to manage outside collaborators
- GitHub API token or credentials have sufficient permissions (admin or maintain level) on all repositories that need to be managed
- Outside collaborators have already accepted their invitation to the organization or will be invited separately (this script manages permissions, not invitations)
- YAML files follow a consistent schema that will be documented (schema definition is part of implementation)
- The script will be run manually or via scheduled automation (e.g., cron job, GitHub Actions) - scheduling mechanism is outside scope
- Network connectivity to GitHub API is available when the script runs
- Python 3.8 or higher is available in the execution environment
- Standard Python libraries for YAML parsing and HTTP requests are acceptable dependencies
- Repository names in YAML files are unique within the organization (no need to handle name collisions)
- The script operates on a single organization (observability-s) - multi-organization support is not required
- Role names in YAML files match GitHub's standard role names exactly (case-sensitive)
- When a user appears in multiple team files with different roles for the same repository, the last processed configuration takes precedence (processing order should be deterministic, e.g., alphabetical by filename)

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
- Automated conflict resolution when multiple team files specify different roles for the same user-repository combination