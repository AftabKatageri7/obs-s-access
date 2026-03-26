"""
End-to-end integration tests for GitHub Collaborator Manager.

Tests complete workflows with sample configurations to verify:
- Configuration loading and validation
- Conflict resolution across multiple files
- Plan generation with existing collaborators
- Dry-run mode operation
- Stale collaborator detection and removal
- Audit logging throughout the workflow
"""

import json
import tempfile
from pathlib import Path
from typing import List
import pytest
from unittest.mock import Mock, MagicMock, call

from github_collab_manager.config_loader import load_team_configs
from github_collab_manager.manager import CollaboratorManager
from github_collab_manager.audit_logger import AuditLogger
from github_collab_manager.models import TeamConfig, RepositoryPermission, CollaboratorInfo


class TestEndToEndIntegration:
    """End-to-end integration tests with realistic scenarios."""

    @pytest.fixture
    def sample_configs_dir(self, tmp_path) -> Path:
        """Create sample configuration files for testing."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        
        # Create engineering team config
        engineering_config = configs_dir / "engineering.yaml"
        engineering_config.write_text("""
engineering-leads:
  members:
    - alice-eng
    - bob-eng
  repositories:
    - repo: observability-s/core-service
      permission: admin
    - repo: observability-s/api-gateway
      permission: admin

engineering-team:
  members:
    - alice-eng
    - charlie-dev
    - diana-dev
  repositories:
    - repo: observability-s/core-service
      permission: write
    - repo: observability-s/api-gateway
      permission: write
    - repo: observability-s/frontend
      permission: write
""")
        
        # Create operations team config
        operations_config = configs_dir / "operations.yaml"
        operations_config.write_text("""
ops-team:
  members:
    - eve-ops
    - frank-sre
  repositories:
    - repo: observability-s/infrastructure
      permission: admin
    - repo: observability-s/monitoring
      permission: admin

on-call:
  members:
    - eve-ops
    - charlie-dev
  repositories:
    - repo: observability-s/core-service
      permission: write
    - repo: observability-s/monitoring
      permission: write
""")
        
        return configs_dir

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client with realistic responses."""
        client = Mock()
        
        # Mock existing collaborators for different repositories
        def get_collaborators(repo: str) -> List[CollaboratorInfo]:
            existing = {
                "observability-s/core-service": [
                    CollaboratorInfo(username="alice-eng", permission="admin"),
                    CollaboratorInfo(username="old-dev", permission="write"),  # Stale
                ],
                "observability-s/api-gateway": [
                    CollaboratorInfo(username="bob-eng", permission="write"),  # Needs update
                ],
                "observability-s/frontend": [
                    CollaboratorInfo(username="stale-contractor", permission="read"),  # Stale
                ],
                "observability-s/infrastructure": [],
                "observability-s/monitoring": [
                    CollaboratorInfo(username="eve-ops", permission="admin"),
                ],
            }
            return existing.get(repo, [])
        
        client.get_repository_collaborators.side_effect = get_collaborators
        client.add_collaborator.return_value = None
        client.update_collaborator_permission.return_value = None
        client.remove_collaborator.return_value = None
        
        return client

    @pytest.fixture
    def audit_log_file(self, tmp_path) -> Path:
        """Create temporary audit log file."""
        return tmp_path / "audit.log"

    def test_complete_workflow_without_stale_removal(
        self, sample_configs_dir, mock_github_client, audit_log_file
    ):
        """Test complete workflow: load configs, plan changes, apply without stale removal."""
        # Setup
        logger = AuditLogger(str(audit_log_file))
        manager = CollaboratorManager(mock_github_client, logger)
        
        # Load all configuration files
        configs, validation_result = load_team_configs(str(sample_configs_dir))
        
        # Verify configurations loaded successfully
        assert validation_result.valid, f"Config validation failed: {validation_result.errors}"
        assert len(configs) == 2  # 2 config files: engineering.yaml and operations.yaml
        
        # Plan changes without removing stale collaborators
        plan = manager.plan_changes(configs, remove_stale=False)
        
        # Verify plan contains expected operations
        assert len(plan.additions) > 0  # New collaborators to add
        assert len(plan.updates) > 0  # Existing collaborators to update
        assert len(plan.removals) == 0  # No removals without --remove-stale
        
        # Apply changes
        results = manager.apply_changes(plan)
        
        # Verify results
        assert len(results) > 0
        successful = [r for r in results if r.success]
        assert len(successful) == len(results)  # All operations should succeed
        
        # Verify audit log was written
        assert audit_log_file.exists()
        log_entries = audit_log_file.read_text().strip().split("\n")
        assert len(log_entries) > 0
        
        # Verify audit log contains expected entries
        for entry_line in log_entries:
            entry = json.loads(entry_line)
            assert "timestamp" in entry
            assert "action" in entry
            assert entry["action"] in ["add_collaborator", "update_permission"]

    def test_complete_workflow_with_stale_removal(
        self, sample_configs_dir, mock_github_client, audit_log_file
    ):
        """Test complete workflow with stale collaborator removal."""
        # Setup
        logger = AuditLogger(str(audit_log_file))
        loader = ConfigLoader()
        manager = CollaboratorManager(mock_github_client, logger)
        
        # Load configurations
        config_files = [str(f) for f in sample_configs_dir.glob("*.yaml")]
        configs = loader.load_configs(config_files)
        
        # Plan changes WITH stale removal
        plan = manager.plan_changes(configs, remove_stale=True)
        
        # Verify plan includes removals for stale collaborators
        assert len(plan.removals) > 0  # Should detect stale collaborators
        
        # Verify specific stale collaborators are identified
        stale_users = {r.username for r in plan.removals}
        assert "old-dev" in stale_users
        assert "stale-contractor" in stale_users
        
        # Apply changes
        results = manager.apply_changes(plan)
        
        # Verify removals were executed
        removal_results = [r for r in results if r.action == "remove_collaborator"]
        assert len(removal_results) > 0
        
        # Verify audit log contains removal entries
        log_entries = audit_log_file.read_text().strip().split("\n")
        removal_logs = [json.loads(line) for line in log_entries if "remove_collaborator" in line]
        assert len(removal_logs) > 0

    def test_dry_run_mode(self, sample_configs_dir, mock_github_client, audit_log_file):
        """Test dry-run mode: plan changes but don't apply them."""
        # Setup
        logger = AuditLogger(str(audit_log_file))
        loader = ConfigLoader()
        manager = CollaboratorManager(mock_github_client, logger)
        
        # Load configurations
        config_files = [str(f) for f in sample_configs_dir.glob("*.yaml")]
        configs = loader.load_configs(config_files)
        
        # Plan changes
        plan = manager.plan_changes(configs, remove_stale=True)
        
        # Verify plan was generated
        total_operations = len(plan.additions) + len(plan.updates) + len(plan.removals)
        assert total_operations > 0
        
        # In dry-run mode, we DON'T call apply_changes
        # Verify no API calls were made (except for getting existing collaborators)
        add_calls = mock_github_client.add_collaborator.call_count
        update_calls = mock_github_client.update_collaborator_permission.call_count
        remove_calls = mock_github_client.remove_collaborator.call_count
        
        assert add_calls == 0, "Dry-run should not add collaborators"
        assert update_calls == 0, "Dry-run should not update permissions"
        assert remove_calls == 0, "Dry-run should not remove collaborators"

    def test_conflict_resolution_across_files(
        self, sample_configs_dir, mock_github_client, audit_log_file
    ):
        """Test conflict resolution when same user appears in multiple files."""
        # Setup
        logger = AuditLogger(str(audit_log_file))
        loader = ConfigLoader()
        manager = CollaboratorManager(mock_github_client, logger)
        
        # Load configurations (alice-eng and charlie-dev appear in multiple roles)
        config_files = sorted([str(f) for f in sample_configs_dir.glob("*.yaml")])
        configs = loader.load_configs(config_files)
        
        # Plan changes
        plan = manager.plan_changes(configs, remove_stale=False)
        
        # Verify alice-eng gets admin permission (highest from engineering-leads)
        alice_operations = [
            op for op in plan.additions + plan.updates
            if op.username == "alice-eng" and op.repo == "observability-s/core-service"
        ]
        assert len(alice_operations) > 0
        # alice-eng should have admin (from engineering-leads), not push (from engineering-team)
        assert all(op.permission == "admin" for op in alice_operations)
        
        # Verify charlie-dev appears in both engineering and operations
        charlie_repos = {
            op.repo for op in plan.additions + plan.updates
            if op.username == "charlie-dev"
        }
        assert "observability-s/core-service" in charlie_repos  # From engineering-team
        assert "observability-s/monitoring" in charlie_repos  # From on-call

    def test_error_handling_and_recovery(
        self, sample_configs_dir, mock_github_client, audit_log_file
    ):
        """Test error handling when some operations fail."""
        # Setup with failing operations
        logger = AuditLogger(str(audit_log_file))
        loader = ConfigLoader()
        
        # Configure client to fail on specific operations
        def add_collaborator_with_failures(repo: str, username: str, permission: str):
            if username == "charlie-dev" and repo == "observability-s/frontend":
                raise Exception("API rate limit exceeded")
            return None
        
        mock_github_client.add_collaborator.side_effect = add_collaborator_with_failures
        
        manager = CollaboratorManager(mock_github_client, logger)
        
        # Load configurations
        config_files = [str(f) for f in sample_configs_dir.glob("*.yaml")]
        configs = loader.load_configs(config_files)
        
        # Plan and apply changes
        plan = manager.plan_changes(configs, remove_stale=False)
        results = manager.apply_changes(plan)
        
        # Verify some operations succeeded and some failed
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        assert len(successful) > 0, "Some operations should succeed"
        assert len(failed) > 0, "Some operations should fail"
        
        # Verify failed operation has error message
        charlie_failures = [
            r for r in failed
            if r.username == "charlie-dev" and r.repo == "observability-s/frontend"
        ]
        assert len(charlie_failures) > 0
        assert "rate limit" in charlie_failures[0].error.lower()
        
        # Verify audit log contains both successes and failures
        log_entries = audit_log_file.read_text().strip().split("\n")
        assert len(log_entries) > 0
        
        success_logs = [json.loads(line) for line in log_entries if '"success": true' in line]
        failure_logs = [json.loads(line) for line in log_entries if '"success": false' in line]
        
        assert len(success_logs) > 0
        assert len(failure_logs) > 0

    def test_validate_only_mode(self, sample_configs_dir):
        """Test validate-only mode: check YAML syntax without GitHub connection."""
        # Setup (no GitHub client needed)
        loader = ConfigLoader()
        
        # Load and validate configurations
        config_files = [str(f) for f in sample_configs_dir.glob("*.yaml")]
        configs = loader.load_configs(config_files)
        
        # Verify configurations are valid
        assert len(configs) > 0
        
        # Verify all required fields are present
        for config in configs:
            assert config.members is not None
            assert len(config.members) > 0
            assert config.repositories is not None
            assert len(config.repositories) > 0
            
            for repo_perm in config.repositories:
                assert repo_perm.repo is not None
                assert repo_perm.permission in ["read", "write", "admin"]

    def test_operation_summary_reporting(
        self, sample_configs_dir, mock_github_client, audit_log_file
    ):
        """Test operation summary reporting after applying changes."""
        # Setup
        logger = AuditLogger(str(audit_log_file))
        loader = ConfigLoader()
        manager = CollaboratorManager(mock_github_client, logger)
        
        # Load configurations
        config_files = [str(f) for f in sample_configs_dir.glob("*.yaml")]
        configs = loader.load_configs(config_files)
        
        # Plan and apply changes
        plan = manager.plan_changes(configs, remove_stale=True)
        results = manager.apply_changes(plan)
        
        # Categorize results by operation type
        additions = [r for r in results if r.action == "add_collaborator"]
        updates = [r for r in results if r.action == "update_permission"]
        removals = [r for r in results if r.action == "remove_collaborator"]
        no_changes = [r for r in results if r.action == "no_change"]
        
        # Verify operation summary
        total_operations = len(additions) + len(updates) + len(removals) + len(no_changes)
        assert total_operations == len(results)
        
        # Verify each category has expected operations
        assert len(additions) > 0, "Should have additions"
        assert len(updates) > 0, "Should have updates"
        assert len(removals) > 0, "Should have removals (stale collaborators)"
        
        # Group by repository
        repos_affected = set(r.repo for r in results)
        assert len(repos_affected) > 0
        
        # Verify all expected repositories are affected
        expected_repos = {
            "observability-s/core-service",
            "observability-s/api-gateway",
            "observability-s/frontend",
            "observability-s/infrastructure",
            "observability-s/monitoring",
        }
        assert repos_affected == expected_repos


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

# Made with Bob
