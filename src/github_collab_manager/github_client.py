"""GitHub API client for managing repository collaborators.

This module provides a wrapper around the PyGithub library with
rate limit handling, error management, and audit logging.
"""

import time
from typing import Optional, List, Dict
from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.NamedUser import NamedUser

from .models import OperationResult
from .audit_logger import AuditLogger


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: str, org_name: str, logger: Optional[AuditLogger] = None):
        """Initialize GitHub client.
        
        Args:
            token: GitHub personal access token
            org_name: GitHub organization name
            logger: Optional audit logger instance
        """
        self.token = token
        self.org_name = org_name
        self.logger = logger or AuditLogger()
        self._github: Optional[Github] = None
        self._org = None
    
    def authenticate(self) -> bool:
        """Authenticate with GitHub API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self._github = Github(self.token)
            # Test authentication by getting user
            user = self._github.get_user()
            self.logger.log_info(
                f"Authenticated as GitHub user: {user.login}",
                user=user.login
            )
            
            # Get organization
            self._org = self._github.get_organization(self.org_name)
            self.logger.log_info(
                f"Connected to organization: {self.org_name}",
                organization=self.org_name
            )
            
            return True
            
        except GithubException as e:
            self.logger.log_error(
                "GitHub authentication failed",
                error=e,
                status_code=e.status if hasattr(e, 'status') else None
            )
            return False
        except Exception as e:
            self.logger.log_error(
                "Unexpected error during authentication",
                error=e
            )
            return False
    
    def get_repository(self, repo_name: str) -> Optional[Repository]:
        """Get a repository object.
        
        Args:
            repo_name: Repository name (without org prefix)
            
        Returns:
            Repository object or None if not found
        """
        if not self._org:
            self.logger.log_error("Not authenticated - call authenticate() first")
            return None
        
        try:
            full_name = f"{self.org_name}/{repo_name}"
            repo = self._org.get_repo(repo_name)
            self.logger.log_debug(
                f"Retrieved repository: {full_name}",
                repository=repo_name
            )
            return repo
            
        except GithubException as e:
            if e.status == 404:
                self.logger.log_warning(
                    f"Repository not found: {self.org_name}/{repo_name}",
                    repository=repo_name,
                    status_code=404
                )
            else:
                self.logger.log_error(
                    f"Error retrieving repository: {self.org_name}/{repo_name}",
                    error=e,
                    repository=repo_name,
                    status_code=e.status if hasattr(e, 'status') else None
                )
            return None
        except Exception as e:
            self.logger.log_error(
                f"Unexpected error retrieving repository: {repo_name}",
                error=e,
                repository=repo_name
            )
            return None
    
    def list_collaborators(self, repo: Repository) -> Dict[str, str]:
        """List all collaborators for a repository.
        
        Args:
            repo: Repository object
            
        Returns:
            Dictionary mapping username to permission level
        """
        collaborators = {}
        
        try:
            for collab in repo.get_collaborators():
                # Get permission level
                permission = repo.get_collaborator_permission(collab)
                collaborators[collab.login] = permission
            
            self.logger.log_debug(
                f"Listed {len(collaborators)} collaborators for {repo.name}",
                repository=repo.name,
                count=len(collaborators)
            )
            
        except GithubException as e:
            self.logger.log_error(
                f"Error listing collaborators for {repo.name}",
                error=e,
                repository=repo.name,
                status_code=e.status if hasattr(e, 'status') else None
            )
        except Exception as e:
            self.logger.log_error(
                f"Unexpected error listing collaborators for {repo.name}",
                error=e,
                repository=repo.name
            )
        
        return collaborators
    
    def add_collaborator(self, repo: Repository, username: str, 
                        permission: str) -> OperationResult:
        """Add a collaborator to a repository.
        
        Args:
            repo: Repository object
            username: GitHub username
            permission: Permission level (pull, triage, push, maintain, admin)
            
        Returns:
            OperationResult indicating success or failure
        """
        try:
            # Add collaborator with retry logic
            self._execute_with_retry(
                lambda: repo.add_to_collaborators(username, permission)
            )
            
            return OperationResult(
                success=True,
                action="add_collaborator",
                user=username,
                repository=repo.name,
                role=permission,
                message=f"Successfully added {username} to {repo.name} with {permission} permission"
            )
            
        except GithubException as e:
            error_msg = f"Failed to add {username} to {repo.name}: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}"
            return OperationResult(
                success=False,
                action="add_collaborator",
                user=username,
                repository=repo.name,
                role=permission,
                message=error_msg,
                error=e
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action="add_collaborator",
                user=username,
                repository=repo.name,
                role=permission,
                message=f"Unexpected error: {str(e)}",
                error=e
            )
    
    def update_collaborator(self, repo: Repository, username: str, 
                           permission: str) -> OperationResult:
        """Update a collaborator's permission level.
        
        Args:
            repo: Repository object
            username: GitHub username
            permission: New permission level
            
        Returns:
            OperationResult indicating success or failure
        """
        try:
            # Update is same as add in GitHub API
            self._execute_with_retry(
                lambda: repo.add_to_collaborators(username, permission)
            )
            
            return OperationResult(
                success=True,
                action="update_collaborator",
                user=username,
                repository=repo.name,
                role=permission,
                message=f"Successfully updated {username} on {repo.name} to {permission} permission"
            )
            
        except GithubException as e:
            error_msg = f"Failed to update {username} on {repo.name}: {e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)}"
            return OperationResult(
                success=False,
                action="update_collaborator",
                user=username,
                repository=repo.name,
                role=permission,
                message=error_msg,
                error=e
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action="update_collaborator",
                user=username,
                repository=repo.name,
                role=permission,
                message=f"Unexpected error: {str(e)}",
                error=e
            )
    
    def _execute_with_retry(self, operation, max_retries: int = 3, 
                           base_delay: float = 1.0):
        """Execute an operation with exponential backoff retry on rate limit.
        
        Args:
            operation: Callable to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            
        Raises:
            GithubException: If operation fails after all retries
        """
        for attempt in range(max_retries + 1):
            try:
                return operation()
                
            except RateLimitExceededException as e:
                if attempt >= max_retries:
                    self.logger.log_error(
                        "Rate limit exceeded after maximum retries",
                        error=e,
                        attempts=attempt + 1
                    )
                    raise
                
                # Calculate exponential backoff delay
                delay = base_delay * (2 ** attempt)
                
                self.logger.log_warning(
                    f"Rate limit exceeded, retrying in {delay} seconds",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay
                )
                
                time.sleep(delay)
                
            except GithubException as e:
                # Don't retry on other GitHub exceptions
                raise
    
    def remove_collaborator(self, repository: str, username: str) -> bool:
        """Remove a collaborator from a repository.
        
        Args:
            repository: Repository name
            username: GitHub username to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            repo = self.get_repository(repository)
            if not repo:
                self.logger.log_error(
                    f"Cannot remove collaborator - repository not found: {repository}",
                    repository=repository,
                    user=username
                )
                return False
            
            # Remove collaborator
            repo.remove_from_collaborators(username)
            
            self.logger.log_info(
                f"Removed collaborator {username} from {repository}",
                action="remove_collaborator",
                user=username,
                repository=repository
            )
            
            return True
            
        except GithubException as e:
            self.logger.log_error(
                f"Failed to remove collaborator {username} from {repository}: {e}",
                user=username,
                repository=repository,
                error=str(e)
            )
            return False
    
    def get_rate_limit(self) -> Dict[str, int]:
        """Get current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        if not self._github:
            return {}
        
        try:
            rate_limit = self._github.get_rate_limit()
            return {
                'limit': rate_limit.core.limit,
                'remaining': rate_limit.core.remaining,
                'reset_timestamp': rate_limit.core.reset.timestamp()
            }
        except Exception as e:
            self.logger.log_error("Error getting rate limit", error=e)
            return {}

# Made with Bob
