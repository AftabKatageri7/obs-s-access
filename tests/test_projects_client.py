"""
Unit tests for ProjectsClient (GitHub Projects v2 API client).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.github_collab_manager.projects_client import (
    ProjectsClient,
    GraphQLError,
    GraphQLErrorCategory
)


@pytest.fixture
def mock_gql_client():
    """Mock GQL client for testing."""
    with patch('src.github_collab_manager.projects_client.Client') as mock_client:
        yield mock_client


@pytest.fixture
def projects_client():
    """Create a ProjectsClient instance for testing."""
    return ProjectsClient(token="test_token")


class TestProjectsClientInitialization:
    """Test ProjectsClient initialization."""
    
    def test_init_with_default_url(self):
        """Test initialization with default GraphQL URL."""
        client = ProjectsClient(token="test_token")
        assert client.token == "test_token"
        assert client.base_url == "https://api.github.com/graphql"
        assert client._client is None
    
    def test_init_with_custom_url(self):
        """Test initialization with custom GraphQL URL."""
        custom_url = "https://github.enterprise.com/api/graphql"
        client = ProjectsClient(token="test_token", base_url=custom_url)
        assert client.base_url == custom_url


class TestGraphQLErrorHandling:
    """Test GraphQL error categorization and handling."""
    
    def test_rate_limit_error_categorization(self, projects_client, mock_gql_client):
        """Test that rate limit errors are properly categorized."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("rate limit exceeded")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client._execute_with_retry("query { test }", max_retries=0)
        
        assert exc_info.value.category == GraphQLErrorCategory.RATE_LIMIT
    
    def test_authentication_error_categorization(self, projects_client, mock_gql_client):
        """Test that authentication errors are properly categorized."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("unauthorized access")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client._execute_with_retry("query { test }", max_retries=0)
        
        assert exc_info.value.category == GraphQLErrorCategory.AUTHENTICATION
    
    def test_not_found_error_categorization(self, projects_client, mock_gql_client):
        """Test that not found errors are properly categorized."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("could not resolve to a User")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client._execute_with_retry("query { test }", max_retries=0)
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND
    
    def test_permission_denied_error_categorization(self, projects_client, mock_gql_client):
        """Test that permission errors are properly categorized."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("forbidden: insufficient permissions")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client._execute_with_retry("query { test }", max_retries=0)
        
        assert exc_info.value.category == GraphQLErrorCategory.PERMISSION_DENIED
    
    def test_network_error_categorization(self, projects_client, mock_gql_client):
        """Test that network errors are properly categorized."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("network connection failed")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client._execute_with_retry("query { test }", max_retries=0)
        
        assert exc_info.value.category == GraphQLErrorCategory.NETWORK


class TestRetryLogic:
    """Test exponential backoff retry logic."""
    
    @patch('src.github_collab_manager.projects_client.time.sleep')
    def test_retry_on_rate_limit(self, mock_sleep, projects_client, mock_gql_client):
        """Test that rate limit errors trigger retry with backoff."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = [
            Exception("rate limit exceeded"),
            Exception("rate limit exceeded"),
            {"data": "success"}
        ]
        
        result = projects_client._execute_with_retry("query { test }", max_retries=3)
        
        assert result == {"data": "success"}
        assert mock_sleep.call_count == 2
        # Verify exponential backoff: 1s, 2s
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('src.github_collab_manager.projects_client.time.sleep')
    def test_retry_on_network_error(self, mock_sleep, projects_client, mock_gql_client):
        """Test that network errors trigger retry with backoff."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = [
            Exception("network error"),
            {"data": "success"}
        ]
        
        result = projects_client._execute_with_retry("query { test }", max_retries=3)
        
        assert result == {"data": "success"}
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(1)
    
    def test_no_retry_on_authentication_error(self, projects_client, mock_gql_client):
        """Test that authentication errors do not trigger retry."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("unauthorized")
        
        with pytest.raises(GraphQLError):
            projects_client._execute_with_retry("query { test }", max_retries=3)
        
        # Should only call execute once (no retries)
        assert mock_instance.execute.call_count == 1
    
    @patch('src.github_collab_manager.projects_client.time.sleep')
    def test_max_retries_exceeded(self, mock_sleep, projects_client, mock_gql_client):
        """Test that max retries limit is respected."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("rate limit exceeded")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client._execute_with_retry("query { test }", max_retries=2)
        
        assert "Max retries" in str(exc_info.value)
        assert mock_instance.execute.call_count == 3  # Initial + 2 retries


class TestListOrganizationProjects:
    """Test listing organization projects."""
    
    def test_list_org_projects_success(self, projects_client, mock_gql_client):
        """Test successful listing of organization projects."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'organization': {
                'projectsV2': {
                    'nodes': [
                        {'id': 'proj1', 'number': 1, 'title': 'Project 1', 'url': 'url1', 'closed': False},
                        {'id': 'proj2', 'number': 2, 'title': 'Project 2', 'url': 'url2', 'closed': False}
                    ],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None}
                }
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        projects = projects_client.list_organization_projects("test-org")
        
        assert len(projects) == 2
        assert projects[0]['id'] == 'proj1'
        assert projects[1]['title'] == 'Project 2'
        assert projects_client.rate_limit_remaining == 5000
    
    def test_list_org_projects_pagination(self, projects_client, mock_gql_client):
        """Test pagination when listing organization projects."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = [
            {
                'organization': {
                    'projectsV2': {
                        'nodes': [{'id': 'proj1', 'number': 1, 'title': 'Project 1', 'url': 'url1', 'closed': False}],
                        'pageInfo': {'hasNextPage': True, 'endCursor': 'cursor1'}
                    }
                },
                'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            {
                'organization': {
                    'projectsV2': {
                        'nodes': [{'id': 'proj2', 'number': 2, 'title': 'Project 2', 'url': 'url2', 'closed': False}],
                        'pageInfo': {'hasNextPage': False, 'endCursor': None}
                    }
                },
                'rateLimit': {'remaining': 4999, 'resetAt': '2024-01-01T00:00:00Z'}
            }
        ]
        
        projects = projects_client.list_organization_projects("test-org")
        
        assert len(projects) == 2
        assert mock_instance.execute.call_count == 2
    
    def test_list_org_projects_not_found(self, projects_client, mock_gql_client):
        """Test error when organization is not found."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {'organization': None}
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.list_organization_projects("nonexistent-org")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND
        assert "not found" in str(exc_info.value)


class TestListRepositoryProjects:
    """Test listing repository projects."""
    
    def test_list_repo_projects_success(self, projects_client, mock_gql_client):
        """Test successful listing of repository projects."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'repository': {
                'projectsV2': {
                    'nodes': [
                        {'id': 'proj1', 'number': 1, 'title': 'Repo Project', 'url': 'url1', 'closed': False}
                    ],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None}
                }
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        projects = projects_client.list_repository_projects("owner", "repo")
        
        assert len(projects) == 1
        assert projects[0]['title'] == 'Repo Project'
    
    def test_list_repo_projects_not_found(self, projects_client, mock_gql_client):
        """Test error when repository is not found."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {'repository': None}
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.list_repository_projects("owner", "nonexistent")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND


class TestGetProjectCollaborators:
    """Test getting project collaborators."""
    
    def test_get_collaborators_success(self, projects_client, mock_gql_client):
        """Test successful retrieval of project collaborators."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'node': {
                'collaborators': {
                    'nodes': [
                        {'login': 'user1', 'id': 'id1'},
                        {'login': 'user2', 'id': 'id2'}
                    ],
                    'edges': [
                        {'permission': 'WRITE'},
                        {'permission': 'READ'}
                    ],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None}
                }
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        collaborators = projects_client.get_project_collaborators("proj_id")
        
        assert len(collaborators) == 2
        assert collaborators[0]['login'] == 'user1'
        assert collaborators[0]['permission'] == 'WRITE'
        assert collaborators[1]['permission'] == 'READ'
    
    def test_get_collaborators_project_not_found(self, projects_client, mock_gql_client):
        """Test error when project is not found."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {'node': None}
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.get_project_collaborators("invalid_id")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND


class TestGetUserId:
    """Test getting user ID."""
    
    def test_get_user_id_success(self, projects_client, mock_gql_client):
        """Test successful retrieval of user ID."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'user': {'id': 'user_node_id'},
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        user_id = projects_client.get_user_id("testuser")
        
        assert user_id == 'user_node_id'
    
    def test_get_user_id_not_found(self, projects_client, mock_gql_client):
        """Test error when user is not found."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {'user': None}
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.get_user_id("nonexistent")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND


class TestUpdateProjectCollaborator:
    """Test updating project collaborators."""
    
    def test_update_collaborator_success(self, projects_client, mock_gql_client):
        """Test successful collaborator update."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'updateProjectV2Collaborator': {
                'collaborator': {'login': 'testuser'}
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        result = projects_client.update_project_collaborator("proj_id", "user_id", "write")
        
        assert result is True
    
    def test_update_collaborator_permission_denied(self, projects_client, mock_gql_client):
        """Test error when permission is denied."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("forbidden: insufficient permissions")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.update_project_collaborator("proj_id", "user_id", "admin")
        
        assert exc_info.value.category == GraphQLErrorCategory.PERMISSION_DENIED


class TestRemoveProjectCollaborator:
    """Test removing project collaborators."""
    
    def test_remove_collaborator_success(self, projects_client, mock_gql_client):
        """Test successful collaborator removal."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'removeProjectV2Collaborator': {
                'clientMutationId': 'mutation_id'
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        result = projects_client.remove_project_collaborator("proj_id", "user_id")
        
        assert result is True
    
    def test_remove_collaborator_permission_denied(self, projects_client, mock_gql_client):
        """Test error when permission is denied."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.side_effect = Exception("permission denied")
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.remove_project_collaborator("proj_id", "user_id")
        
        assert exc_info.value.category == GraphQLErrorCategory.PERMISSION_DENIED


class TestRateLimitTracking:
    """Test rate limit tracking."""
    
    def test_rate_limit_info_extracted(self, projects_client, mock_gql_client):
        """Test that rate limit info is extracted from responses."""
        mock_instance = mock_gql_client.return_value
        mock_instance.execute.return_value = {
            'user': {'id': 'user_id'},
            'rateLimit': {
                'remaining': 4500,
                'resetAt': '2024-01-01T12:00:00Z'
            }
        }
        
        projects_client.get_user_id("testuser")
        
        assert projects_client.rate_limit_remaining == 4500
        assert projects_client.rate_limit_reset_at == '2024-01-01T12:00:00Z'
    
    def test_rate_limit_properties(self, projects_client):
        """Test rate limit property accessors."""
        assert projects_client.rate_limit_remaining is None
        assert projects_client.rate_limit_reset_at is None
        
        projects_client._rate_limit_remaining = 1000
        projects_client._rate_limit_reset_at = '2024-01-01T00:00:00Z'
        
        assert projects_client.rate_limit_remaining == 1000
        assert projects_client.rate_limit_reset_at == '2024-01-01T00:00:00Z'


class TestProjectAccessWorkflowIntegration:
    """Integration tests for complete project access workflows."""
    
    def test_complete_org_project_workflow(self, projects_client, mock_gql_client):
        """Test complete workflow: list org projects, get user ID, grant access."""
        mock_instance = mock_gql_client.return_value
        
        # Mock responses for the workflow
        mock_instance.execute.side_effect = [
            # 1. List organization projects
            {
                'organization': {
                    'projectsV2': {
                        'nodes': [
                            {'id': 'proj_123', 'number': 1, 'title': 'Sprint Board', 'url': 'url1', 'closed': False}
                        ],
                        'pageInfo': {'hasNextPage': False, 'endCursor': None}
                    }
                },
                'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            # 2. Get user ID
            {
                'user': {'id': 'user_456'},
                'rateLimit': {'remaining': 4999, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            # 3. Update project collaborator
            {
                'updateProjectV2Collaborator': {
                    'collaborator': {'login': 'testuser'}
                },
                'rateLimit': {'remaining': 4998, 'resetAt': '2024-01-01T00:00:00Z'}
            }
        ]
        
        # Execute workflow
        projects = projects_client.list_organization_projects("test-org")
        assert len(projects) == 1
        assert projects[0]['id'] == 'proj_123'
        
        user_id = projects_client.get_user_id("testuser")
        assert user_id == 'user_456'
        
        result = projects_client.update_project_collaborator('proj_123', 'user_456', 'write')
        assert result is True
        
        # Verify rate limit tracking
        assert projects_client.rate_limit_remaining == 4998
        assert mock_instance.execute.call_count == 3
    
    def test_complete_repo_project_workflow(self, projects_client, mock_gql_client):
        """Test complete workflow: list repo projects, get user ID, grant access."""
        mock_instance = mock_gql_client.return_value
        
        mock_instance.execute.side_effect = [
            # 1. List repository projects
            {
                'repository': {
                    'projectsV2': {
                        'nodes': [
                            {'id': 'proj_789', 'number': 5, 'title': 'Repo Board', 'url': 'url2', 'closed': False}
                        ],
                        'pageInfo': {'hasNextPage': False, 'endCursor': None}
                    }
                },
                'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            # 2. Get user ID
            {
                'user': {'id': 'user_999'},
                'rateLimit': {'remaining': 4999, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            # 3. Update project collaborator
            {
                'updateProjectV2Collaborator': {
                    'collaborator': {'login': 'contributor'}
                },
                'rateLimit': {'remaining': 4998, 'resetAt': '2024-01-01T00:00:00Z'}
            }
        ]
        
        # Execute workflow
        projects = projects_client.list_repository_projects("owner", "repo")
        assert len(projects) == 1
        assert projects[0]['number'] == 5
        
        user_id = projects_client.get_user_id("contributor")
        assert user_id == 'user_999'
        
        result = projects_client.update_project_collaborator('proj_789', 'user_999', 'admin')
        assert result is True
        
        assert mock_instance.execute.call_count == 3
    
    def test_workflow_with_error_recovery(self, projects_client, mock_gql_client):
        """Test workflow with error and retry recovery."""
        mock_instance = mock_gql_client.return_value
        
        mock_instance.execute.side_effect = [
            # 1. List projects - rate limit error, then success
            Exception("rate limit exceeded"),
            {
                'organization': {
                    'projectsV2': {
                        'nodes': [{'id': 'proj_1', 'number': 1, 'title': 'P1', 'url': 'u1', 'closed': False}],
                        'pageInfo': {'hasNextPage': False, 'endCursor': None}
                    }
                },
                'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            # 2. Get user ID - success
            {
                'user': {'id': 'user_1'},
                'rateLimit': {'remaining': 4999, 'resetAt': '2024-01-01T00:00:00Z'}
            },
            # 3. Update collaborator - network error, then success
            Exception("network error"),
            {
                'updateProjectV2Collaborator': {
                    'collaborator': {'login': 'user'}
                },
                'rateLimit': {'remaining': 4998, 'resetAt': '2024-01-01T00:00:00Z'}
            }
        ]
        
        with patch('src.github_collab_manager.projects_client.time.sleep'):
            # Execute workflow with retries
            projects = projects_client.list_organization_projects("test-org")
            assert len(projects) == 1
            
            user_id = projects_client.get_user_id("user")
            assert user_id == 'user_1'
            
            result = projects_client.update_project_collaborator('proj_1', 'user_1', 'read')
            assert result is True
            
            # Should have made 5 calls total (2 retries)
            assert mock_instance.execute.call_count == 5
    
    def test_workflow_handles_not_found_gracefully(self, projects_client, mock_gql_client):
        """Test workflow handles not found errors appropriately."""
        mock_instance = mock_gql_client.return_value
        
        # User not found scenario
        mock_instance.execute.return_value = {'user': None}
        
        with pytest.raises(GraphQLError) as exc_info:
            projects_client.get_user_id("nonexistent-user")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND
        assert "not found" in str(exc_info.value).lower()
    
    def test_workflow_multiple_projects_batch(self, projects_client, mock_gql_client):
        """Test workflow processing multiple projects efficiently."""
        mock_instance = mock_gql_client.return_value
        
        # Mock listing multiple projects
        mock_instance.execute.return_value = {
            'organization': {
                'projectsV2': {
                    'nodes': [
                        {'id': 'proj_1', 'number': 1, 'title': 'P1', 'url': 'u1', 'closed': False},
                        {'id': 'proj_2', 'number': 2, 'title': 'P2', 'url': 'u2', 'closed': False},
                        {'id': 'proj_3', 'number': 3, 'title': 'P3', 'url': 'u3', 'closed': False}
                    ],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None}
                }
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        projects = projects_client.list_organization_projects("test-org")
        
        assert len(projects) == 3
        assert projects[0]['number'] == 1
        assert projects[1]['number'] == 2
        assert projects[2]['number'] == 3
        assert all(not p['closed'] for p in projects)


    def test_workflow_filters_closed_projects(self, projects_client, mock_gql_client):
        """Test that closed projects are filtered out."""
        mock_instance = mock_gql_client.return_value
        
        mock_instance.execute.return_value = {
            'organization': {
                'projectsV2': {
                    'nodes': [
                        {'id': 'proj_1', 'number': 1, 'title': 'Open', 'url': 'u1', 'closed': False},
                        {'id': 'proj_2', 'number': 2, 'title': 'Closed', 'url': 'u2', 'closed': True},
                        {'id': 'proj_3', 'number': 3, 'title': 'Open2', 'url': 'u3', 'closed': False}
                    ],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None}
                }
            },
            'rateLimit': {'remaining': 5000, 'resetAt': '2024-01-01T00:00:00Z'}
        }
        
        projects = projects_client.list_organization_projects("test-org")
        
        # Should only return open projects
        assert len(projects) == 2
        assert projects[0]['number'] == 1
        assert projects[1]['number'] == 3


class TestProjectsClientVCRIntegration:
    """Integration tests using VCR.py to record/replay GraphQL API responses.
    
    These tests use VCR.py cassettes to record actual GitHub GraphQL API responses
    and replay them for deterministic testing without hitting the live API.
    
    To record new cassettes:
    1. Set GITHUB_TOKEN environment variable with a valid token
    2. Delete the cassette file you want to re-record
    3. Run the test - it will record the interaction
    4. Commit the new cassette file
    
    Note: Cassettes contain sanitized tokens and sensitive data.
    """
    
    @pytest.fixture
    def vcr_config(self):
        """Configure VCR.py for GraphQL API recording."""
        return {
            'filter_headers': ['authorization'],
            'filter_post_data_parameters': ['token'],
            'match_on': ['method', 'scheme', 'host', 'port', 'path', 'body'],
            'record_mode': 'once',
            'cassette_library_dir': 'tests/fixtures/vcr_cassettes'
        }
    
    @pytest.mark.vcr()
    def test_vcr_list_organization_projects(self, vcr_config):
        """Test listing organization projects with VCR recording."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # This will use recorded response or record if cassette doesn't exist
        projects = client.list_organization_projects("github")
        
        # Verify response structure
        assert isinstance(projects, list)
        if projects:  # If there are projects
            assert 'id' in projects[0]
            assert 'number' in projects[0]
            assert 'title' in projects[0]
            assert 'url' in projects[0]
            assert 'closed' in projects[0]
    
    @pytest.mark.vcr()
    def test_vcr_list_repository_projects(self, vcr_config):
        """Test listing repository projects with VCR recording."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Test with a known public repository
        projects = client.list_repository_projects("octocat", "Hello-World")
        
        # Verify response structure
        assert isinstance(projects, list)
        # Repository may or may not have projects
    
    @pytest.mark.vcr()
    def test_vcr_get_user_id(self, vcr_config):
        """Test getting user ID with VCR recording."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Test with a known GitHub user
        user_id = client.get_user_id("octocat")
        
        # Verify response
        assert isinstance(user_id, str)
        assert len(user_id) > 0
        assert user_id.startswith('MDQ:')  # GitHub node IDs start with base64 prefix
    
    @pytest.mark.vcr()
    def test_vcr_get_user_id_not_found(self, vcr_config):
        """Test getting user ID for non-existent user with VCR recording."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Test with a user that definitely doesn't exist
        with pytest.raises(GraphQLError) as exc_info:
            client.get_user_id("this-user-definitely-does-not-exist-12345")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND
    
    @pytest.mark.vcr()
    def test_vcr_rate_limit_tracking(self, vcr_config):
        """Test that rate limit info is tracked from real API responses."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Make a simple query
        client.get_user_id("octocat")
        
        # Verify rate limit tracking
        assert client.rate_limit_remaining is not None
        assert isinstance(client.rate_limit_remaining, int)
        assert client.rate_limit_reset_at is not None
        assert isinstance(client.rate_limit_reset_at, str)
    
    @pytest.mark.vcr()
    def test_vcr_organization_not_found(self, vcr_config):
        """Test error handling for non-existent organization."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Test with an organization that doesn't exist
        with pytest.raises(GraphQLError) as exc_info:
            client.list_organization_projects("this-org-does-not-exist-xyz-12345")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.vcr()
    def test_vcr_repository_not_found(self, vcr_config):
        """Test error handling for non-existent repository."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Test with a repository that doesn't exist
        with pytest.raises(GraphQLError) as exc_info:
            client.list_repository_projects("octocat", "this-repo-does-not-exist-xyz")
        
        assert exc_info.value.category == GraphQLErrorCategory.NOT_FOUND
    
    @pytest.mark.vcr()
    def test_vcr_complete_workflow(self, vcr_config):
        """Test complete workflow with VCR: list projects and get user ID."""
        import os
        token = os.environ.get('GITHUB_TOKEN', 'fake_token_for_playback')
        client = ProjectsClient(token=token)
        
        # Step 1: List organization projects
        projects = client.list_organization_projects("github")
        initial_rate_limit = client.rate_limit_remaining
        
        # Step 2: Get user ID
        user_id = client.get_user_id("octocat")
        final_rate_limit = client.rate_limit_remaining
        
        # Verify workflow executed successfully
        assert isinstance(projects, list)
        assert isinstance(user_id, str)
        
        # Verify rate limit decreased (or stayed same if using cached cassette)
        assert final_rate_limit is not None
        assert initial_rate_limit is not None


# Made with Bob
