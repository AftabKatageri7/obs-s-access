# Tasks: GitHub Projects Access Control

**Feature**: GitHub Projects Access Control  
**Branch**: `002-github-projects-access`  
**Status**: Ready for Implementation

---

## Remediation Tasks (Code Review Findings)

**Goal**: Address high-priority issues identified during code review

- [x] [REMED-020] [HIGH] Archive outdated test files (test_e2e_integration.py, test_performance.py) that use non-existent API
- [x] [REMED-021] [HIGH] Add pytest-vcr>=1.0.2 to requirements-dev.txt
- [x] [REMED-022] [HIGH] Verify vcrpy>=5.1.0 in requirements-dev.txt (already present)
- [ ] [REMED-023] [MEDIUM] Fix 38 erroring tests in tests/test_projects_client.py by completing mock setup (10-15 hours estimated)
- [ ] [REMED-024] [MEDIUM] Fix 3 failing assertion tests in tests/test_config_loader.py (1-2 hours estimated)
- [x] [REMED-025] [LOW] Run pytest to verify test status (143/212 passing = 67%)

---

## Phase 1: Setup

**Goal**: Initialize project structure and dependencies for GitHub Projects V2 access control

- [x] T001 Add gql[requests]>=3.5.0 to requirements.txt
- [x] T002 Add pydantic>=2.0.0 to requirements.txt for schema validation
- [x] T003 Add vcrpy>=5.1.0 to requirements-dev.txt for GraphQL response recording
- [x] T004 Create src/github_collab_manager/projects_client.py module file
- [x] T005 Create tests/test_projects_client.py test file

---

## Phase 2: Foundational

**Goal**: Implement core data models and GraphQL client infrastructure needed by all user stories

- [x] T006 Add ProjectPermission enum to src/github_collab_manager/models.py
- [x] T007 Add ProjectConfig dataclass to src/github_collab_manager/models.py
- [x] T008 Add OrganizationProject dataclass to src/github_collab_manager/models.py
- [x] T009 Add RepositoryProject dataclass to src/github_collab_manager/models.py
- [x] T010 Add ProjectAccessGrant dataclass to src/github_collab_manager/models.py
- [x] T011 Initialize GraphQL client with GitHub token in src/github_collab_manager/projects_client.py
- [x] T012 Implement GraphQL query execution with error handling in src/github_collab_manager/projects_client.py
- [x] T013 Implement rate limit detection and retry logic in src/github_collab_manager/projects_client.py

---

## Phase 3: User Story 1 - Define Project Access in Team Configuration (P1)

**User Story**: An organization administrator needs to grant outside collaborators access to GitHub Projects (project boards) in addition to repository access. They extend their existing team YAML files to include a `projects:` section that specifies which organization-level and repository-level projects team members should access and with what permissions (admin, write, read).

**Independent Test Criteria**:
- Can parse YAML files with projects section successfully
- Validates project numbers are positive integers
- Validates permission levels are read/write/admin
- Validates repository names are non-empty strings for repo projects
- Handles missing projects section (backward compatibility)
- Handles empty roles with projects-only configuration

### Implementation Tasks

- [x] T014 [P] [US1] Extend parse_team_config() to parse projects section in src/github_collab_manager/config_loader.py
- [x] T015 [P] [US1] Implement validate_project_config() for schema validation in src/github_collab_manager/config_loader.py
- [x] T016 [US1] Add backward compatibility handling for missing projects section in src/github_collab_manager/config_loader.py
- [x] T017 [US1] Add unit tests for projects section parsing in tests/test_config_loader.py
- [x] T018 [US1] Add unit tests for backward compatibility in tests/test_config_loader.py
- [x] T019 [US1] Create test fixture teams/test-with-projects.yaml with sample project configuration

---

## Phase 4: User Story 2 - Apply Project Access Configuration to GitHub (P2)

**User Story**: An organization administrator runs the script to synchronize project access defined in YAML team configurations with actual GitHub Projects permissions. The script uses GitHub's GraphQL API to add or update outside collaborators' access to specified projects with their assigned permission levels (admin, write, read). All project access operations are logged to stdout in structured format alongside repository operations.

**Independent Test Criteria**:
- Can query organization projects via GraphQL successfully
- Can query repository projects via GraphQL successfully
- Can fetch user ID by username via GraphQL
- Can grant project access with correct permission level
- Can update existing project permission
- Validates project exists before granting access
- Validates user exists before granting access
- Logs all operations with structured format
- Handles GraphQL API errors gracefully
- Processes both repository and project access in single execution

### Implementation Tasks

- [x] T020 [P] [US2] Implement list_organization_projects() in src/github_collab_manager/projects_client.py
- [x] T021 [P] [US2] Implement list_repository_projects() in src/github_collab_manager/projects_client.py
- [x] T022 [P] [US2] Implement get_user_id() helper method in src/github_collab_manager/projects_client.py
- [x] T023 [P] [US2] Implement get_project_collaborators() in src/github_collab_manager/projects_client.py
- [x] T024 [US2] Implement grant_project_access() method in src/github_collab_manager/projects_client.py
- [x] T025 [US2] Implement update_project_permission() method in src/github_collab_manager/projects_client.py
- [x] T026 [US2] Add project validation logic before operations in src/github_collab_manager/projects_client.py
- [x] T027 [US2] Extend audit_logger to support project operations in src/github_collab_manager/audit_logger.py
- [x] T028 [US2] Add resource_type field to log entries in src/github_collab_manager/audit_logger.py
- [x] T029 [US2] Add project-specific log fields in src/github_collab_manager/audit_logger.py
- [x] T030 [US2] Extend Manager.apply_team_config() to process projects in src/github_collab_manager/manager.py
- [x] T031 [US2] Add project access synchronization logic in src/github_collab_manager/manager.py
- [x] T032 [US2] Add error collection and reporting for project operations in src/github_collab_manager/manager.py
- [x] T033 [US2] Add unit tests for GraphQL client methods in tests/test_projects_client.py
- [x] T034 [US2] Add integration tests for project access workflow in tests/test_manager.py
- [x] T035 [US2] Add tests for audit logging with projects in tests/test_audit_logger.py

## Remediation Tasks

- [x] [REMED-001] [CRITICAL] Add ProjectsClient import to src/github_collab_manager/cli.py (line 24)
- [x] [REMED-002] [CRITICAL] Instantiate ProjectsClient in src/github_collab_manager/cli.py (after line 309)
- [x] [REMED-003] [CRITICAL] Pass projects_client to CollaboratorManager in src/github_collab_manager/cli.py (line 341)
- [x] [REMED-004] [CRITICAL] Add project access processing loop in src/github_collab_manager/cli.py (after line 351)
- [x] [REMED-005] [CRITICAL] Update output statistics to include project operations in src/github_collab_manager/cli.py (lines 386-400)
- [x] [REMED-006] [MEDIUM] Fix ProjectsClient initialization parameter in src/github_collab_manager/cli.py (line 314) - change from ProjectsClient(token, org_name) to ProjectsClient(token)
- [x] [REMED-007] [MEDIUM] Implement integration tests for GraphQL client methods in tests/test_projects_client.py (T033)
- [x] [REMED-008] [MEDIUM] Implement integration tests for project access workflow in tests/test_manager.py (T034)
- [x] [REMED-009] [LOW] Add newline at end of requirements.txt
- [x] [REMED-010] [LOW] Add newline at end of requirements-dev.txt

---

## Remediation Tasks (Code Review Findings - 2026-03-25)

**Critical Issues from BobKit-Stakeholder Review**:

- [x] [REMED-011] [CRITICAL] Install missing dependencies: Created .venv virtual environment and installed all dependencies (gql, pydantic, vcrpy)
- [X] [REMED-012] [HIGH] Create integration tests for ProjectsClient in tests/test_projects_client.py with VCR.py mocking for GraphQL queries
  - Added TestProjectsClientVCRIntegration class with 9 VCR.py integration tests
  - Tests cover: list_organization_projects, list_repository_projects, get_user_id, error handling, rate limit tracking, complete workflow
  - Created tests/fixtures/vcr_cassettes/ directory for cassette storage
  - Added .gitignore to exclude cassettes (may contain sensitive data)
  - Tests use @pytest.mark.vcr() decorator for recording/replaying GraphQL API responses
- [X] [REMED-013] [HIGH] Update CLI help text and examples to document projects feature in src/github_collab_manager/cli.py
  - Updated program description to mention GitHub Projects v2 access
  - Added "Team Configuration Format" section with YAML example showing projects syntax
  - Documented project permissions (read, write, admin)
  - Explained organization vs repository projects (with/without repository field)
  - Added 'project' scope to Required Permissions section
  - Noted backward compatibility (projects section is optional)
- [X] [REMED-014] [HIGH] Add process_project_configs() method to CollaboratorManager in src/github_collab_manager/manager.py (Already satisfied by apply_project_access() method at lines 475-643)
- [X] [REMED-015] [HIGH] Add sync_project_access() method to CollaboratorManager in src/github_collab_manager/manager.py (Already satisfied by apply_project_access() method at lines 475-643)
- [X] [REMED-016] [MEDIUM] Add example YAML files with projects configuration to examples/teams/ directory
  - Created three comprehensive example files:
    1. `with-org-projects.yaml`: Demonstrates organization-level projects (no repository field) with read/write/admin permissions
    2. `with-repo-projects.yaml`: Demonstrates repository-level projects (with repository field) scoped to specific repos
    3. `with-mixed-projects.yaml`: Demonstrates both org-level and repo-level projects in a single team configuration
  - Each file includes clear comments explaining the project types and permission levels
- [X] [REMED-017] [MEDIUM] Add rate limit warning logging when remaining < 100 in src/github_collab_manager/projects_client.py
  - Added warning log in `_execute_with_retry()` method after rate limit info extraction (lines 104-108)
  - Logs when `rate_limit_remaining < 100` with message showing remaining requests and reset time
  - Warning format: "GraphQL rate limit running low: {remaining} requests remaining. Resets at: {reset_at}"
- [X] [REMED-018] [MEDIUM] Validate quickstart.md works with current implementation
  - Reviewed quickstart.md against actual implementation
  - Fixed YAML format inconsistencies: Changed from nested `org_projects`/`repo_projects` structure to flat list with `number`, `permission`, and optional `repository` fields
  - Updated all example configurations (lines 54-81, 134-152, 158-179, 186-208, 214-228, 323-332, 370-380)
  - Changed `users` to `members` with `username` field to match actual TeamConfig model
  - Changed `roles` to `repositories` with `name` and `permission` fields to match actual implementation
  - All examples now match the ProjectConfig model structure (number, permission, optional repository)
- [X] [REMED-019] [LOW] Extract common validation logic in config_loader.py to reduce duplication (lines 187-230)
  - Created 5 helper functions: _validate_required_field(), _validate_field_type(), _validate_positive_integer(), _validate_non_empty_string(), _validate_permission_value()
  - Refactored organization_projects validation section (lines ~319-347) to use helper functions
  - Refactored repository_projects validation section (lines ~349-385) to use helper functions
  - Reduced code duplication and improved maintainability

---

## Phase 5: User Story 3 - Validate Project Configuration Before Applying (P3)

**User Story**: An organization administrator wants to verify their project access configurations are correct before applying changes to GitHub. They run the script in dry-run mode which validates project numbers exist, checks current permissions, and reports what changes would be made to project access without actually making them.

**Independent Test Criteria**:
- Reports invalid project numbers without making API calls
- Reports planned project access additions
- Reports planned permission updates
- Reports planned access removals
- Shows current vs desired permission levels
- Validates all projects exist before reporting changes
- Provides unified output for repository and project changes

### Implementation Tasks

- [X] T036 [P] [US3] Implement dry-run mode for project operations in src/github_collab_manager/manager.py
- [X] T037 [US3] Add project existence validation in src/github_collab_manager/projects_client.py
- [X] T038 [US3] Add current permission fetching logic in src/github_collab_manager/projects_client.py
- [X] T039 [US3] Implement permission change diff calculation in src/github_collab_manager/manager.py
- [X] T040 [US3] Add dry-run output formatting for projects in src/github_collab_manager/cli.py
- [X] T041 [US3] Add unit tests for dry-run mode in tests/test_manager.py
- [X] T042 [US3] Add integration tests for validation workflow in tests/test_cli_integration.py

---

## Phase 6: User Story 4 - Remove Stale Project Collaborators (P4)

**User Story**: An organization administrator wants to ensure that collaborators who are no longer in any team configuration are removed from projects. The script can optionally detect collaborators who have project access but are not defined in any current YAML team file and either report them or remove them automatically.

**Independent Test Criteria**:
- Can list all current project collaborators
- Identifies collaborators not in any YAML configuration
- Reports stale collaborators without removing them (report mode)
- Removes stale collaborators when cleanup mode enabled
- Skips organization members (only manages outside collaborators)
- Logs all removal operations
- Handles errors gracefully during cleanup

### Implementation Tasks

- [X] T043 [US4] Implement stale project collaborator detection in src/github_collab_manager/manager.py
- [X] T044 [US4] Add project collaborator filtering logic in src/github_collab_manager/manager.py
- [X] T045 [US4] Implement stale project collaborator removal in src/github_collab_manager/manager.py
- [X] T046 [US4] Add --report-stale flag support for projects in src/github_collab_manager/cli.py
- [X] T047 [US4] Add --remove-stale flag support for projects in src/github_collab_manager/cli.py
- [X] T048 [US4] Add unit tests for stale detection in tests/test_manager.py
- [X] T049 [US4] Add unit tests for stale removal in tests/test_manager.py
- [X] T050 [US4] Add integration tests for stale workflow in tests/test_cli_integration.py

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Finalize documentation, error handling, and production readiness

- [X] T051 Update README.md with GitHub Projects V2 access control usage examples
- [X] T052 Add projects section examples to README.md
- [X] T053 Document token scope requirements in README.md
- [ ] T054 Create examples/projects/ directory with sample configurations
- [X] T055 Add example YAML files with project access in examples/projects/
- [X] T056 Add comprehensive error messages for GraphQL API failures in src/github_collab_manager/projects_client.py
- [X] T057 Add error messages for missing project scope in src/github_collab_manager/projects_client.py
- [X] T058 Update setup.py with new dependencies (gql, pydantic)
- [X] T059 Create migration guide for existing users in docs/MIGRATION.md
- [X] T060 Add troubleshooting section for common project access issues in docs/TROUBLESHOOTING.md

---

## Dependencies

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3-6 (User Stories) → Phase 7 (Polish)
```

**User Story Dependencies**:
- **US1 (Configuration Schema)**: Independent - foundational for all other stories
- **US2 (Apply Configuration)**: Depends on US1 (needs config parsing)
- **US3 (Dry-Run Validation)**: Depends on US1, US2 (needs config and client)
- **US4 (Stale Cleanup)**: Depends on US1, US2 (needs config and client)

**Parallel Execution Opportunities**:

**After Phase 2 completes**:
- US1 (Phase 3) can start immediately

**After US1 completes**:
- US2 (Phase 4) must complete first
- Then US3 (Phase 5) and US4 (Phase 6) can run in parallel

```
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3)
                                                    ↘ Phase 6 (US4)
                                                    ↓
                                                  Phase 7 (Polish)
```

---

## Implementation Strategy

### MVP Scope (Recommended First Iteration)

Implement **Phase 1-4** for a minimal viable product:
- Setup and foundational infrastructure (Phase 1-2)
- Configuration schema extension (US1) - Phase 3
- Project access synchronization (US2) - Phase 4

This provides core functionality to manage project access via YAML configuration.

### Incremental Delivery

1. **Iteration 1 (MVP)**: Phase 1-4 (Setup + US1 + US2)
   - Can parse project configurations
   - Can apply project access to GitHub
   - Basic error handling and logging

2. **Iteration 2**: Phase 5 (US3)
   - Add dry-run validation
   - Improve error reporting
   - Enhance user confidence

3. **Iteration 3**: Phase 6 (US4)
   - Add stale collaborator detection
   - Add cleanup functionality
   - Complete access hygiene features

4. **Iteration 4**: Phase 7 (Polish)
   - Documentation updates
   - Migration guides
   - Production hardening

### Testing Strategy

**Note**: Tests are included in this task list as they are essential for the GraphQL integration and backward compatibility validation. Each user story phase includes its own test tasks to ensure independent testability.

**Test Coverage**:
- Unit tests for data models and validation
- Unit tests for GraphQL client methods
- Integration tests for project access workflow
- End-to-end tests with mocked GraphQL responses
- Backward compatibility tests for existing configs

---

## Task Format Validation

✅ All tasks follow the required checklist format:
- Checkbox: `- [ ]`
- Task ID: Sequential (T001, T002, T003...)
- [P] marker: Only for parallelizable tasks
- [Story] label: [US1], [US2], [US3], [US4] for user story phases
- Description: Clear action with exact file path

**Total Tasks**: 60
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 8 tasks
- Phase 3 (US1): 6 tasks
- Phase 4 (US2): 16 tasks
- Phase 5 (US3): 7 tasks
- Phase 6 (US4): 8 tasks
- Phase 7 (Polish): 10 tasks

**Parallel Opportunities**: 15 tasks marked with [P]

---

**Tasks Version**: 1.0  
**Generated**: 2026-03-24  
**Status**: Ready for implementation

**Next Step**: ✅ Task breakdown created successfully. **Start a new task** and proceed with `/bobkit.checklist` (optional), `/bobkit.analyze` (optional), or `/bobkit.implement` to execute your implementation plan.

---

## Remediation Tasks (Code Review Findings)

**Goal**: Address high-priority issues identified during code review

- [ ] [REMED-020] [HIGH] Archive outdated test files (test_e2e_integration.py, test_performance.py) that use non-existent API
- [ ] [REMED-021] [HIGH] Add pytest-vcr>=1.0.2 to requirements-dev.txt
- [ ] [REMED-022] [HIGH] Add vcrpy>=4.2.1 to requirements-dev.txt (if not already present)
- [ ] [REMED-023] [MEDIUM] Fix 30 erroring tests in tests/test_projects_client.py by completing mock setup
- [ ] [REMED-024] [MEDIUM] Fix 3 failing assertion tests in tests/test_config_loader.py
- [ ] [REMED-025] [LOW] Run pytest on working test files to verify 149+ tests still pass