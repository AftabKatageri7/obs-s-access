# Tasks: GitHub Collaborator Manager

**Feature**: GitHub Collaborator Manager  
**Branch**: `001-github-collab-manager`  
**Created**: 2026-03-06  
**Status**: Ready for Implementation

---

## Task Overview

This task list breaks down the GitHub Collaborator Manager implementation into actionable, dependency-ordered tasks organized by user story. Each user story represents an independently testable increment of functionality.

**Total Tasks**: 47  
**Parallelizable Tasks**: 15  
**User Stories**: 4 (P1-P4)

---

## Phase 1: Setup

**Objective**: Establish project structure, dependencies, and development environment.

**Tasks**:

- [ ] T001 Create project directory structure in obs-s-access/
- [ ] T002 Create requirements.txt with PyGithub>=2.1.0, PyYAML>=6.0
- [ ] T003 Create requirements-dev.txt with pytest>=7.0, pytest-mock>=3.10
- [ ] T004 Create setup.py for package installation
- [ ] T005 Create .env.example with GITHUB_TOKEN, GITHUB_ORG, LOG_LEVEL
- [ ] T006 Create src/github_collab_manager/__init__.py
- [ ] T007 Create tests/__init__.py
- [ ] T008 Create examples/teams/ directory
- [ ] T009 Create README.md with installation instructions

**Validation**: Can install package with `pip install -e .` and import `github_collab_manager` without errors.

---

## Phase 2: Foundational

**Objective**: Implement core data models and utilities needed by all user stories.

**Tasks**:

- [ ] T010 [P] Create src/github_collab_manager/models.py with TeamConfig dataclass
- [ ] T011 [P] Add AccessGrant dataclass to src/github_collab_manager/models.py
- [ ] T012 [P] Add AuditLogEntry dataclass to src/github_collab_manager/models.py
- [ ] T013 [P] Add OperationResult dataclass to src/github_collab_manager/models.py
- [ ] T014 Create src/github_collab_manager/audit_logger.py with JSON log formatting
- [ ] T015 Implement ISO 8601 timestamp generation in src/github_collab_manager/audit_logger.py
- [ ] T016 Implement log_operation() method in src/github_collab_manager/audit_logger.py
- [ ] T017 Create tests/test_audit_logger.py with log format validation tests

**Validation**: All data models can be instantiated and audit logger produces valid JSON output.

---

## Phase 3: User Story 1 - Define Team Access Configuration (P1)

**Story Goal**: Enable administrators to define team configurations in YAML format with users and repository-role mappings.

**Independent Test**: Create sample YAML files and validate they parse correctly without GitHub API interaction.

**Tasks**:

- [ ] T018 [US1] Create src/github_collab_manager/config.py with load_yaml_file() function
- [ ] T019 [US1] Implement validate_yaml_schema() in src/github_collab_manager/config.py
- [ ] T020 [US1] Implement validate_role_names() in src/github_collab_manager/config.py
- [ ] T021 [US1] Implement load_team_configs() in src/github_collab_manager/config.py
- [ ] T022 [US1] Add error reporting with file names and line numbers to src/github_collab_manager/config.py
- [ ] T023 [US1] Create tests/fixtures/sample_teams/valid-team.yaml
- [ ] T024 [US1] Create tests/fixtures/sample_teams/invalid-syntax.yaml
- [ ] T025 [US1] Create tests/fixtures/sample_teams/missing-fields.yaml
- [ ] T026 [US1] Create tests/fixtures/sample_teams/invalid-role.yaml
- [ ] T027 [US1] Create tests/test_config.py with YAML parsing tests
- [ ] T028 [US1] Add schema validation tests to tests/test_config.py
- [ ] T029 [US1] Add error handling tests to tests/test_config.py
- [ ] T030 [US1] Create examples/teams/backend-team.yaml
- [ ] T031 [US1] Create examples/teams/frontend-team.yaml
- [ ] T032 [US1] Create examples/teams/devops-team.yaml

**Acceptance**: Can load valid YAML files and reject invalid ones with clear error messages including file names and line numbers.

---

## Phase 4: User Story 2 - Apply Team Configuration to GitHub (P2)

**Story Goal**: Synchronize YAML team definitions with GitHub repository collaborator settings, handling authentication, API operations, and conflict resolution.

**Independent Test**: Run script against test organization and verify collaborators are added/updated correctly through GitHub UI or API.

**Tasks**:

- [ ] T033 [US2] Create src/github_collab_manager/github_client.py with GitHubClient class
- [ ] T034 [US2] Implement authenticate() method in src/github_collab_manager/github_client.py
- [ ] T035 [US2] Implement get_repository() method in src/github_collab_manager/github_client.py
- [ ] T036 [US2] Implement list_collaborators() method in src/github_collab_manager/github_client.py
- [ ] T037 [US2] Implement add_collaborator() method in src/github_collab_manager/github_client.py
- [ ] T038 [US2] Implement update_collaborator() method in src/github_collab_manager/github_client.py
- [ ] T039 [US2] Implement rate limit handling with exponential backoff in src/github_collab_manager/github_client.py
- [ ] T040 [US2] Create src/github_collab_manager/manager.py with CollaboratorManager class
- [ ] T041 [US2] Implement process_team_configs() in src/github_collab_manager/manager.py
- [ ] T042 [US2] Implement alphabetical file ordering in src/github_collab_manager/manager.py
- [ ] T043 [US2] Implement last-wins conflict resolution in src/github_collab_manager/manager.py
- [ ] T044 [US2] Implement change detection (add vs update vs no-op) in src/github_collab_manager/manager.py
- [ ] T045 [US2] Implement apply_access_grants() in src/github_collab_manager/manager.py
- [ ] T046 [US2] Add error handling for non-existent repositories in src/github_collab_manager/manager.py
- [ ] T047 [US2] Create src/github_collab_manager/cli.py with argument parser
- [ ] T048 [US2] Implement main() function in src/github_collab_manager/cli.py
- [ ] T049 [US2] Add exit code handling in src/github_collab_manager/cli.py
- [ ] T050 [US2] Create tests/test_github_client.py with mocked API tests
- [ ] T051 [US2] Create tests/test_manager.py with conflict resolution tests
- [ ] T052 [US2] Add integration test for complete workflow in tests/test_manager.py
- [ ] T053 [US2] Update README.md with usage examples and authentication setup

**Acceptance**: Script successfully adds/updates collaborators with correct roles, handles conflicts deterministically, logs all operations, and reports errors for non-existent repositories.

---

## Phase 5: User Story 3 - Validate Configuration Before Applying (P3)

**Story Goal**: Provide dry-run and validation modes to verify configurations before making changes to GitHub.

**Independent Test**: Run script with --dry-run flag and verify it reports planned changes without modifying GitHub.

**Tasks**:

- [ ] T054 [P] [US3] Add --dry-run flag to src/github_collab_manager/cli.py
- [ ] T055 [P] [US3] Add --validate-only flag to src/github_collab_manager/cli.py
- [ ] T056 [US3] Implement dry_run mode in src/github_collab_manager/manager.py
- [ ] T057 [US3] Implement validate_only mode in src/github_collab_manager/manager.py
- [ ] T058 [US3] Add repository existence validation in src/github_collab_manager/github_client.py
- [ ] T059 [US3] Add conflict reporting in dry-run mode to src/github_collab_manager/manager.py
- [ ] T060 [US3] Create tests/test_cli.py with dry-run mode tests
- [ ] T061 [US3] Add validation mode tests to tests/test_cli.py
- [ ] T062 [US3] Update README.md with dry-run and validation examples

**Acceptance**: Dry-run mode reports all planned changes without contacting GitHub API. Validation mode checks YAML syntax and reports issues without making changes.

---

## Phase 6: User Story 4 - Remove Stale Collaborators (P4)

**Story Goal**: Detect and optionally remove collaborators who are no longer in any team configuration.

**Independent Test**: Set up repositories with existing collaborators, run script with configurations excluding some collaborators, verify correct identification/removal.

**Tasks**:

- [ ] T063 [P] [US4] Add --remove-stale flag to src/github_collab_manager/cli.py
- [ ] T064 [P] [US4] Add --report-stale flag to src/github_collab_manager/cli.py
- [ ] T065 [US4] Implement detect_stale_collaborators() in src/github_collab_manager/manager.py
- [ ] T066 [US4] Implement remove_collaborator() in src/github_collab_manager/github_client.py
- [ ] T067 [US4] Add organization member filtering in src/github_collab_manager/manager.py
- [ ] T068 [US4] Implement remove_stale_collaborators() in src/github_collab_manager/manager.py
- [ ] T069 [US4] Add stale collaborator tests to tests/test_manager.py
- [ ] T070 [US4] Update README.md with stale collaborator removal examples

**Acceptance**: Script correctly identifies collaborators not in any YAML file and can report or remove them while preserving organization members.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Objective**: Finalize documentation, add comprehensive error handling, and ensure production readiness.

**Tasks**:

- [ ] T071 Add comprehensive error messages for all failure scenarios in src/github_collab_manager/cli.py
- [ ] T072 Implement operation summary reporting in src/github_collab_manager/cli.py
- [ ] T073 Add help text and usage examples to src/github_collab_manager/cli.py
- [ ] T074 Create YAML schema documentation in README.md
- [ ] T075 Add troubleshooting section to README.md
- [ ] T076 Add security best practices section to README.md
- [ ] T077 Create examples/teams/security-team.yaml demonstrating overlapping users
- [ ] T078 Create examples/teams/contractors.yaml demonstrating single role
- [ ] T079 Add performance testing for 50 users across 20 repositories
- [ ] T080 Add end-to-end integration test with sample configurations
- [ ] T081 Update README.md with complete API reference

**Validation**: All documentation is complete, error messages are clear, and script handles edge cases gracefully.

---

## Dependencies

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 7 (Polish)
```

**Dependency Graph**:

- **US1** (P1): No dependencies (can start after Foundational)
- **US2** (P2): Depends on US1 (needs config loading)
- **US3** (P3): Depends on US2 (needs apply logic to validate against)
- **US4** (P4): Depends on US2 (needs collaborator management logic)

**Parallel Opportunities**:

- Within **Phase 2**: Tasks T010-T013 (data models) can be implemented in parallel
- Within **US1**: Tasks T023-T026 (test fixtures) and T030-T032 (examples) can be created in parallel
- Within **US3**: Tasks T054-T055 (CLI flags) can be added in parallel
- Within **US4**: Tasks T063-T064 (CLI flags) can be added in parallel

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Recommended MVP**: Complete through **Phase 4 (User Story 2)** for core functionality.

This provides:
- ✅ YAML configuration loading and validation (US1)
- ✅ GitHub API integration with authentication (US2)
- ✅ Collaborator addition and role updates (US2)
- ✅ Conflict resolution (US2)
- ✅ Audit logging (US2)
- ✅ Error handling for non-existent repositories (US2)

**Post-MVP Enhancements**:
- Phase 5 (US3): Dry-run and validation modes for safety
- Phase 6 (US4): Stale collaborator cleanup for hygiene
- Phase 7: Documentation polish and advanced error handling

### Incremental Delivery

1. **Week 1**: Complete Setup (Phase 1) and Foundational (Phase 2)
2. **Week 2**: Complete US1 (configuration loading)
3. **Week 3**: Complete US2 (GitHub integration and apply logic)
4. **Week 4**: Complete US3 (validation modes) and US4 (stale cleanup)
5. **Week 5**: Complete Polish phase and production hardening

### Testing Strategy

- **Unit Tests**: Each module has corresponding test file
- **Integration Tests**: End-to-end workflow tests in tests/test_manager.py
- **Manual Testing**: Test against real GitHub organization with test repositories
- **Performance Testing**: Validate with 50 users across 20 repositories (Task T079)

---

## Task Format Validation

✅ All tasks follow the required checklist format:
- Checkbox: `- [ ]`
- Task ID: Sequential (T001-T081)
- [P] marker: Present only for parallelizable tasks
- [Story] label: Present for user story phase tasks (US1-US4)
- File paths: Included in all implementation tasks

---

## Next Steps

✅ Task breakdown created successfully. **Start a new task** and proceed with:
- `/bobkit.checklist` (optional) - Create quality validation checklist
- `/bobkit.analyze` (optional) - Analyze artifact consistency
- `/bobkit.implement` - Begin implementation

---

**Tasks Version**: 1.0  
**Last Updated**: 2026-03-06