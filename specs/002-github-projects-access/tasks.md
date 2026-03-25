# Tasks: GitHub Projects Access Control

**Feature**: GitHub Projects Access Control  
**Branch**: `002-github-projects-access`  
**Status**: Ready for Implementation

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
- [ ] T033 [US2] Add unit tests for GraphQL client methods in tests/test_projects_client.py
- [ ] T034 [US2] Add integration tests for project access workflow in tests/test_manager.py
- [ ] T035 [US2] Add tests for audit logging with projects in tests/test_audit_logger.py

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

- [ ] T036 [P] [US3] Implement dry-run mode for project operations in src/github_collab_manager/manager.py
- [ ] T037 [US3] Add project existence validation in src/github_collab_manager/projects_client.py
- [ ] T038 [US3] Add current permission fetching logic in src/github_collab_manager/projects_client.py
- [ ] T039 [US3] Implement permission change diff calculation in src/github_collab_manager/manager.py
- [ ] T040 [US3] Add dry-run output formatting for projects in src/github_collab_manager/cli.py
- [ ] T041 [US3] Add unit tests for dry-run mode in tests/test_manager.py
- [ ] T042 [US3] Add integration tests for validation workflow in tests/test_cli_integration.py

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

- [ ] T043 [P] [US4] Implement detect_stale_collaborators() in src/github_collab_manager/manager.py
- [ ] T044 [US4] Add organization member detection logic in src/github_collab_manager/projects_client.py
- [ ] T045 [US4] Implement revoke_project_access() method in src/github_collab_manager/projects_client.py
- [ ] T046 [US4] Add --report-stale CLI flag in src/github_collab_manager/cli.py
- [ ] T047 [US4] Add --cleanup-stale CLI flag in src/github_collab_manager/cli.py
- [ ] T048 [US4] Add stale collaborator reporting logic in src/github_collab_manager/manager.py
- [ ] T049 [US4] Add unit tests for stale detection in tests/test_manager.py
- [ ] T050 [US4] Add end-to-end tests for cleanup workflow in tests/test_e2e_integration.py

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Finalize documentation, error handling, and production readiness

- [ ] T051 Update README.md with GitHub Projects V2 access control usage examples
- [ ] T052 Add projects section examples to README.md
- [ ] T053 Document token scope requirements in README.md
- [ ] T054 Create examples/projects/ directory with sample configurations
- [ ] T055 Add example YAML files with project access in examples/projects/
- [ ] T056 Add comprehensive error messages for GraphQL API failures in src/github_collab_manager/projects_client.py
- [ ] T057 Add error messages for missing project scope in src/github_collab_manager/projects_client.py
- [ ] T058 Update setup.py with new dependencies (gql, pydantic)
- [ ] T059 Create migration guide for existing users in docs/MIGRATION.md
- [ ] T060 Add troubleshooting section for common project access issues in docs/TROUBLESHOOTING.md

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