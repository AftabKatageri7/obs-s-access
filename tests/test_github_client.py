"""Tests for GitHub client module"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.NamedUser import NamedUser

from src.github_collab_manager.github_client import GitHubClient
from src.github_collab_manager.models import OperationResult
from src.github_collab_manager.audit_logger import AuditLogger


@pytest.fixture
def mock_logger():
    """Create a mock audit logger."""
    return Mock(spec=AuditLogger)


@pytest.fixture
def mock_github():
    """Create a mock GitHub instance."""
    with patch('src.github_collab_manager.github_client.Github') as mock:
        yield mock


@pytest.fixture
def github_client(mock_logger):
    """Create a GitHubClient instance with mocked dependencies."""
    with patch('src.github_collab_manager.github_client.Github'):
        client = GitHubClient(
            token="test_token",
            org_name="test_org",
            logger=mock_logger
        )
        return client


class TestGitHubClientInit:
    """Tests for GitHubClient initialization."""
    
    def test_init_with_logger(self, mock_logger):
        """Test initialization with provided logger."""
        with patch('src.github_collab_manager.github_client.Github'):
            client = GitHubClient("token", "org", mock_logger)
            assert client.org_name == "org"
            assert client.logger == mock_logger
    
    def test_init_without_logger(self):
        """Test initialization without logger creates default."""
        with patch('src.github_collab_manager.github_client.Github'):
            client = GitHubClient("token", "org")
            assert client.org_name == "org"
            assert client.logger is not None
            assert isinstance(client.logger, AuditLogger)


class TestAuthentication:
    """Tests for GitHub authentication."""
    
    def test_authenticate_success(self, github_client, mock_logger):
        """Test successful authentication."""
        mock_user = Mock()
        mock_user.login = "test_user"
        github_client.github.get_user.return_value = mock_user
        
        result = github_client.authenticate()
        
        assert result is True
        mock_logger.log_info.assert_called_once()
        assert "test_user" in mock_logger.log_info.call_args[0][0]
    
    def test_authenticate_failure(self, github_client, mock_logger):
        """Test authentication failure."""
        github_client.github.get_user.side_effect = GithubException(
            status=401,
            data={"message": "Bad credentials"},
            headers={}
        )
        
        result = github_client.authenticate()
        
        assert result is False
        mock_logger.log_error.assert_called_once()
        assert "Authentication failed" in mock_logger.log_error.call_args[0][0]


class TestGetRepository:
    """Tests for repository retrieval."""
    
    def test_get_repository_success(self, github_client, mock_logger):
        """Test successful repository retrieval."""
        mock_org = Mock()
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        mock_org.get_repo.return_value = mock_repo
        github_client.github.get_organization.return_value = mock_org
        
        result = github_client.get_repository("test_repo")
        
        assert result == mock_repo
        mock_org.get_repo.assert_called_once_with("test_repo")
    
    def test_get_repository_not_found(self, github_client, mock_logger):
        """Test repository not found."""
        mock_org = Mock()
        mock_org.get_repo.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"},
            headers={}
        )
        github_client.github.get_organization.return_value = mock_org
        
        result = github_client.get_repository("nonexistent")
        
        assert result is None
        mock_logger.log_error.assert_called_once()
        assert "Repository not found" in mock_logger.log_error.call_args[0][0]
    
    def test_get_repository_api_error(self, github_client, mock_logger):
        """Test API error during repository retrieval."""
        mock_org = Mock()
        mock_org.get_repo.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"},
            headers={}
        )
        github_client.github.get_organization.return_value = mock_org
        
        result = github_client.get_repository("test_repo")
        
        assert result is None
        mock_logger.log_error.assert_called_once()


class TestListCollaborators:
    """Tests for listing repository collaborators."""
    
    def test_list_collaborators_success(self, github_client):
        """Test successful collaborator listing."""
        mock_repo = Mock(spec=Repository)
        mock_collab1 = Mock()
        mock_collab1.login = "user1"
        
        mock_collab2 = Mock()
        mock_collab2.login = "user2"
        
        mock_repo.get_collaborators.return_value = [mock_collab1, mock_collab2]
        
        # Mock get_collaborator_permission to return GitHub API format
        # GitHub API returns "write" for push and "admin" for admin
        def mock_get_permission(collab):
            if collab.login == "user1":
                return "write"  # GitHub API format for "push"
            elif collab.login == "user2":
                return "admin"
        
        mock_repo.get_collaborator_permission.side_effect = mock_get_permission
        
        result = github_client.list_collaborators(mock_repo)
        
        assert result == {"user1": "write", "user2": "admin"}
    
    def test_list_collaborators_empty(self, github_client):
        """Test listing collaborators for repository with none."""
        mock_repo = Mock(spec=Repository)
        mock_repo.get_collaborators.return_value = []
        
        result = github_client.list_collaborators(mock_repo)
        
        assert result == {}
    
    def test_list_collaborators_api_error(self, github_client, mock_logger):
        """Test API error during collaborator listing."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        mock_repo.get_collaborators.side_effect = GithubException(
            status=403,
            data={"message": "Forbidden"},
            headers={}
        )
        
        result = github_client.list_collaborators(mock_repo)
        
        assert result == {}
        mock_logger.log_error.assert_called_once()


class TestAddCollaborator:
    """Tests for adding collaborators."""
    
    def test_add_collaborator_success(self, github_client, mock_logger):
        """Test successful collaborator addition."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        mock_repo.add_to_collaborators.return_value = None
        
        result = github_client.add_collaborator(mock_repo, "new_user", "write")
        
        assert result.success is True
        assert result.action == "add_collaborator"
        assert result.user == "new_user"
        assert result.repository == "test_repo"
        assert result.role == "write"
        mock_repo.add_to_collaborators.assert_called_once_with("new_user", permission="write")
    
    def test_add_collaborator_api_error(self, github_client, mock_logger):
        """Test API error during collaborator addition."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        error = GithubException(status=422, data={"message": "Validation Failed"}, headers={})
        mock_repo.add_to_collaborators.side_effect = error
        
        result = github_client.add_collaborator(mock_repo, "new_user", "write")
        
        assert result.success is False
        assert result.action == "add_collaborator"
        assert result.error == error
        mock_logger.log_error.assert_called_once()


class TestUpdateCollaborator:
    """Tests for updating collaborator permissions."""
    
    def test_update_collaborator_success(self, github_client, mock_logger):
        """Test successful permission update."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        mock_repo.add_to_collaborators.return_value = None
        
        result = github_client.update_collaborator(mock_repo, "existing_user", "admin")
        
        assert result.success is True
        assert result.action == "update_collaborator"
        assert result.user == "existing_user"
        assert result.role == "admin"
        mock_repo.add_to_collaborators.assert_called_once_with("existing_user", permission="admin")
    
    def test_update_collaborator_api_error(self, github_client, mock_logger):
        """Test API error during permission update."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        error = GithubException(status=404, data={"message": "Not Found"}, headers={})
        mock_repo.add_to_collaborators.side_effect = error
        
        result = github_client.update_collaborator(mock_repo, "user", "maintain")
        
        assert result.success is False
        assert result.error == error


class TestRetryLogic:
    """Tests for retry logic with exponential backoff."""
    
    def test_retry_on_rate_limit(self, github_client, mock_logger):
        """Test retry on rate limit exceeded."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        
        # First two calls raise rate limit, third succeeds
        mock_repo.add_to_collaborators.side_effect = [
            RateLimitExceededException(status=403, data={}, headers={}),
            RateLimitExceededException(status=403, data={}, headers={}),
            None
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = github_client.add_collaborator(mock_repo, "user", "write")
        
        assert result.success is True
        assert mock_repo.add_to_collaborators.call_count == 3
    
    def test_retry_exhausted(self, github_client, mock_logger):
        """Test all retries exhausted."""
        mock_repo = Mock(spec=Repository)
        mock_repo.name = "test_repo"
        
        # All calls raise rate limit
        error = RateLimitExceededException(status=403, data={}, headers={})
        mock_repo.add_to_collaborators.side_effect = error
        
        with patch('time.sleep'):
            result = github_client.add_collaborator(mock_repo, "user", "write", max_retries=2)
        
        assert result.success is False
        assert result.error == error
        assert mock_repo.add_to_collaborators.call_count == 2


class TestGetRateLimit:
    """Tests for rate limit information retrieval."""
    
    def test_get_rate_limit_success(self, github_client):
        """Test successful rate limit retrieval."""
        mock_rate_limit = Mock()
        mock_core = Mock()
        mock_core.remaining = 4500
        mock_core.limit = 5000
        mock_core.reset.timestamp.return_value = 1234567890
        mock_rate_limit.core = mock_core
        
        github_client.github.get_rate_limit.return_value = mock_rate_limit
        
        result = github_client.get_rate_limit()
        
        assert result["remaining"] == 4500
        assert result["limit"] == 5000
        assert result["reset"] == 1234567890
    
    def test_get_rate_limit_error(self, github_client, mock_logger):
        """Test error during rate limit retrieval."""
        github_client.github.get_rate_limit.side_effect = GithubException(
            status=500,
            data={"message": "Internal Error"},
            headers={}
        )
        
        result = github_client.get_rate_limit()
        
        assert result == {"remaining": 0, "limit": 0, "reset": 0}
        mock_logger.log_error.assert_called_once()


# Made with Bob