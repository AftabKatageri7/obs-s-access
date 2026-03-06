"""Data models for GitHub Collaborator Manager"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class TeamConfig:
    """Represents a team configuration loaded from YAML.
    
    Attributes:
        team_name: Identifier for the team (for logging/reporting)
        users: List of GitHub usernames
        roles: Mapping of role names to lists of repository names
        source_file: Path to the YAML file this config was loaded from
    """
    team_name: str
    users: List[str]
    roles: Dict[str, List[str]]
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

# Made with Bob
