"""
GitHub Projects v2 API client using GraphQL.

This module provides a client for interacting with GitHub Projects v2 API
to manage project access and collaborators.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import time
import logging
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport


logger = logging.getLogger(__name__)


class GraphQLErrorCategory(Enum):
    """Categories of GraphQL API errors for structured error handling."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


class GraphQLError(Exception):
    """Custom exception for GraphQL API errors with categorization."""
    
    def __init__(self, message: str, category: GraphQLErrorCategory, 
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.category = category
        self.original_error = original_error


class ProjectsClient:
    """
    Client for GitHub Projects v2 API using GraphQL.
    
    Handles project listing, collaborator management, and permission updates
    with rate limiting, error handling, and retry logic.
    """
    
    def __init__(self, token: str, base_url: str = "https://api.github.com/graphql"):
        """
        Initialize the Projects API client.
        
        Args:
            token: GitHub personal access token with 'project' scope
            base_url: GraphQL API endpoint URL
        """
        self.token = token
        self.base_url = base_url
        self._client = None
        self._rate_limit_remaining = None
        self._rate_limit_reset_at = None
        
    def _get_client(self) -> Client:
        """Get or create the GraphQL client instance."""
        if self._client is None:
            transport = RequestsHTTPTransport(
                url=self.base_url,
                headers={'Authorization': f'bearer {self.token}'},
                verify=True,
                retries=3,
            )
            self._client = Client(transport=transport, fetch_schema_from_transport=False)
        return self._client
    
    def _execute_with_retry(self, query: str, variables: Optional[Dict[str, Any]] = None,
                           max_retries: int = 3) -> Dict[str, Any]:
        """
        Execute a GraphQL query with exponential backoff retry logic.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query result data
            
        Raises:
            GraphQLError: On API errors with appropriate category
        """
        client = self._get_client()
        retry_count = 0
        backoff_seconds = 1
        
        while retry_count <= max_retries:
            try:
                result = client.execute(gql(query), variable_values=variables)
                
                # Extract rate limit info if present
                if 'rateLimit' in result:
                    self._rate_limit_remaining = result['rateLimit'].get('remaining')
                    self._rate_limit_reset_at = result['rateLimit'].get('resetAt')
                
                return result
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Categorize the error
                if 'rate limit' in error_message or 'secondary rate limit' in error_message:
                    category = GraphQLErrorCategory.RATE_LIMIT
                    if retry_count < max_retries:
                        wait_time = backoff_seconds * (2 ** retry_count)
                        logger.warning(f"Rate limit hit, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                elif 'unauthorized' in error_message or 'authentication' in error_message:
                    category = GraphQLErrorCategory.AUTHENTICATION
                elif 'not found' in error_message or 'could not resolve' in error_message:
                    category = GraphQLErrorCategory.NOT_FOUND
                elif 'forbidden' in error_message or 'permission' in error_message:
                    category = GraphQLErrorCategory.PERMISSION_DENIED
                elif 'network' in error_message or 'connection' in error_message:
                    category = GraphQLErrorCategory.NETWORK
                    if retry_count < max_retries:
                        wait_time = backoff_seconds * (2 ** retry_count)
                        logger.warning(f"Network error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                else:
                    category = GraphQLErrorCategory.UNKNOWN
                
                raise GraphQLError(
                    f"GraphQL API error: {str(e)}",
                    category=category,
                    original_error=e
                )
        
        raise GraphQLError(
            f"Max retries ({max_retries}) exceeded",
            category=GraphQLErrorCategory.RATE_LIMIT
        )
    
    def list_organization_projects(self, org_name: str) -> List[Dict[str, Any]]:
        """
        List all projects for an organization.
        
        Args:
            org_name: Organization name
            
        Returns:
            List of project dictionaries with id, number, title, url
            
        Raises:
            GraphQLError: On API errors
        """
        query = """
        query($orgName: String!, $cursor: String) {
          organization(login: $orgName) {
            projectsV2(first: 100, after: $cursor) {
              nodes {
                id
                number
                title
                url
                closed
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        projects = []
        cursor = None
        
        while True:
            variables = {"orgName": org_name, "cursor": cursor}
            result = self._execute_with_retry(query, variables)
            
            org_data = result.get('organization')
            if not org_data:
                raise GraphQLError(
                    f"Organization '{org_name}' not found",
                    category=GraphQLErrorCategory.NOT_FOUND
                )
            
            projects_data = org_data['projectsV2']
            projects.extend(projects_data['nodes'])
            
            if not projects_data['pageInfo']['hasNextPage']:
                break
            cursor = projects_data['pageInfo']['endCursor']
        
        return projects
    
    def list_repository_projects(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List all projects for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of project dictionaries with id, number, title, url
            
        Raises:
            GraphQLError: On API errors
        """
        query = """
        query($owner: String!, $repo: String!, $cursor: String) {
          repository(owner: $owner, name: $repo) {
            projectsV2(first: 100, after: $cursor) {
              nodes {
                id
                number
                title
                url
                closed
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        projects = []
        cursor = None
        
        while True:
            variables = {"owner": owner, "repo": repo, "cursor": cursor}
            result = self._execute_with_retry(query, variables)
            
            repo_data = result.get('repository')
            if not repo_data:
                raise GraphQLError(
                    f"Repository '{owner}/{repo}' not found",
                    category=GraphQLErrorCategory.NOT_FOUND
                )
            
            projects_data = repo_data['projectsV2']
            projects.extend(projects_data['nodes'])
            
            if not projects_data['pageInfo']['hasNextPage']:
                break
            cursor = projects_data['pageInfo']['endCursor']
        
        return projects
    
    def get_project_collaborators(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all collaborators for a project.
        
        Args:
            project_id: Project node ID
            
        Returns:
            List of collaborator dictionaries with login, role, permission
            
        Raises:
            GraphQLError: On API errors
        """
        query = """
        query($projectId: ID!, $cursor: String) {
          node(id: $projectId) {
            ... on ProjectV2 {
              collaborators(first: 100, after: $cursor) {
                nodes {
                  login
                  ... on User {
                    id
                  }
                }
                edges {
                  permission
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        collaborators = []
        cursor = None
        
        while True:
            variables = {"projectId": project_id, "cursor": cursor}
            result = self._execute_with_retry(query, variables)
            
            project_data = result.get('node')
            if not project_data:
                raise GraphQLError(
                    f"Project '{project_id}' not found",
                    category=GraphQLErrorCategory.NOT_FOUND
                )
            
            collab_data = project_data['collaborators']
            nodes = collab_data['nodes']
            edges = collab_data['edges']
            
            # Combine node and edge data
            for node, edge in zip(nodes, edges):
                collaborators.append({
                    'login': node['login'],
                    'id': node.get('id'),
                    'permission': edge['permission']
                })
            
            if not collab_data['pageInfo']['hasNextPage']:
                break
            cursor = collab_data['pageInfo']['endCursor']
        
        return collaborators
    
    def get_user_id(self, username: str) -> str:
        """
        Get the node ID for a GitHub user.
        
        Args:
            username: GitHub username
            
        Returns:
            User node ID
            
        Raises:
            GraphQLError: On API errors
        """
        query = """
        query($username: String!) {
          user(login: $username) {
            id
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        variables = {"username": username}
        result = self._execute_with_retry(query, variables)
        
        user_data = result.get('user')
        if not user_data:
            raise GraphQLError(
                f"User '{username}' not found",
                category=GraphQLErrorCategory.NOT_FOUND
            )
        
        return user_data['id']
    
    def update_project_collaborator(self, project_id: str, user_id: str, 
                                   permission: str) -> bool:
        """
        Update or add a collaborator to a project.
        
        Args:
            project_id: Project node ID
            user_id: User node ID
            permission: Permission level (READ, WRITE, ADMIN)
            
        Returns:
            True if successful
            
        Raises:
            GraphQLError: On API errors
        """
        mutation = """
        mutation($projectId: ID!, $userId: ID!, $permission: ProjectV2Permission!) {
          updateProjectV2Collaborator(input: {
            projectId: $projectId
            userId: $userId
            permission: $permission
          }) {
            collaborator {
              login
            }
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        variables = {
            "projectId": project_id,
            "userId": user_id,
            "permission": permission.upper()
        }
        
        try:
            self._execute_with_retry(mutation, variables)
            return True
        except GraphQLError as e:
            if e.category == GraphQLErrorCategory.PERMISSION_DENIED:
                logger.error(f"Permission denied updating project collaborator: {e}")
                raise
            raise
    
    def remove_project_collaborator(self, project_id: str, user_id: str) -> bool:
        """
        Remove a collaborator from a project.
        
        Args:
            project_id: Project node ID
            user_id: User node ID
            
        Returns:
            True if successful
            
        Raises:
            GraphQLError: On API errors
        """
        mutation = """
        mutation($projectId: ID!, $userId: ID!) {
          removeProjectV2Collaborator(input: {
            projectId: $projectId
            userId: $userId
          }) {
            clientMutationId
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        variables = {
            "projectId": project_id,
            "userId": user_id
        }
        
        try:
            self._execute_with_retry(mutation, variables)
            return True
        except GraphQLError as e:
            if e.category == GraphQLErrorCategory.PERMISSION_DENIED:
                logger.error(f"Permission denied removing project collaborator: {e}")
                raise
            raise
    
    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """Get the remaining rate limit quota."""
        return self._rate_limit_remaining
    
    @property
    def rate_limit_reset_at(self) -> Optional[str]:
        """Get the rate limit reset timestamp."""
        return self._rate_limit_reset_at

# Made with Bob
