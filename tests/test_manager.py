"""Tests for CollaboratorManager module"""

import pytest
from unittest.mock import Mock, MagicMock
from github.Repository import Repository

from src.github_collab_manager.manager import CollaboratorManager
from src.github_collab_manager.models import TeamConfig, AccessGrant, OperationResult
from src.github_collab_manager.github_client import GitHubClient
from src.github_collab_manager.audit_logger import AuditLogger


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return Mock(spec=GitHubClient)


@pytest.fixture
def mock_logger():
    """Create a mock audit logger."""
    return Mock(spec=AuditLogger)


@pytest.fixture
def manager(mock_github_client, mock_logger):
    """Create a CollaboratorManager instance."""
    return CollaboratorManager(mock_github_client, mock_logger)


@pytest.fixture
def sample_team_configs():
    """Create sample team configurations for testing."""
    return [
        TeamConfig(
            team_name="backend-team",
            users=["alice", "bob"],
            roles={
                "push": ["api-service", "data-processor"],
                "pull": ["frontend-app"]
            },
            source_file="backend-team.yaml"
        ),
        TeamConfig(
            team_name="frontend-team",
            users=["charlie", "diana"],
            roles={
                "push": ["frontend-app"],
                "pull": ["api-service"]
            },
            source_file="frontend-team.yaml"
        )
    ]


class TestProcessTeamConfigs:
    """Tests for process_team_configs method."""
    
    def test_process_single_team(self, manager):
        """Test processing a single team configuration."""
        team_config = TeamConfig(
            team_name="test-team",
            users=["user1", "user2"],
            roles={"push": ["repo1", "repo2"]},
            source_file="test.yaml"
        )
        
        result = manager.process_team_configs([team_config])
        
        assert "repo1" in result
        assert "repo2" in result
        assert result["repo1"] == {"user1": "push", "user2": "push"}
        assert result["repo2"] == {"user1": "push", "user2": "push"}
    
    def test_process_multiple_teams(self, manager, sample_team_configs):
        """Test processing multiple team configurations."""
        result = manager.process_team_configs(sample_team_configs)
        
        # Check api-service has users from both teams
        assert "api-service" in result
        assert result["api-service"]["alice"] == "push"
        assert result["api-service"]["bob"] == "push"
        assert result["api-service"]["charlie"] == "pull"
        assert result["api-service"]["diana"] == "pull"
        
        # Check frontend-app
        assert "frontend-app" in result
        assert result["frontend-app"]["alice"] == "pull"
        assert result["frontend-app"]["bob"] == "pull"
        assert result["frontend-app"]["charlie"] == "push"
        assert result["frontend-app"]["diana"] == "push"
    
    def test_conflict_resolution_alphabetical(self, manager):
        """Test conflict resolution uses alphabetical file order (last wins)."""
        team_configs = [
            TeamConfig(
                team_name="team-a",
                users=["user1"],
                roles={"pull": ["repo1"]},
                source_file="a-team.yaml"  # Alphabetically first
            ),
            TeamConfig(
                team_name="team-b",
                users=["user1"],
                roles={"push": ["repo1"]},
                source_file="b-team.yaml"  # Alphabetically second (wins)
            )
        ]
        
        result = manager.process_team_configs(team_configs)
        
        # Last file alphabetically wins
        assert result["repo1"]["user1"] == "push"
    
    def test_empty_team_configs(self, manager):
        """Test processing empty team configurations."""
        result = manager.process_team_configs([])
        
        assert result == {}
    
    def test_team_with_multiple_roles(self, manager):
        """Test team with users having multiple roles."""
        team_config = TeamConfig(
            team_name="multi-role-team",
            users=["user1"],
            roles={
                "push": ["repo1"],
                "admin": ["repo2"],
                "pull": ["repo3"]
            },
            source_file="multi.yaml"
        )
        
        result = manager.process_team_configs([team_config])
        
        assert result["repo1"]["user1"] == "push"
        assert result["repo2"]["user1"] == "admin"
        assert result["repo3"]["user1"] == "pull"


class TestDetectChanges:
    """Tests for detect_changes method."""
    
    def test_detect_additions(self, manager, mock_github_client):
        """Test detecting new collaborators to add."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {}
        
        desired_access = {"user1": "push", "user2": "admin"}
        
        additions, updates, no_ops = manager.detect_changes("test-repo", desired_access)
        
        assert len(additions) == 2
        assert ("user1", "push") in additions
        assert ("user2", "admin") in additions
        assert len(updates) == 0
        assert len(no_ops) == 0
    
    def test_detect_updates(self, manager, mock_github_client):
        """Test detecting permission updates."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {
            "user1": "pull",
            "user2": "push"
        }
        
        desired_access = {"user1": "push", "user2": "admin"}
        
        additions, updates, no_ops = manager.detect_changes("test-repo", desired_access)
        
        assert len(additions) == 0
        assert len(updates) == 2
        assert ("user1", "push") in updates
        assert ("user2", "admin") in updates
        assert len(no_ops) == 0
    
    def test_detect_no_ops(self, manager, mock_github_client):
        """Test detecting unchanged permissions."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {
            "user1": "push",
            "user2": "admin"
        }
        
        desired_access = {"user1": "push", "user2": "admin"}
        
        additions, updates, no_ops = manager.detect_changes("test-repo", desired_access)
        
        assert len(additions) == 0
        assert len(updates) == 0
        assert len(no_ops) == 2
        assert "user1" in no_ops
        assert "user2" in no_ops
    
    def test_detect_mixed_changes(self, manager, mock_github_client):
        """Test detecting mixed additions, updates, and no-ops."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {
            "user1": "pull",
            "user2": "push"
        }
        
        desired_access = {
            "user1": "push",    # Update
            "user2": "push",    # No-op
            "user3": "admin"    # Addition
        }
        
        additions, updates, no_ops = manager.detect_changes("test-repo", desired_access)
        
        assert len(additions) == 1
        assert ("user3", "admin") in additions
        assert len(updates) == 1
        assert ("user1", "push") in updates
        assert len(no_ops) == 1
        assert "user2" in no_ops
    
    def test_repository_not_found(self, manager, mock_github_client, mock_logger):
        """Test handling repository not found."""
        mock_github_client.get_repository.return_value = None
        
        desired_access = {"user1": "push"}
        
        additions, updates, no_ops = manager.detect_changes("nonexistent", desired_access)
        
        assert len(additions) == 0
        assert len(updates) == 0
        assert len(no_ops) == 0
        mock_logger.log_error.assert_called_once()


class TestApplyAccessGrants:
    """Tests for apply_access_grants method."""
    
    def test_apply_additions(self, manager, mock_github_client):
        """Test applying new collaborator additions."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {}
        mock_github_client.add_collaborator.return_value = OperationResult(
            success=True,
            action="add_collaborator",
            user="user1",
            repository="repo1",
            role="push",
            message="Added successfully"
        )
        
        repo_access = {"repo1": {"user1": "push"}}
        
        results = manager.apply_access_grants(repo_access, dry_run=False)
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].action == "add_collaborator"
        mock_github_client.add_collaborator.assert_called_once()
    
    def test_apply_updates(self, manager, mock_github_client):
        """Test applying permission updates."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {"user1": "pull"}
        mock_github_client.update_collaborator.return_value = OperationResult(
            success=True,
            action="update_collaborator",
            user="user1",
            repository="repo1",
            role="push",
            message="Updated successfully"
        )
        
        repo_access = {"repo1": {"user1": "push"}}
        
        results = manager.apply_access_grants(repo_access, dry_run=False)
        
        assert len(results) == 1
        assert results[0].action == "update_collaborator"
        mock_github_client.update_collaborator.assert_called_once()
    
    def test_dry_run_mode(self, manager, mock_github_client, mock_logger):
        """Test dry-run mode doesn't apply changes."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {}
        
        repo_access = {"repo1": {"user1": "push", "user2": "admin"}}
        
        results = manager.apply_access_grants(repo_access, dry_run=True)
        
        # In dry-run, no actual API calls should be made
        mock_github_client.add_collaborator.assert_not_called()
        mock_github_client.update_collaborator.assert_not_called()
        
        # Should log the planned changes
        assert mock_logger.log_info.call_count >= 2
    
    def test_skip_no_ops(self, manager, mock_github_client, mock_logger):
        """Test skipping unchanged permissions."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {"user1": "push"}
        
        repo_access = {"repo1": {"user1": "push"}}
        
        results = manager.apply_access_grants(repo_access, dry_run=False)
        
        # No operations should be performed for no-ops
        mock_github_client.add_collaborator.assert_not_called()
        mock_github_client.update_collaborator.assert_not_called()
        
        # Should log the skip
        mock_logger.log_info.assert_called()
    
    def test_handle_api_errors(self, manager, mock_github_client, mock_logger):
        """Test handling API errors during apply."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {}
        mock_github_client.add_collaborator.return_value = OperationResult(
            success=False,
            action="add_collaborator",
            user="user1",
            repository="repo1",
            role="push",
            message="API error",
            error=Exception("API failed")
        )
        
        repo_access = {"repo1": {"user1": "push"}}
        
        results = manager.apply_access_grants(repo_access, dry_run=False)
        
        assert len(results) == 1
        assert results[0].success is False
        mock_logger.log_error.assert_called()
    
    def test_multiple_repositories(self, manager, mock_github_client):
        """Test applying changes across multiple repositories."""
        mock_repo1 = Mock(spec=Repository)
        mock_repo2 = Mock(spec=Repository)
        
        def get_repo_side_effect(repo_name):
            if repo_name == "repo1":
                return mock_repo1
            elif repo_name == "repo2":
                return mock_repo2
            return None
        
        mock_github_client.get_repository.side_effect = get_repo_side_effect
        mock_github_client.list_collaborators.return_value = {}
        mock_github_client.add_collaborator.return_value = OperationResult(
            success=True,
            action="add_collaborator",
            user="user1",
            repository="repo",
            role="push"
        )
        
        repo_access = {
            "repo1": {"user1": "push"},
            "repo2": {"user2": "admin"}
        }
        
        results = manager.apply_access_grants(repo_access, dry_run=False)
        
        assert len(results) == 2
        assert mock_github_client.add_collaborator.call_count == 2


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_workflow(self, manager, mock_github_client, sample_team_configs):
        """Test complete workflow from configs to applied changes."""
        # Setup mocks
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = {}
        mock_github_client.add_collaborator.return_value = OperationResult(
            success=True,
            action="add_collaborator",
            user="user",
            repository="repo",
            role="push"
        )
        
        # Process configs
        repo_access = manager.process_team_configs(sample_team_configs)
        
        # Apply changes
        results = manager.apply_access_grants(repo_access, dry_run=False)
        
        # Verify results
        assert len(results) > 0
        assert all(r.success for r in results)


class TestStaleCollaboratorDetection:
    """Tests for stale collaborator detection."""
    
    def test_detect_stale_collaborators(self, manager, mock_github_client, mock_logger):
        """Test detection of stale collaborators."""
        # Setup: repo has alice, bob, charlie but config only has alice, bob
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        
        # Current collaborators
        alice = Mock(login='alice')
        bob = Mock(login='bob')
        charlie = Mock(login='charlie')  # Stale
        mock_github_client.list_collaborators.return_value = [alice, bob, charlie]
        
        # Mock org members (empty - charlie is not an org member)
        mock_org = Mock()
        mock_org.get_members.return_value = []
        mock_github_client._org = mock_org
        
        # Desired access (alice and bob only)
        repo_access = {
            'repo1': {'alice': 'push', 'bob': 'pull'}
        }
        
        stale = manager.detect_stale_collaborators(repo_access)
        
        assert 'repo1' in stale
        assert stale['repo1'] == ['charlie']
    
    def test_detect_stale_collaborators_filters_org_members(self, manager, mock_github_client, mock_logger):
        """Test that organization members are filtered out from stale detection."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        
        # Current collaborators
        alice = Mock(login='alice')
        bob = Mock(login='bob')
        charlie = Mock(login='charlie')  # Stale but org member
        mock_github_client.list_collaborators.return_value = [alice, bob, charlie]
        
        # Mock org members (charlie is an org member)
        mock_org = Mock()
        charlie_member = Mock(login='charlie')
        mock_org.get_members.return_value = [charlie_member]
        mock_github_client._org = mock_org
        
        # Desired access (alice and bob only)
        repo_access = {
            'repo1': {'alice': 'push', 'bob': 'pull'}
        }
        
        stale = manager.detect_stale_collaborators(repo_access)
        
        # Charlie should be filtered out as org member
        assert 'repo1' not in stale or stale['repo1'] == []
    
    def test_detect_stale_collaborators_no_stale(self, manager, mock_github_client, mock_logger):
        """Test when there are no stale collaborators."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        
        # Current collaborators match desired
        alice = Mock(login='alice')
        bob = Mock(login='bob')
        mock_github_client.list_collaborators.return_value = [alice, bob]
        
        mock_org = Mock()
        mock_org.get_members.return_value = []
        mock_github_client._org = mock_org
        
        repo_access = {
            'repo1': {'alice': 'push', 'bob': 'pull'}
        }
        
        stale = manager.detect_stale_collaborators(repo_access)
        
        assert stale == {}
    
    def test_detect_stale_collaborators_repo_not_found(self, manager, mock_github_client, mock_logger):
        """Test stale detection when repository doesn't exist."""
        mock_github_client.get_repository.return_value = None
        
        repo_access = {
            'nonexistent-repo': {'alice': 'push'}
        }
        
        stale = manager.detect_stale_collaborators(repo_access)
        
        assert stale == {}
    
    def test_detect_stale_collaborators_list_fails(self, manager, mock_github_client, mock_logger):
        """Test stale detection when listing collaborators fails."""
        mock_repo = Mock(spec=Repository)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.list_collaborators.return_value = None
        
        repo_access = {
            'repo1': {'alice': 'push'}
        }
        
        stale = manager.detect_stale_collaborators(repo_access)
        
        assert stale == {}


class TestStaleCollaboratorRemoval:
    """Tests for stale collaborator removal."""
    
    def test_remove_stale_collaborators(self, manager, mock_github_client, mock_logger):
        """Test removal of stale collaborators."""
        mock_github_client.remove_collaborator.return_value = True
        
        stale_collaborators = {
            'repo1': ['charlie', 'dave'],
            'repo2': ['eve']
        }
        
        results = manager.remove_stale_collaborators(stale_collaborators, dry_run=False)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.action == 'remove_collaborator' for r in results)
        
        # Verify remove_collaborator was called for each stale user
        assert mock_github_client.remove_collaborator.call_count == 3
        mock_github_client.remove_collaborator.assert_any_call('repo1', 'charlie')
        mock_github_client.remove_collaborator.assert_any_call('repo1', 'dave')
        mock_github_client.remove_collaborator.assert_any_call('repo2', 'eve')
    
    def test_remove_stale_collaborators_dry_run(self, manager, mock_github_client, mock_logger):
        """Test dry-run mode for stale collaborator removal."""
        stale_collaborators = {
            'repo1': ['charlie'],
            'repo2': ['dave']
        }
        
        results = manager.remove_stale_collaborators(stale_collaborators, dry_run=True)
        
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.action == 'remove_collaborator' for r in results)
        
        # In dry-run, no actual API calls should be made
        mock_github_client.remove_collaborator.assert_not_called()
    
    def test_remove_stale_collaborators_failure(self, manager, mock_github_client, mock_logger):
        """Test handling of removal failures."""
        # First removal succeeds, second fails
        mock_github_client.remove_collaborator.side_effect = [True, False]
        
        stale_collaborators = {
            'repo1': ['charlie', 'dave']
        }
        
        results = manager.remove_stale_collaborators(stale_collaborators, dry_run=False)
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
    
    def test_remove_stale_collaborators_empty(self, manager, mock_github_client, mock_logger):
        """Test removal with no stale collaborators."""
        stale_collaborators = {}
        
        results = manager.remove_stale_collaborators(stale_collaborators, dry_run=False)
        
        assert results == []
        mock_github_client.remove_collaborator.assert_not_called()


class TestProjectAccessIntegration:
    """Integration tests for project access management."""
    
    def test_apply_project_access_org_projects(self, mock_github_client, mock_logger):
        """Test applying project access for organization projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        # Create mock projects client
        mock_projects_client = Mock(spec=ProjectsClient)
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Sprint Board', 'url': 'url1', 'closed': False}
        ]
        mock_projects_client.get_user_id.return_value = 'user_node_id'
        mock_projects_client.update_project_collaborator.return_value = True
        
        # Create manager with projects client
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        # Create team config with project access
        team_configs = [
            TeamConfig(
                team_name="test-team",
                users=["alice", "bob"],
                roles={},
                projects=[
                    ProjectConfig(number=1, permission=ProjectPermission.WRITE)
                ],
                source_file="test.yaml"
            )
        ]
        
        # Apply project access
        errors = manager.apply_project_access(team_configs, "test-org", dry_run=False)
        
        # Verify no errors
        assert errors == []
        
        # Verify projects client was called correctly
        mock_projects_client.list_organization_projects.assert_called_once_with("test-org")
        assert mock_projects_client.get_user_id.call_count == 2  # alice and bob
        assert mock_projects_client.update_project_collaborator.call_count == 2
    
    def test_apply_project_access_repo_projects(self, mock_github_client, mock_logger):
        """Test applying project access for repository projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        mock_projects_client.list_repository_projects.return_value = [
            {'id': 'proj_2', 'number': 5, 'title': 'Repo Board', 'url': 'url2', 'closed': False}
        ]
        mock_projects_client.get_user_id.return_value = 'user_node_id'
        mock_projects_client.update_project_collaborator.return_value = True
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="repo-team",
                users=["charlie"],
                roles={},
                projects=[
                    ProjectConfig(number=5, permission=ProjectPermission.READ, repository="my-repo")
                ],
                source_file="repo-team.yaml"
            )
        ]
        
        errors = manager.apply_project_access(team_configs, "test-org", dry_run=False)
        
        assert errors == []
        mock_projects_client.list_repository_projects.assert_called_once_with("test-org", "my-repo")
        mock_projects_client.get_user_id.assert_called_once_with("charlie")
        mock_projects_client.update_project_collaborator.assert_called_once()
    
    def test_apply_project_access_dry_run(self, mock_github_client, mock_logger):
        """Test dry-run mode for project access."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        mock_projects_client.get_user_id.return_value = 'user_id'
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["user1"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.ADMIN)],
                source_file="team.yaml"
            )
        ]
        
        errors = manager.apply_project_access(team_configs, "org", dry_run=True)
        
        assert errors == []
        # In dry-run, should not call update_project_collaborator
        mock_projects_client.update_project_collaborator.assert_not_called()
        # But should still validate projects exist
        mock_projects_client.list_organization_projects.assert_called_once()
    
    def test_apply_project_access_handles_errors(self, mock_github_client, mock_logger):
        """Test error handling in project access workflow."""
        from src.github_collab_manager.projects_client import ProjectsClient, GraphQLError, GraphQLErrorCategory
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        # User not found error
        mock_projects_client.get_user_id.side_effect = GraphQLError(
            "User not found",
            GraphQLErrorCategory.NOT_FOUND,
            Exception("not found")
        )
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["nonexistent"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.WRITE)],
                source_file="team.yaml"
            )
        ]
        
        errors = manager.apply_project_access(team_configs, "org", dry_run=False)
        
        # Should collect error but not crash
        assert len(errors) > 0
        assert "nonexistent" in errors[0] or "not found" in errors[0].lower()
    
    def test_apply_project_access_mixed_org_and_repo(self, mock_github_client, mock_logger):
        """Test applying access to both org and repo projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'org_proj', 'number': 1, 'title': 'Org Board', 'url': 'url1', 'closed': False}
        ]
        mock_projects_client.list_repository_projects.return_value = [
            {'id': 'repo_proj', 'number': 2, 'title': 'Repo Board', 'url': 'url2', 'closed': False}
        ]
        mock_projects_client.get_user_id.return_value = 'user_id'
        mock_projects_client.update_project_collaborator.return_value = True
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="mixed-team",
                users=["user1"],
                roles={},
                projects=[
                    ProjectConfig(number=1, permission=ProjectPermission.WRITE),  # Org project
                    ProjectConfig(number=2, permission=ProjectPermission.READ, repository="repo1")  # Repo project
                ],
                source_file="mixed.yaml"
            )
        ]
        
        errors = manager.apply_project_access(team_configs, "org", dry_run=False)
        
        assert errors == []
        mock_projects_client.list_organization_projects.assert_called_once()
        mock_projects_client.list_repository_projects.assert_called_once()
        # Should grant access to both projects
        assert mock_projects_client.update_project_collaborator.call_count == 2
    
    def test_apply_project_access_project_not_found(self, mock_github_client, mock_logger):
        """Test handling when project doesn't exist."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        # Project 999 doesn't exist
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["user1"],
                roles={},
                projects=[
                    ProjectConfig(number=999, permission=ProjectPermission.WRITE)  # Doesn't exist
                ],
                source_file="team.yaml"
            )
        ]
        
        errors = manager.apply_project_access(team_configs, "org", dry_run=False)
        
        # Should report error for nonexistent project
        assert len(errors) > 0
        assert "999" in errors[0] or "not found" in errors[0].lower()
        # Should not attempt to grant access
        mock_projects_client.update_project_collaborator.assert_not_called()


class TestStaleProjectCollaborators:
    """Tests for stale project collaborator detection and removal."""
    
    def test_detect_stale_project_collaborators_org_projects(self, mock_github_client, mock_logger):
        """Test detecting stale collaborators on organization projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock organization projects
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board 1', 'url': 'url1', 'closed': False},
            {'id': 'proj_2', 'number': 2, 'title': 'Board 2', 'url': 'url2', 'closed': False}
        ]
        
        # Mock current collaborators - user3 is stale (not in team configs)
        mock_projects_client.get_project_collaborators.side_effect = [
            [{'login': 'user1'}, {'login': 'user3'}],  # Project 1
            [{'login': 'user2'}, {'login': 'user3'}]   # Project 2
        ]
        
        # Mock org membership check - user3 is NOT an org member
        mock_org = Mock()
        mock_member1 = Mock()
        mock_member1.login = 'user1'
        mock_member2 = Mock()
        mock_member2.login = 'user2'
        mock_org.get_members.return_value = [mock_member1, mock_member2]
        mock_github_client._org = mock_org
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team1",
                users=["user1"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.WRITE)],
                source_file="team1.yaml"
            ),
            TeamConfig(
                team_name="team2",
                users=["user2"],
                roles={},
                projects=[ProjectConfig(number=2, permission=ProjectPermission.READ)],
                source_file="team2.yaml"
            )
        ]
        
        stale = manager.detect_stale_project_collaborators(team_configs, "test-org")
        
        # Should detect user3 as stale on both projects
        assert "org:1" in stale
        assert "user3" in stale["org:1"]
        assert "org:2" in stale
        assert "user3" in stale["org:2"]
    
    def test_detect_stale_project_collaborators_repo_projects(self, mock_github_client, mock_logger):
        """Test detecting stale collaborators on repository projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock repository projects
        mock_projects_client.list_repository_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Repo Board', 'url': 'url', 'closed': False}
        ]
        
        # Mock current collaborators
        mock_projects_client.get_project_collaborators.return_value = [
            {'login': 'user1'},
            {'login': 'stale_user'}
        ]
        
        # Mock org membership check
        mock_org = Mock()
        mock_member = Mock()
        mock_member.login = 'user1'
        mock_org.get_members.return_value = [mock_member]
        mock_github_client._org = mock_org
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["user1"],
                roles={},
                projects=[
                    ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository="my-repo")
                ],
                source_file="team.yaml"
            )
        ]
        
        stale = manager.detect_stale_project_collaborators(team_configs, "test-org")
        
        # Should detect stale_user on repo project
        assert "repo:my-repo:1" in stale
        assert "stale_user" in stale["repo:my-repo:1"]
        assert "user1" not in stale["repo:my-repo:1"]
    
    def test_detect_stale_project_collaborators_filters_org_members(self, mock_github_client, mock_logger):
        """Test that organization members are filtered out from stale detection."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        # Mock collaborators - org_member is an org member, outside_collab is not
        mock_projects_client.get_project_collaborators.return_value = [
            {'login': 'user1'},
            {'login': 'org_member'},
            {'login': 'outside_collab'}
        ]
        
        # org_member is an org member, others are not
        mock_org = Mock()
        mock_member1 = Mock()
        mock_member1.login = 'user1'
        mock_member2 = Mock()
        mock_member2.login = 'org_member'
        mock_org.get_members.return_value = [mock_member1, mock_member2]
        mock_github_client._org = mock_org
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["user1"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.WRITE)],
                source_file="team.yaml"
            )
        ]
        
        stale = manager.detect_stale_project_collaborators(team_configs, "test-org")
        
        # Should only detect outside_collab as stale (org_member filtered out)
        assert "org:1" in stale
        assert "outside_collab" in stale["org:1"]
        assert "org_member" not in stale["org:1"]
        assert "user1" not in stale["org:1"]
    
    def test_detect_stale_project_collaborators_no_stale(self, mock_github_client, mock_logger):
        """Test when there are no stale collaborators."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        # All current collaborators are in team configs
        mock_projects_client.get_project_collaborators.return_value = [
            {'login': 'user1'},
            {'login': 'user2'}
        ]
        
        # Mock org with no members (all are outside collaborators)
        mock_org = Mock()
        mock_org.get_members.return_value = []
        mock_github_client._org = mock_org
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["user1", "user2"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.WRITE)],
                source_file="team.yaml"
            )
        ]
        
        stale = manager.detect_stale_project_collaborators(team_configs, "test-org")
        
        # Should return empty dict
        assert len(stale) == 0
    
    def test_detect_stale_project_collaborators_mixed_projects(self, mock_github_client, mock_logger):
        """Test detecting stale collaborators across org and repo projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock both org and repo projects
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Org Board', 'url': 'url1', 'closed': False}
        ]
        mock_projects_client.list_repository_projects.return_value = [
            {'id': 'proj_2', 'number': 2, 'title': 'Repo Board', 'url': 'url2', 'closed': False}
        ]
        
        # Mock collaborators
        mock_projects_client.get_project_collaborators.side_effect = [
            [{'login': 'user1'}, {'login': 'stale1'}],  # Org project
            [{'login': 'user2'}, {'login': 'stale2'}]   # Repo project
        ]
        
        # Mock org with no members
        mock_org = Mock()
        mock_org.get_members.return_value = []
        mock_github_client._org = mock_org
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        team_configs = [
            TeamConfig(
                team_name="team",
                users=["user1", "user2"],
                roles={},
                projects=[
                    ProjectConfig(number=1, permission=ProjectPermission.WRITE),
                    ProjectConfig(number=2, permission=ProjectPermission.READ, repository="repo")
                ],
                source_file="team.yaml"
            )
        ]
        
        stale = manager.detect_stale_project_collaborators(team_configs, "test-org")
        
        # Should detect stale users on both project types
        assert "org:1" in stale
        assert "stale1" in stale["org:1"]
        assert "repo:repo:2" in stale
        assert "stale2" in stale["repo:repo:2"]
    
    def test_remove_stale_project_collaborators_dry_run(self, mock_github_client, mock_logger):
        """Test removing stale project collaborators in dry-run mode."""
        from src.github_collab_manager.projects_client import ProjectsClient
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock project details
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        stale_collaborators = {
            "org:1": ["stale_user1", "stale_user2"]
        }
        
        errors = manager.remove_stale_project_collaborators(
            stale_collaborators,
            "test-org",
            dry_run=True
        )
        
        # Should not actually remove in dry-run mode
        mock_projects_client.remove_project_collaborator.assert_not_called()
        
        # Should log dry-run actions
        assert mock_logger.log_info.call_count >= 2
        
        # Should return no errors
        assert len(errors) == 0
    
    def test_remove_stale_project_collaborators_actual_removal(self, mock_github_client, mock_logger):
        """Test actually removing stale project collaborators."""
        from src.github_collab_manager.projects_client import ProjectsClient
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock project details
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        # Mock get_user_id to return a user ID
        mock_projects_client.get_user_id.return_value = 'user_id_123'
        
        # Mock successful removal
        mock_projects_client.remove_project_collaborator.return_value = None
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        stale_collaborators = {
            "org:1": ["stale_user"]
        }
        
        errors = manager.remove_stale_project_collaborators(
            stale_collaborators,
            "test-org",
            dry_run=False
        )
        
        # Should get user ID
        mock_projects_client.get_user_id.assert_called_once_with('stale_user')
        
        # Should actually remove with user ID
        mock_projects_client.remove_project_collaborator.assert_called_once_with(
            'proj_1',
            'user_id_123'
        )
        
        # Should log removal
        mock_logger.log_project_operation.assert_called()
        
        # Should return no errors
        assert len(errors) == 0
    
    def test_remove_stale_project_collaborators_handles_errors(self, mock_github_client, mock_logger):
        """Test error handling when removal fails."""
        from src.github_collab_manager.projects_client import ProjectsClient
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock project details
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        # Mock get_user_id
        mock_projects_client.get_user_id.return_value = 'user_id_123'
        
        # Mock removal failure
        mock_projects_client.remove_project_collaborator.side_effect = Exception("API error")
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        stale_collaborators = {
            "org:1": ["stale_user"]
        }
        
        errors = manager.remove_stale_project_collaborators(
            stale_collaborators,
            "test-org",
            dry_run=False
        )
        
        # Should return error message
        assert len(errors) == 1
        assert "stale_user" in errors[0]
        assert "#1" in errors[0]  # Project number should be in error
    
    def test_remove_stale_project_collaborators_repo_projects(self, mock_github_client, mock_logger):
        """Test removing stale collaborators from repository projects."""
        from src.github_collab_manager.projects_client import ProjectsClient
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Mock repository project details
        mock_projects_client.list_repository_projects.return_value = [
            {'id': 'proj_1', 'number': 5, 'title': 'Repo Board', 'url': 'url', 'closed': False}
        ]
        
        mock_projects_client.remove_project_collaborator.return_value = None
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        stale_collaborators = {
            "repo:my-repo:5": ["stale_user"]
        }
        
        errors = manager.remove_stale_project_collaborators(
            stale_collaborators,
            "test-org",
            dry_run=False
        )
        
        # Should call list_repository_projects with correct repo name
        mock_projects_client.list_repository_projects.assert_called_with("test-org", "my-repo")
        
        # Should remove collaborator
        mock_projects_client.remove_project_collaborator.assert_called_once()
        
        assert len(errors) == 0
    
    def test_remove_stale_project_collaborators_project_not_found(self, mock_github_client, mock_logger):
        """Test handling when project doesn't exist during removal."""
        from src.github_collab_manager.projects_client import ProjectsClient
        
        mock_projects_client = Mock(spec=ProjectsClient)
        
        # Project 999 doesn't exist
        mock_projects_client.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Board', 'url': 'url', 'closed': False}
        ]
        
        manager = CollaboratorManager(mock_github_client, mock_logger, mock_projects_client)
        
        stale_collaborators = {
            "org:999": ["stale_user"]  # Project doesn't exist
        }
        
        errors = manager.remove_stale_project_collaborators(
            stale_collaborators,
            "test-org",
            dry_run=False
        )
        
        # Should return error for nonexistent project
        assert len(errors) == 1
        assert "999" in errors[0]
        assert "not found" in errors[0].lower()
        
        # Should not attempt removal
        mock_projects_client.remove_project_collaborator.assert_not_called()


# Made with Bob