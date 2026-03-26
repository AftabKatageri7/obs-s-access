"""Data models for GitHub Collaborator Manager"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


@dataclass
class TeamConfig:
    """Represents a team configuration loaded from YAML.
    
    Attributes:
        team_name: Identifier for the team (for logging/reporting)
        users: List of GitHub usernames
        roles: Mapping of role names to lists of repository names
        projects: List of project configurations (optional)
        source_file: Path to the YAML file this config was loaded from
    """
    team_name: str
    users: List[str]
    roles: Dict[str, List[str]]
    projects: List['ProjectConfig'] = field(default_factory=list)
    source_file: str = ""
    
    def get_access_grants(self) -> List['AccessGrant']:
        """Generate all access grants from this team configuration.
        
        Returns:
            List of AccessGrant objects for each user-repository-role combination
        """
        grants = []
        for role, repositories in self.roles.items():
            for repository in repositories:
                for user in self.users:
                    grants.append(AccessGrant(
                        user=user,
                        repository=repository,
                        role=role,
                        source_team=self.team_name,
                        source_file=self.source_file
                    ))
        return grants


@dataclass
class AccessGrant:
    """Represents a specific user-repository-role assignment.
    
    Attributes:
        user: GitHub username
        repository: Repository name (without org prefix)
        role: Permission level (read, triage, write, maintain, admin)
        source_team: Team name that defined this grant
        source_file: YAML file that defined this grant
    """
    user: str
    repository: str
    role: str
    source_team: str = ""
    source_file: str = ""
    
    def __hash__(self):
        """Make AccessGrant hashable for deduplication."""
        return hash((self.user, self.repository))
    
    def __eq__(self, other):
        """Two grants are equal if they affect the same user-repository pair."""
        if not isinstance(other, AccessGrant):
            return False
        return self.user == other.user and self.repository == other.repository


@dataclass
class AuditLogEntry:
    """Represents a logged operation for audit trail.
    
    Attributes:
        timestamp: ISO 8601 formatted timestamp with timezone
        action: Type of action (add_collaborator, update_collaborator, remove_collaborator, skip, error)
        user: GitHub username affected
        repository: Repository name
        role: Permission level (if applicable)
        result: Operation result (success, failure, skipped)
        message: Additional context or error message
        source_team: Team that triggered this action
        source_file: YAML file that triggered this action
    """
    timestamp: str
    action: str
    user: str
    repository: str
    role: str
    result: str
    message: str = ""
    source_team: str = ""
    source_file: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "user": self.user,
            "repository": self.repository,
            "role": self.role,
            "result": self.result,
            "message": self.message,
            "source_team": self.source_team,
            "source_file": self.source_file,
        }


@dataclass
class OperationResult:
    """Represents the outcome of a GitHub API operation.
    
    Attributes:
        success: Whether the operation succeeded
        action: Type of action performed
        user: GitHub username affected
        repository: Repository name
        role: Permission level
        message: Success message or error description
        error: Exception object if operation failed
    """
    success: bool
    action: str
    user: str
    repository: str
    role: str
    message: str = ""
    error: Optional[Exception] = None
    
    @property
    def result_status(self) -> str:
        """Get result status string for logging."""
        return "success" if self.success else "failure"


@dataclass
class ValidationResult:
    """Represents the result of configuration validation.
    
    Attributes:
        valid: Whether the configuration is valid
        errors: List of error messages
        warnings: List of warning messages
        file_path: Path to the file being validated
    """
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_path: str = ""
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)


class ProjectPermission(Enum):
    """GitHub Projects v2 permission levels.
    
    Projects have three permission levels (vs five for repositories):
    - READ: Can view project
    - WRITE: Can view and edit project
    - ADMIN: Full control including settings and collaborators
    """
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    
    @classmethod
    def from_string(cls, value: str) -> 'ProjectPermission':
        """Convert string to ProjectPermission enum.
        
        Args:
            value: Permission string (case-insensitive)
            
        Returns:
            ProjectPermission enum value
            
        Raises:
            ValueError: If value is not a valid permission level
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = [p.value for p in cls]
            raise ValueError(
                f"Invalid project permission '{value}'. "
                f"Must be one of: {', '.join(valid_values)}"
            )
    
    def to_graphql(self) -> str:
        """Convert to GraphQL API format (uppercase)."""
        return self.value.upper()


@dataclass
class ProjectConfig:
    """Configuration for a single project access grant.
    
    Attributes:
        number: Project number (unique within org or repo)
        permission: Access level (read, write, admin)
        repository: Repository name for repo-level projects (None for org projects)
    """
    number: int
    permission: ProjectPermission
    repository: Optional[str] = None
    
    def __post_init__(self):
        """Validate project configuration after initialization."""
        if self.number <= 0:
            raise ValueError(f"Project number must be positive, got {self.number}")
        
        if isinstance(self.permission, str):
            self.permission = ProjectPermission.from_string(self.permission)
        
        if self.repository is not None and not self.repository.strip():
            raise ValueError("Repository name cannot be empty string")
    
    @property
    def is_organization_project(self) -> bool:
        """Check if this is an organization-level project."""
        return self.repository is None
    
    @property
    def is_repository_project(self) -> bool:
        """Check if this is a repository-level project."""
        return self.repository is not None


@dataclass
class OrganizationProject:
    """Represents an organization-level GitHub Project.
    
    Attributes:
        id: Project node ID (GraphQL)
        number: Project number
        title: Project title
        url: Project URL
        closed: Whether project is closed
    """
    id: str
    number: int
    title: str
    url: str
    closed: bool = False


@dataclass
class RepositoryProject:
    """Represents a repository-level GitHub Project.
    
    Attributes:
        id: Project node ID (GraphQL)
        number: Project number
        title: Project title
        url: Project URL
        repository: Repository name
        closed: Whether project is closed
    """
    id: str
    number: int
    title: str
    url: str
    repository: str
    closed: bool = False


@dataclass
class ProjectAccessGrant:
    """Represents a specific user-project-permission assignment.
    
    Attributes:
        user: GitHub username
        project_id: Project node ID
        project_number: Project number
        project_title: Project title
        permission: Permission level (read, write, admin)
        repository: Repository name for repo projects (None for org projects)
        source_team: Team name that defined this grant
        source_file: YAML file that defined this grant
    """
    user: str
    project_id: str
    project_number: int
    project_title: str
    permission: ProjectPermission
    repository: Optional[str] = None
    source_team: str = ""
    source_file: str = ""
    
    def __post_init__(self):
        """Ensure permission is ProjectPermission enum."""
        if isinstance(self.permission, str):
            self.permission = ProjectPermission.from_string(self.permission)
    
    def __hash__(self):
        """Make ProjectAccessGrant hashable for deduplication."""
        return hash((self.user, self.project_id))
    
    def __eq__(self, other):
        """Two grants are equal if they affect the same user-project pair."""
        if not isinstance(other, ProjectAccessGrant):
            return False
        return self.user == other.user and self.project_id == other.project_id
    
    @property
    def is_organization_project(self) -> bool:
        """Check if this grant is for an organization-level project."""
        return self.repository is None
    
    @property
    def is_repository_project(self) -> bool:
        """Check if this grant is for a repository-level project."""
        return self.repository is not None
    
    @property
    def resource_identifier(self) -> str:
        """Get human-readable resource identifier for logging."""
        if self.is_organization_project:
            return f"org project #{self.project_number}"
        return f"repo project {self.repository}#{self.project_number}"


# Made with Bob
