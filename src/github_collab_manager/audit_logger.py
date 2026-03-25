"""Audit logging for GitHub Collaborator Manager"""

import json
import sys
from datetime import datetime, timezone
from typing import Optional

from .models import AuditLogEntry, OperationResult


class AuditLogger:
    """Handles structured audit logging to stdout.
    
    All logs are written in JSON format with ISO 8601 timestamps for
    machine-parseability and integration with log aggregation tools.
    """
    
    def __init__(self, log_level: str = "INFO"):
        """Initialize the audit logger.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_level = log_level.upper()
        self.log_levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }
    
    def _should_log(self, level: str) -> bool:
        """Check if a message at the given level should be logged.
        
        Args:
            level: Log level to check
            
        Returns:
            True if the message should be logged
        """
        return self.log_levels.get(level, 20) >= self.log_levels.get(self.log_level, 20)
    
    def _get_timestamp(self) -> str:
        """Generate ISO 8601 timestamp with timezone.
        
        Returns:
            Timestamp string in format: 2026-03-06T10:00:00+00:00
        """
        return datetime.now(timezone.utc).isoformat()
    
    def _write_log(self, log_entry: dict):
        """Write a log entry to stdout as JSON.
        
        Args:
            log_entry: Dictionary to serialize as JSON
        """
        try:
            json_log = json.dumps(log_entry, ensure_ascii=False)
            print(json_log, file=sys.stdout, flush=True)
        except Exception as e:
            # Fallback to stderr if JSON serialization fails
            print(f"ERROR: Failed to serialize log entry: {e}", file=sys.stderr)
    
    def log_operation(
        self,
        action: str,
        user: str,
        repository: str,
        role: str,
        result: str,
        message: str = "",
        source_team: str = "",
        source_file: str = "",
        level: str = "INFO",
        resource_type: str = "repository",
        project_type: Optional[str] = None,
        project_number: Optional[int] = None,
        project_repository: Optional[str] = None
    ):
        """Log a GitHub API operation.
        
        Args:
            action: Type of action (add_collaborator, update_collaborator, etc.)
            user: GitHub username
            repository: Repository name (for repo operations) or organization (for project operations)
            role: Permission level
            result: Operation result (success, failure, skipped)
            message: Additional context or error message
            source_team: Team that triggered this action
            source_file: YAML file that triggered this action
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            resource_type: Type of resource ("repository" or "project")
            project_type: For projects: "organization" or "repository"
            project_number: For projects: project number
            project_repository: For repository projects: repository name
        """
        if not self._should_log(level):
            return
        
        entry = AuditLogEntry(
            timestamp=self._get_timestamp(),
            action=action,
            user=user,
            repository=repository,
            role=role,
            result=result,
            message=message,
            source_team=source_team,
            source_file=source_file,
        )
        
        log_dict = entry.to_dict()
        
        # Add project-specific fields if this is a project operation
        if resource_type == "project":
            log_dict["resource_type"] = "project"
            if project_type:
                log_dict["project_type"] = project_type
            if project_number is not None:
                log_dict["project_number"] = project_number
            if project_repository:
                log_dict["project_repository"] = project_repository
        else:
            log_dict["resource_type"] = "repository"
        
        self._write_log(log_dict)
    
    def log_operation_result(
        self,
        result: OperationResult,
        source_team: str = "",
        source_file: str = "",
        resource_type: str = "repository",
        project_type: Optional[str] = None,
        project_number: Optional[int] = None,
        project_repository: Optional[str] = None
    ):
        """Log an OperationResult object.
        
        Args:
            result: OperationResult to log
            source_team: Team that triggered this action
            source_file: YAML file that triggered this action
            resource_type: Type of resource ("repository" or "project")
            project_type: For projects: "organization" or "repository"
            project_number: For projects: project number
            project_repository: For repository projects: repository name
        """
        level = "INFO" if result.success else "ERROR"
        self.log_operation(
            action=result.action,
            user=result.user,
            repository=result.repository,
            role=result.role,
            result=result.result_status,
            message=result.message,
            source_team=source_team,
            source_file=source_file,
            level=level,
            resource_type=resource_type,
            project_type=project_type,
            project_number=project_number,
            project_repository=project_repository,
        )
    
    def log_project_operation(
        self,
        action: str,
        user: str,
        organization: str,
        project_number: int,
        permission: str,
        result: str,
        message: str = "",
        source_team: str = "",
        source_file: str = "",
        project_type: str = "organization",
        project_repository: Optional[str] = None,
        level: str = "INFO"
    ):
        """Log a GitHub Projects API operation.
        
        This is a convenience method for logging project operations with
        proper field mapping.
        
        Args:
            action: Type of action (grant_project_access, update_project_permission, etc.)
            user: GitHub username
            organization: Organization name
            project_number: Project number
            permission: Permission level (read, write, admin)
            result: Operation result (success, failure, skipped)
            message: Additional context or error message
            source_team: Team that triggered this action
            source_file: YAML file that triggered this action
            project_type: "organization" or "repository"
            project_repository: For repository projects: repository name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_operation(
            action=action,
            user=user,
            repository=organization,  # Use repository field for organization
            role=permission,
            result=result,
            message=message,
            source_team=source_team,
            source_file=source_file,
            level=level,
            resource_type="project",
            project_type=project_type,
            project_number=project_number,
            project_repository=project_repository,
        )
    
    def log_info(self, message: str, **kwargs):
        """Log an informational message.
        
        Args:
            message: Log message
            **kwargs: Additional fields to include in log entry
        """
        if not self._should_log("INFO"):
            return
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "level": "INFO",
            "message": message,
            **kwargs
        }
        self._write_log(log_entry)
    
    def log_warning(self, message: str, **kwargs):
        """Log a warning message.
        
        Args:
            message: Warning message
            **kwargs: Additional fields to include in log entry
        """
        if not self._should_log("WARNING"):
            return
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "level": "WARNING",
            "message": message,
            **kwargs
        }
        self._write_log(log_entry)
    
    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log an error message.
        
        Args:
            message: Error message
            error: Exception object if available
            **kwargs: Additional fields to include in log entry
        """
        if not self._should_log("ERROR"):
            return
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "level": "ERROR",
            "message": message,
            **kwargs
        }
        
        if error:
            log_entry["error_type"] = type(error).__name__
            log_entry["error_message"] = str(error)
        
        self._write_log(log_entry)
    
    def log_debug(self, message: str, **kwargs):
        """Log a debug message.
        
        Args:
            message: Debug message
            **kwargs: Additional fields to include in log entry
        """
        if not self._should_log("DEBUG"):
            return
        
        log_entry = {
            "timestamp": self._get_timestamp(),
            "level": "DEBUG",
            "message": message,
            **kwargs
        }
        self._write_log(log_entry)

# Made with Bob
