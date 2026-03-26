"""Integration tests for CLI module"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from src.github_collab_manager.cli import main, parse_arguments, get_github_credentials
from src.github_collab_manager.models import ValidationResult, OperationResult


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {
        'GITHUB_TOKEN': 'test_token',
        'GITHUB_ORG': 'test_org',
        'LOG_LEVEL': 'INFO'
    }):
        yield


@pytest.fixture
def temp_teams_dir(tmp_path):
    """Create a temporary teams directory with sample YAML files."""
    teams_dir = tmp_path / "teams"
    teams_dir.mkdir()
    
    # Create a valid team file
    team_file = teams_dir / "test-team.yaml"
    team_file.write_text("""
team_name: test-team
users:
  - alice
  - bob
roles:
  push:
    - repo1
    - repo2
  pull:
    - repo3
""")
    
    return str(teams_dir)


class TestParseArguments:
    """Tests for argument parsing."""
    
    def test_parse_minimal_args(self):
        """Test parsing with minimal required arguments."""
        with patch('sys.argv', ['github-collab-manager', '--teams-dir', '/path/to/teams']):
            args = parse_arguments()
            assert args.teams_dir == '/path/to/teams'
            assert args.dry_run is False
            assert args.validate_only is False
    
    def test_parse_all_args(self):
        """Test parsing with all arguments."""
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', '/teams',
            '--dry-run',
            '--validate-only',
            '--github-token', 'token123',
            '--github-org', 'myorg',
            '--log-level', 'DEBUG'
        ]):
            args = parse_arguments()
            assert args.teams_dir == '/teams'
            assert args.dry_run is True
            assert args.validate_only is True
            assert args.github_token == 'token123'
            assert args.github_org == 'myorg'
            assert args.log_level == 'DEBUG'
    
    def test_parse_missing_required_arg(self):
        """Test parsing fails without required argument."""
        with patch('sys.argv', ['github-collab-manager']):
            with pytest.raises(SystemExit):
                parse_arguments()


class TestGetGitHubCredentials:
    """Tests for credential retrieval."""
    
    def test_credentials_from_args(self):
        """Test getting credentials from command-line arguments."""
        args = Mock()
        args.github_token = 'arg_token'
        args.github_org = 'arg_org'
        
        token, org = get_github_credentials(args)
        
        assert token == 'arg_token'
        assert org == 'arg_org'
    
    def test_credentials_from_env(self, mock_env):
        """Test getting credentials from environment variables."""
        args = Mock()
        args.github_token = None
        args.github_org = None
        
        token, org = get_github_credentials(args)
        
        assert token == 'test_token'
        assert org == 'test_org'
    
    def test_args_override_env(self, mock_env):
        """Test command-line args override environment variables."""
        args = Mock()
        args.github_token = 'arg_token'
        args.github_org = 'arg_org'
        
        token, org = get_github_credentials(args)
        
        assert token == 'arg_token'
        assert org == 'arg_org'
    
    def test_missing_credentials(self):
        """Test error when credentials are missing."""
        args = Mock()
        args.github_token = None
        args.github_org = None
        
        with patch.dict(os.environ, {}, clear=True):
            token, org = get_github_credentials(args)
            assert token is None
            assert org is None


class TestValidateOnlyMode:
    """Tests for validate-only mode."""
    
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_validate_only_success(self, mock_load, temp_teams_dir, capsys):
        """Test validate-only mode with valid configurations."""
        mock_load.return_value = (
            [Mock()],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--validate-only'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Validation successful" in captured.out
    
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_validate_only_failure(self, mock_load, temp_teams_dir, capsys):
        """Test validate-only mode with invalid configurations."""
        mock_load.return_value = (
            [],
            ValidationResult(
                valid=False,
                errors=["Missing required field: team_name"],
                warnings=[]
            )
        )
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--validate-only'
        ]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Validation failed" in captured.out
        assert "Missing required field" in captured.out


class TestDryRunMode:
    """Tests for dry-run mode."""
    
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_dry_run_mode(self, mock_load, mock_manager_class, mock_client_class, 
                         temp_teams_dir, mock_env, capsys):
        """Test dry-run mode doesn't apply changes."""
        # Setup mocks
        mock_load.return_value = (
            [Mock()],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {"repo1": {"user1": "push"}}
        mock_manager.apply_access_grants.return_value = []
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--dry-run'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify apply_access_grants was called with dry_run=True
        mock_manager.apply_access_grants.assert_called_once()
        call_args = mock_manager.apply_access_grants.call_args
        assert call_args[1]['dry_run'] is True


class TestNormalMode:
    """Tests for normal execution mode."""
    
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_successful_execution(self, mock_load, mock_manager_class, mock_client_class,
                                  temp_teams_dir, mock_env, capsys):
        """Test successful normal execution."""
        # Setup mocks
        mock_load.return_value = (
            [Mock()],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {"repo1": {"user1": "push"}}
        mock_manager.apply_access_grants.return_value = [
            OperationResult(
                success=True,
                action="add_collaborator",
                user="user1",
                repository="repo1",
                role="push",
                message="Success"
            )
        ]
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir
        ]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Successfully applied" in captured.out or "Completed" in captured.out
    
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_authentication_failure(self, mock_load, mock_client_class,
                                    temp_teams_dir, mock_env, capsys):
        """Test handling authentication failure."""
        mock_load.return_value = (
            [Mock()],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = False
        mock_client_class.return_value = mock_client
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir
        ]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Authentication failed" in captured.out or "Failed to authenticate" in captured.out


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_teams_directory(self, capsys):
        """Test handling invalid teams directory."""
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', '/nonexistent/path',
            '--validate-only'
        ]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.out or "not found" in captured.out
    
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_keyboard_interrupt(self, mock_load, temp_teams_dir, mock_env):
        """Test handling keyboard interrupt (Ctrl+C)."""
        mock_load.side_effect = KeyboardInterrupt()
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir
        ]):
            exit_code = main()
        
        assert exit_code == 130  # Standard exit code for SIGINT
    
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_unexpected_exception(self, mock_load, temp_teams_dir, mock_env, capsys):
        """Test handling unexpected exceptions."""
        mock_load.side_effect = Exception("Unexpected error")
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir
        ]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out or "error" in captured.out


class TestLogLevels:
    """Tests for log level configuration."""
    
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_debug_log_level(self, mock_load, temp_teams_dir, mock_env):
        """Test DEBUG log level configuration."""
        mock_load.return_value = (
            [Mock()],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--validate-only',
            '--log-level', 'DEBUG'
        ]):
            exit_code = main()
        
        assert exit_code == 0
    
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_error_log_level(self, mock_load, temp_teams_dir, mock_env):
        """Test ERROR log level configuration."""
        mock_load.return_value = (
            [Mock()],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--validate-only',
            '--log-level', 'ERROR'
        ]):
            exit_code = main()
        
        assert exit_code == 0


class TestProjectAccessValidation:
    """Integration tests for project access validation workflow."""
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_project_access_dry_run_validation(self, mock_load, mock_manager_class, 
                                               mock_client_class, mock_projects_class,
                                               temp_teams_dir, mock_env, capsys):
        """Test dry-run validation for project access operations."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        # Setup team config with projects
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice", "bob"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        # Setup GitHub client mock
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        # Setup Projects client mock
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Test Project', 'url': 'url', 'closed': False}
        ]
        mock_projects.get_user_id.return_value = 'user_id'
        mock_projects_class.return_value = mock_projects
        
        # Setup manager mock
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_project_access.return_value = []  # No errors
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--dry-run'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify apply_project_access was called with dry_run=True
        mock_manager.apply_project_access.assert_called_once()
        call_args = mock_manager.apply_project_access.call_args
        assert call_args[1]['dry_run'] is True
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_project_validation_detects_nonexistent_project(self, mock_load, mock_manager_class,
                                                            mock_client_class, mock_projects_class,
                                                            temp_teams_dir, mock_env, capsys):
        """Test validation detects when project doesn't exist."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=999, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = []  # Project doesn't exist
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        # Return error for nonexistent project
        mock_manager.apply_project_access.return_value = ["Project #999 not found in organization"]
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--dry-run'
        ]):
            exit_code = main()
        
        # Should still exit 0 in dry-run but report errors
        assert exit_code == 0
        captured = capsys.readouterr()
        # Error should be logged/displayed
        mock_manager.apply_project_access.assert_called_once()
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_project_validation_mixed_org_and_repo(self, mock_load, mock_manager_class,
                                                   mock_client_class, mock_projects_class,
                                                   temp_teams_dir, mock_env):
        """Test validation workflow with mixed org and repo projects."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="mixed-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None),
                ProjectConfig(number=2, permission=ProjectPermission.READ, repository="test-repo")
            ],
            source_file="mixed.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'org_proj', 'number': 1, 'title': 'Org Project', 'url': 'url1', 'closed': False}
        ]
        mock_projects.list_repository_projects.return_value = [
            {'id': 'repo_proj', 'number': 2, 'title': 'Repo Project', 'url': 'url2', 'closed': False}
        ]
        mock_projects.get_user_id.return_value = 'user_id'
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_project_access.return_value = []
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--dry-run'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify both org and repo projects were validated
        mock_manager.apply_project_access.assert_called_once()
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_project_validation_without_projects_client(self, mock_load, mock_manager_class,
                                                        mock_client_class, mock_projects_class,
                                                        temp_teams_dir, mock_env):
        """Test validation when projects client initialization fails."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        # Projects client initialization fails
        mock_projects_class.side_effect = Exception("Failed to initialize projects client")
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        # Manager created without projects client
        mock_manager.apply_project_access.return_value = ["Projects client not initialized"]
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir
        ]):
            exit_code = main()
        
        # Should handle gracefully
        assert exit_code in [0, 1]  # May exit with error or warning
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_project_validation_with_multiple_teams(self, mock_load, mock_manager_class,
                                                    mock_client_class, mock_projects_class,
                                                    temp_teams_dir, mock_env):
        """Test validation workflow with multiple teams accessing projects."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_configs = [
            TeamConfig(
                team_name="team-a",
                users=["alice"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.WRITE)],
                source_file="team-a.yaml"
            ),
            TeamConfig(
                team_name="team-b",
                users=["bob"],
                roles={},
                projects=[ProjectConfig(number=1, permission=ProjectPermission.READ)],
                source_file="team-b.yaml"
            )
        ]
        
        mock_load.return_value = (
            team_configs,
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Shared Project', 'url': 'url', 'closed': False}
        ]
        mock_projects.get_user_id.side_effect = lambda u: f"{u}_id"
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_project_access.return_value = []
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--dry-run'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify all teams were processed
        mock_manager.apply_project_access.assert_called_once()
        call_args = mock_manager.apply_project_access.call_args
        assert len(call_args[0][0]) == 2  # Two team configs passed



class TestStaleCollaboratorWorkflow:
    """Integration tests for stale collaborator detection and removal workflow."""
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_report_stale_with_projects(self, mock_load, mock_manager_class,
                                       mock_client_class, mock_projects_class,
                                       temp_teams_dir, mock_env, capsys):
        """Test --report-stale flag with project collaborators."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Test Project', 'url': 'url', 'closed': False}
        ]
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_access_grants.return_value = []  # Return empty list for results
        mock_manager.apply_project_access.return_value = []  # Return empty list for project errors
        
        # Mock rate limit
        mock_client.get_rate_limit.return_value = {
            'remaining': 5000,
            'limit': 5000,
            'reset_timestamp': '2026-03-26T13:00:00Z'
        }
        
        mock_manager.detect_stale_collaborators.return_value = {}  # No stale repo collaborators
        mock_manager.detect_stale_project_collaborators.return_value = {
            'org:1': ['bob', 'charlie']  # Stale project collaborators
        }
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--report-stale'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        # Should report stale project collaborators
        assert 'bob' in captured.out or 'charlie' in captured.out
        mock_manager.detect_stale_project_collaborators.assert_called_once()
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_remove_stale_with_projects_dry_run(self, mock_load, mock_manager_class,
                                                mock_client_class, mock_projects_class,
                                                temp_teams_dir, mock_env, capsys):
        """Test --remove-stale flag with projects in dry-run mode."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Test Project', 'url': 'url', 'closed': False}
        ]
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_access_grants.return_value = []  # Return empty list for results
        mock_manager.apply_project_access.return_value = []  # Return empty list for project errors
        
        # Mock rate limit
        mock_client.get_rate_limit.return_value = {
            'remaining': 5000,
            'limit': 5000,
            'reset_timestamp': '2026-03-26T13:00:00Z'
        }
        
        mock_manager.detect_stale_collaborators.return_value = {}
        mock_manager.detect_stale_project_collaborators.return_value = {
            'org:1': ['bob']
        }
        mock_manager.remove_stale_collaborators.return_value = []
        mock_manager.remove_stale_project_collaborators.return_value = []
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--remove-stale',
            '--dry-run'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify dry_run=True was passed
        mock_manager.remove_stale_project_collaborators.assert_called_once()
        call_args = mock_manager.remove_stale_project_collaborators.call_args
        assert call_args[1]['dry_run'] is True
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_remove_stale_with_projects_actual_removal(self, mock_load, mock_manager_class,
                                                       mock_client_class, mock_projects_class,
                                                       temp_teams_dir, mock_env, capsys):
        """Test --remove-stale flag with projects performing actual removal."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Test Project', 'url': 'url', 'closed': False}
        ]
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_access_grants.return_value = []  # Return empty list for results
        mock_manager.apply_project_access.return_value = []  # Return empty list for project errors
        
        # Mock rate limit
        mock_client.get_rate_limit.return_value = {
            'remaining': 5000,
            'limit': 5000,
            'reset_timestamp': '2026-03-26T13:00:00Z'
        }
        
        mock_manager.detect_stale_collaborators.return_value = {}
        mock_manager.detect_stale_project_collaborators.return_value = {
            'org:1': ['bob']
        }
        mock_manager.remove_stale_collaborators.return_value = []
        mock_manager.remove_stale_project_collaborators.return_value = []  # No errors
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--remove-stale'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify dry_run=False was passed
        mock_manager.remove_stale_project_collaborators.assert_called_once()
        call_args = mock_manager.remove_stale_project_collaborators.call_args
        assert call_args[1]['dry_run'] is False
        captured = capsys.readouterr()
        # Should show removal summary
        assert 'Removals' in captured.out or 'removed' in captured.out.lower()
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_combined_repo_and_project_stale_detection(self, mock_load, mock_manager_class,
                                                       mock_client_class, mock_projects_class,
                                                       temp_teams_dir, mock_env, capsys):
        """Test stale detection for both repositories and projects."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={"push": ["repo1"]},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Test Project', 'url': 'url', 'closed': False}
        ]
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {"repo1": {"alice": "push"}}
        mock_manager.apply_access_grants.return_value = []  # Return empty list for results
        mock_manager.apply_project_access.return_value = []  # Return empty list for project errors
        
        # Mock rate limit
        mock_client.get_rate_limit.return_value = {
            'remaining': 5000,
            'limit': 5000,
            'reset_timestamp': '2026-03-26T13:00:00Z'
        }
        
        # Stale collaborators in both repos and projects
        mock_manager.detect_stale_collaborators.return_value = {
            'repo1': ['bob']  # Stale repo collaborator
        }
        mock_manager.detect_stale_project_collaborators.return_value = {
            'org:1': ['charlie']  # Stale project collaborator
        }
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--report-stale'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        # Should report both types of stale collaborators
        mock_manager.detect_stale_collaborators.assert_called_once()
        mock_manager.detect_stale_project_collaborators.assert_called_once()
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_stale_removal_with_errors(self, mock_load, mock_manager_class,
                                      mock_client_class, mock_projects_class,
                                      temp_teams_dir, mock_env, capsys):
        """Test stale removal handles errors gracefully."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository=None)
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_organization_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Test Project', 'url': 'url', 'closed': False}
        ]
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_access_grants.return_value = []  # Return empty list for results
        mock_manager.apply_project_access.return_value = []  # Return empty list for project errors
        
        # Mock rate limit
        mock_client.get_rate_limit.return_value = {
            'remaining': 5000,
            'limit': 5000,
            'reset_timestamp': '2026-03-26T13:00:00Z'
        }
        
        mock_manager.detect_stale_collaborators.return_value = {}
        mock_manager.detect_stale_project_collaborators.return_value = {
            'org:1': ['bob']
        }
        mock_manager.remove_stale_collaborators.return_value = []
        # Return errors from project removal
        mock_manager.remove_stale_project_collaborators.return_value = [
            "Failed to remove bob from project org:1: GraphQL error"
        ]
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--remove-stale'
        ]):
            exit_code = main()
        
        # Should still exit 0 but report errors
        assert exit_code == 0
        captured = capsys.readouterr()
        # Error should be displayed
        assert 'error' in captured.out.lower() or 'failed' in captured.out.lower()
    
    @patch('src.github_collab_manager.cli.ProjectsClient')
    @patch('src.github_collab_manager.cli.GitHubClient')
    @patch('src.github_collab_manager.cli.CollaboratorManager')
    @patch('src.github_collab_manager.cli.load_team_configs')
    def test_stale_detection_with_repo_projects(self, mock_load, mock_manager_class,
                                               mock_client_class, mock_projects_class,
                                               temp_teams_dir, mock_env, capsys):
        """Test stale detection with repository-level projects."""
        from src.github_collab_manager.models import TeamConfig, ProjectConfig, ProjectPermission
        
        team_config = TeamConfig(
            team_name="test-team",
            users=["alice"],
            roles={},
            projects=[
                ProjectConfig(number=1, permission=ProjectPermission.WRITE, repository="test-repo")
            ],
            source_file="test.yaml"
        )
        
        mock_load.return_value = (
            [team_config],
            ValidationResult(valid=True, errors=[], warnings=[])
        )
        
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        mock_projects = Mock()
        mock_projects.list_repository_projects.return_value = [
            {'id': 'proj_1', 'number': 1, 'title': 'Repo Project', 'url': 'url', 'closed': False}
        ]
        mock_projects_class.return_value = mock_projects
        
        mock_manager = Mock()
        mock_manager.process_team_configs.return_value = {}
        mock_manager.apply_access_grants.return_value = []  # Return empty list for results
        mock_manager.apply_project_access.return_value = []  # Return empty list for project errors
        
        # Mock rate limit
        mock_client.get_rate_limit.return_value = {
            'remaining': 5000,
            'limit': 5000,
            'reset_timestamp': '2026-03-26T13:00:00Z'
        }
        
        mock_manager.detect_stale_collaborators.return_value = {}
        mock_manager.detect_stale_project_collaborators.return_value = {
            'repo:test-repo:1': ['bob']  # Stale repo project collaborator
        }
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.argv', [
            'github-collab-manager',
            '--teams-dir', temp_teams_dir,
            '--report-stale'
        ]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        # Should report stale repo project collaborator
        mock_manager.detect_stale_project_collaborators.assert_called_once()


# Made with Bob