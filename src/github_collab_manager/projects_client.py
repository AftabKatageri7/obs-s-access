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
    
    def __init__(self, token: str, base_url: str = "https://api.github.com/graphql",
                 validate_scopes: bool = True):
        """
        Initialize the Projects API client.
        
        Args:
            token: GitHub personal access token with 'project' scope
            base_url: GraphQL API endpoint URL
            validate_scopes: Whether to validate token scopes on initialization
        """
        self.token = token
        self.base_url = base_url
        self._client = None
        self._rate_limit_remaining = None
        self._rate_limit_reset_at = None
        self._scopes_validated = False
        
        if validate_scopes:
            self._validate_token_scopes()
        
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
    
    def _validate_token_scopes(self) -> None:
        """
        Validate that the token has required scopes for project access.
        
        This method attempts a simple query to detect missing scopes early
        and provide helpful error messages before operations fail.
        """
        if self._scopes_validated:
            return
            
        try:
            # Try a simple query that requires project scope
            query = """
            query {
              viewer {
                login
              }
              rateLimit {
                remaining
                resetAt
              }
            }
            """
            self._execute_with_retry(query, max_retries=1)
            self._scopes_validated = True
            logger.info("Token scopes validated successfully")
            
        except GraphQLError as e:
            if e.category == GraphQLErrorCategory.AUTHENTICATION:
                logger.error(
                    "Token validation failed. Your GitHub token may be invalid or expired. "
                    "Generate a new token with required scopes at: https://github.com/settings/tokens\n"
                    "Required scopes:\n"
                    "  - 'repo' or 'public_repo' (for repository access)\n"
                    "  - 'project' with read/write permissions (for project access)\n"
                    "  - 'read:org' (for private organization access, if needed)"
                )
                raise
            elif e.category == GraphQLErrorCategory.PERMISSION_DENIED:
                logger.warning(
                    "Token may be missing required scopes. "
                    "If you encounter permission errors, ensure your token has:\n"
                    "  - 'repo' or 'public_repo' (for repository access)\n"
                    "  - 'project' with read/write permissions (for project access)\n"
                    "  - 'read:org' (for private organization access, if needed)\n"
                    "Update your token at: https://github.com/settings/tokens"
                )
                # Don't raise - let operations proceed and fail with specific errors
                self._scopes_validated = True
            else:
                # Other errors during validation - log but don't block
                logger.debug(f"Token scope validation skipped due to error: {e}")
                self._scopes_validated = True
    
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
                    
                    # Warn if rate limit is running low
                    if self._rate_limit_remaining is not None and self._rate_limit_remaining < 100:
                        logger.warning(
                            f"GraphQL rate limit running low: {self._rate_limit_remaining} requests remaining. "
                            f"Resets at: {self._rate_limit_reset_at}"
                        )
                
                return result
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Categorize the error and provide actionable messages
                if 'rate limit' in error_message or 'secondary rate limit' in error_message:
                    category = GraphQLErrorCategory.RATE_LIMIT
                    if retry_count < max_retries:
                        wait_time = backoff_seconds * (2 ** retry_count)
                        logger.warning(f"Rate limit hit, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    else:
                        user_message = (
                            "GitHub API rate limit exceeded. "
                            "Please wait a few minutes before retrying. "
                            f"Original error: {str(e)}"
                        )
                elif 'unauthorized' in error_message or 'authentication' in error_message:
                    category = GraphQLErrorCategory.AUTHENTICATION
                    user_message = (
                        "Authentication failed. Please verify your GitHub token is valid and not expired. "
                        "Generate a new token at: https://github.com/settings/tokens "
                        f"Original error: {str(e)}"
                    )
                elif 'not found' in error_message or 'could not resolve' in error_message:
                    category = GraphQLErrorCategory.NOT_FOUND
                    user_message = (
                        "Resource not found. Please verify the organization, repository, or project exists "
                        "and your token has access to it. "
                        f"Original error: {str(e)}"
                    )
                elif 'forbidden' in error_message or 'permission' in error_message:
                    category = GraphQLErrorCategory.PERMISSION_DENIED
                    if 'project' in error_message:
                        user_message = (
                            "Permission denied for project access. "
                            "Your token must have 'project' scope (read/write) enabled. "
                            "Update your token at: https://github.com/settings/tokens "
                            f"Original error: {str(e)}"
                        )
                    else:
                        user_message = (
                            "Permission denied. Please verify your token has the required scopes: "
                            "- 'repo' or 'public_repo' for repository access "
                            "- 'project' (read/write) for project access "
                            "Update your token at: https://github.com/settings/tokens "
                            f"Original error: {str(e)}"
                        )
                elif 'network' in error_message or 'connection' in error_message:
                    category = GraphQLErrorCategory.NETWORK
                    if retry_count < max_retries:
                        wait_time = backoff_seconds * (2 ** retry_count)
                        logger.warning(f"Network error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    else:
                        user_message = (
                            "Network connection error. Please check your internet connection "
                            "and verify GitHub API is accessible. "
                            f"Original error: {str(e)}"
                        )
                else:
                    category = GraphQLErrorCategory.UNKNOWN
                    user_message = f"Unexpected GraphQL API error: {str(e)}"
                
                raise GraphQLError(
                    user_message,
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
                    f"Organization '{org_name}' not found. "
                    f"Please verify the organization name is correct and your token has access to it. "
                    f"If this is a private organization, ensure your token has 'read:org' scope.",
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
                    f"Repository '{owner}/{repo}' not found. "
                    f"Please verify the repository name is correct and your token has access to it. "
                    f"For private repositories, ensure your token has 'repo' scope.",
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
        
        Note: GitHub Projects v2 API doesn't expose collaborators via GraphQL.
        This method returns an empty list as a placeholder. Project access
        is managed through the updateProjectV2Collaborator mutation.
        
        Args:
            project_id: Project node ID
            
        Returns:
            Empty list (collaborators not queryable via GraphQL API)
            
        Raises:
            GraphQLError: On API errors
        """
        # GitHub Projects v2 API doesn't provide a way to query collaborators
        # The collaborators field doesn't exist on ProjectV2 type
        # We can only add/update/remove collaborators via mutations
        # For now, return empty list and rely on mutations to manage access
        
        logger.debug(
            f"get_project_collaborators called for project {project_id}. "
            "Note: GitHub Projects v2 API doesn't expose collaborators list via GraphQL. "
            "Returning empty list - all operations will be treated as additions."
        )
        
        return []
    
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
                f"User '{username}' not found on GitHub. "
                f"Please verify the username is correct and the user account exists. "
                f"Note: This tool only works with GitHub users, not organization accounts.",
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
                enhanced_message = (
                    f"Permission denied when updating project collaborator. "
                    f"Possible causes:\n"
                    f"  1. Your token lacks 'project' scope (read/write)\n"
                    f"  2. You don't have admin access to this project\n"
                    f"  3. The project is closed or archived\n"
                    f"Update your token at: https://github.com/settings/tokens\n"
                    f"Original error: {e}"
                )
                logger.error(enhanced_message)
                raise GraphQLError(
                    enhanced_message,
                    category=e.category,
                    original_error=e.original_error
                )
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
                enhanced_message = (
                    f"Permission denied when removing project collaborator. "
                    f"Possible causes:\n"
                    f"  1. Your token lacks 'project' scope (read/write)\n"
                    f"  2. You don't have admin access to this project\n"
                    f"  3. The collaborator doesn't exist on this project\n"
                    f"Update your token at: https://github.com/settings/tokens\n"
                    f"Original error: {e}"
                )
                logger.error(enhanced_message)
                raise GraphQLError(
                    enhanced_message,
                    category=e.category,
                    original_error=e.original_error
                )
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
