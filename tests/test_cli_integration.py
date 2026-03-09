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


# Made with Bob