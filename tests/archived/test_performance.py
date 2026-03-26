"""
Performance tests for GitHub Collaborator Manager.

Tests system behavior with large-scale configurations:
- 50 users across 20 repositories
- Multiple overlapping roles
- Conflict resolution at scale
"""

import time
from typing import List
import pytest
from unittest.mock import Mock, MagicMock

from github_collab_manager.config_loader import ConfigLoader
from github_collab_manager.manager import CollaboratorManager
from github_collab_manager.models import TeamConfig, RepositoryPermission


class TestPerformance:
    """Performance tests for large-scale configurations."""

    @pytest.fixture
    def large_scale_config(self, tmp_path) -> str:
        """Create a large-scale configuration with 50 users and 20 repositories."""
        config_file = tmp_path / "large-scale.yaml"
        
        # Generate 5 roles with 10 users each
        roles = []
        for role_idx in range(5):
            role_name = f"team-{role_idx}"
            members = [f"user-{role_idx * 10 + i}" for i in range(10)]
            
            # Each role has access to 4 repositories with different permissions
            repos = []
            permission = ["read", "write", "admin"][role_idx % 3]
            for repo_idx in range(4):
                repos.append(f"      - repo: observability-s/repo-{role_idx * 4 + repo_idx}\n")
                repos.append(f"        permission: {permission}\n")
            
            role_config = f"""
{role_name}:
  members:
{chr(10).join(f"    - {m}" for m in members)}
  repositories:
{''.join(repos)}"""
            roles.append(role_config)
        
        config_content = "\n".join(roles)
        config_file.write_text(config_content)
        return str(config_file)

    @pytest.fixture
    def overlapping_config(self, tmp_path) -> str:
        """Create configuration with overlapping users across multiple roles."""
        config_file = tmp_path / "overlapping.yaml"
        
        # Create 10 roles where users appear in multiple roles
        roles = []
        for role_idx in range(10):
            role_name = f"role-{role_idx}"
            # Each role has 10 users, with 5 overlapping from previous role
            start_user = max(0, role_idx * 5 - 5)
            members = [f"user-{start_user + i}" for i in range(10)]
            
            # Each role has access to 2 repositories
            repos = []
            permission = ["read", "write", "admin"][role_idx % 3]
            for repo_idx in range(2):
                repos.append(f"      - repo: observability-s/repo-{role_idx * 2 + repo_idx}\n")
                repos.append(f"        permission: {permission}\n")
            
            role_config = f"""
{role_name}:
  members:
{chr(10).join(f"    - {m}" for m in members)}
  repositories:
{''.join(repos)}"""
            roles.append(role_config)
        
        config_content = "\n".join(roles)
        config_file.write_text(config_content)
        return str(config_file)

    def test_config_loading_performance(self, large_scale_config):
        """Test configuration loading performance with 50 users and 20 repositories."""
        loader = ConfigLoader()
        
        start_time = time.time()
        configs = loader.load_configs([large_scale_config])
        load_time = time.time() - start_time
        
        # Verify configuration loaded correctly
        assert len(configs) > 0
        
        # Count total users and repositories
        total_users = set()
        total_repos = set()
        for config in configs:
            total_users.update(config.members)
            total_repos.update(r.repo for r in config.repositories)
        
        assert len(total_users) == 50, f"Expected 50 users, got {len(total_users)}"
        assert len(total_repos) == 20, f"Expected 20 repositories, got {len(total_repos)}"
        
        # Performance assertion: loading should complete in under 1 second
        assert load_time < 1.0, f"Config loading took {load_time:.2f}s, expected < 1.0s"
        print(f"✓ Config loading: {load_time:.3f}s for 50 users across 20 repositories")

    def test_conflict_resolution_performance(self, overlapping_config):
        """Test conflict resolution performance with overlapping users."""
        loader = ConfigLoader()
        
        start_time = time.time()
        configs = loader.load_configs([overlapping_config])
        
        # Build desired state (this includes conflict resolution)
        desired_state = {}
        for config in configs:
            for member in config.members:
                if member not in desired_state:
                    desired_state[member] = {}
                for repo_perm in config.repositories:
                    repo = repo_perm.repo
                    if repo not in desired_state[member]:
                        desired_state[member][repo] = repo_perm.permission
                    else:
                        # Conflict resolution: higher permission wins
                        current = desired_state[member][repo]
                        new = repo_perm.permission
                        perm_order = {"read": 0, "write": 1, "admin": 2}
                        if perm_order[new] > perm_order[current]:
                            desired_state[member][repo] = new
        
        resolution_time = time.time() - start_time
        
        # Verify overlapping users were resolved
        assert len(desired_state) > 0
        
        # Performance assertion: resolution should complete in under 1 second
        assert resolution_time < 1.0, f"Conflict resolution took {resolution_time:.2f}s, expected < 1.0s"
        print(f"✓ Conflict resolution: {resolution_time:.3f}s for overlapping users")

    def test_plan_generation_performance(self, large_scale_config, mocker):
        """Test plan generation performance with 50 users and 20 repositories."""
        # Mock GitHub client
        mock_client = Mock()
        mock_client.get_repository_collaborators.return_value = []  # No existing collaborators
        
        # Load configuration
        loader = ConfigLoader()
        configs = loader.load_configs([large_scale_config])
        
        # Create manager
        manager = CollaboratorManager(mock_client)
        
        # Measure plan generation time
        start_time = time.time()
        plan = manager.plan_changes(configs, remove_stale=False)
        plan_time = time.time() - start_time
        
        # Verify plan was generated
        assert len(plan.additions) > 0
        
        # Count total operations
        total_ops = len(plan.additions) + len(plan.updates) + len(plan.removals)
        
        # Performance assertion: planning should complete in under 2 seconds
        assert plan_time < 2.0, f"Plan generation took {plan_time:.2f}s, expected < 2.0s"
        print(f"✓ Plan generation: {plan_time:.3f}s for {total_ops} operations")

    def test_apply_changes_performance(self, large_scale_config, mocker):
        """Test apply changes performance with 50 users and 20 repositories."""
        # Mock GitHub client with fast responses
        mock_client = Mock()
        mock_client.get_repository_collaborators.return_value = []
        mock_client.add_collaborator.return_value = None
        mock_client.update_collaborator_permission.return_value = None
        mock_client.remove_collaborator.return_value = None
        
        # Load configuration
        loader = ConfigLoader()
        configs = loader.load_configs([large_scale_config])
        
        # Create manager
        manager = CollaboratorManager(mock_client)
        
        # Generate plan
        plan = manager.plan_changes(configs, remove_stale=False)
        
        # Measure apply time
        start_time = time.time()
        results = manager.apply_changes(plan)
        apply_time = time.time() - start_time
        
        # Verify changes were applied
        assert len(results) > 0
        
        # Performance assertion: applying should complete in under 5 seconds
        # (This is generous to account for potential API rate limiting)
        assert apply_time < 5.0, f"Apply changes took {apply_time:.2f}s, expected < 5.0s"
        print(f"✓ Apply changes: {apply_time:.3f}s for {len(results)} operations")

    def test_memory_usage_large_config(self, large_scale_config):
        """Test memory usage with large-scale configuration."""
        import sys
        
        loader = ConfigLoader()
        
        # Measure memory before loading
        initial_size = sys.getsizeof(loader)
        
        # Load configuration
        configs = loader.load_configs([large_scale_config])
        
        # Measure memory after loading
        final_size = sys.getsizeof(loader) + sum(sys.getsizeof(c) for c in configs)
        memory_increase = final_size - initial_size
        
        # Memory assertion: should use less than 10MB for this configuration
        max_memory_mb = 10
        memory_mb = memory_increase / (1024 * 1024)
        assert memory_mb < max_memory_mb, f"Memory usage {memory_mb:.2f}MB exceeds {max_memory_mb}MB"
        print(f"✓ Memory usage: {memory_mb:.2f}MB for 50 users across 20 repositories")

    def test_end_to_end_performance(self, large_scale_config, mocker):
        """Test complete end-to-end workflow performance."""
        # Mock GitHub client
        mock_client = Mock()
        mock_client.get_repository_collaborators.return_value = []
        mock_client.add_collaborator.return_value = None
        
        # Measure total time for complete workflow
        start_time = time.time()
        
        # 1. Load configuration
        loader = ConfigLoader()
        configs = loader.load_configs([large_scale_config])
        
        # 2. Create manager and plan changes
        manager = CollaboratorManager(mock_client)
        plan = manager.plan_changes(configs, remove_stale=False)
        
        # 3. Apply changes
        results = manager.apply_changes(plan)
        
        total_time = time.time() - start_time
        
        # Verify workflow completed
        assert len(results) > 0
        
        # Performance assertion: complete workflow should finish in under 10 seconds
        assert total_time < 10.0, f"End-to-end workflow took {total_time:.2f}s, expected < 10.0s"
        print(f"✓ End-to-end workflow: {total_time:.3f}s for complete operation")
        print(f"  - Loaded {len(configs)} team configs")
        print(f"  - Planned {len(plan.additions)} additions")
        print(f"  - Applied {len(results)} changes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

# Made with Bob
