"""Tests for audit logger"""

import json
import sys
from io import StringIO
from datetime import datetime

import pytest

from github_collab_manager.audit_logger import AuditLogger
from github_collab_manager.models import OperationResult


class TestAuditLogger:
    """Test suite for AuditLogger"""
    
    def test_log_operation_creates_valid_json(self, capsys):
        """Test that log_operation produces valid JSON output"""
        logger = AuditLogger()
        
        logger.log_operation(
            action="add_collaborator",
            user="test-user",
            repository="test-repo",
            role="write",
            result="success",
            message="User added successfully",
            source_team="Test Team",
            source_file="test.yaml"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["action"] == "add_collaborator"
        assert log_entry["user"] == "test-user"
        assert log_entry["repository"] == "test-repo"
        assert log_entry["role"] == "write"
        assert log_entry["result"] == "success"
        assert log_entry["message"] == "User added successfully"
        assert log_entry["source_team"] == "Test Team"
        assert log_entry["source_file"] == "test.yaml"
        assert "timestamp" in log_entry
    
    def test_timestamp_is_iso8601_format(self, capsys):
        """Test that timestamps are in ISO 8601 format with timezone"""
        logger = AuditLogger()
        
        logger.log_operation(
            action="test",
            user="user",
            repository="repo",
            role="read",
            result="success"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        # Verify ISO 8601 format by parsing
        timestamp = log_entry["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None
        
        # Verify timezone is present (contains + or Z)
        assert "+" in timestamp or timestamp.endswith("Z") or "-" in timestamp.split("T")[1]
    
    def test_log_operation_result(self, capsys):
        """Test logging an OperationResult object"""
        logger = AuditLogger()
        
        result = OperationResult(
            success=True,
            action="update_collaborator",
            user="alice",
            repository="my-repo",
            role="maintain",
            message="Role updated"
        )
        
        logger.log_operation_result(result, source_team="Team A", source_file="team-a.yaml")
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["action"] == "update_collaborator"
        assert log_entry["user"] == "alice"
        assert log_entry["repository"] == "my-repo"
        assert log_entry["role"] == "maintain"
        assert log_entry["result"] == "success"
        assert log_entry["message"] == "Role updated"
    
    def test_log_operation_result_failure(self, capsys):
        """Test logging a failed operation"""
        logger = AuditLogger()
        
        result = OperationResult(
            success=False,
            action="add_collaborator",
            user="bob",
            repository="test-repo",
            role="write",
            message="Repository not found",
            error=Exception("404 Not Found")
        )
        
        logger.log_operation_result(result)
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["result"] == "failure"
        assert log_entry["message"] == "Repository not found"
    
    def test_log_info(self, capsys):
        """Test logging informational messages"""
        logger = AuditLogger()
        
        logger.log_info("Processing team configurations", team_count=3)
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Processing team configurations"
        assert log_entry["team_count"] == 3
        assert "timestamp" in log_entry
    
    def test_log_warning(self, capsys):
        """Test logging warning messages"""
        logger = AuditLogger()
        
        logger.log_warning("Duplicate user found", user="charlie", files=["a.yaml", "b.yaml"])
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["level"] == "WARNING"
        assert log_entry["message"] == "Duplicate user found"
        assert log_entry["user"] == "charlie"
    
    def test_log_error(self, capsys):
        """Test logging error messages"""
        logger = AuditLogger()
        
        error = ValueError("Invalid role name")
        logger.log_error("Configuration validation failed", error=error, file="bad.yaml")
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["level"] == "ERROR"
        assert log_entry["message"] == "Configuration validation failed"
        assert log_entry["error_type"] == "ValueError"
        assert log_entry["error_message"] == "Invalid role name"
        assert log_entry["file"] == "bad.yaml"
    
    def test_log_debug(self, capsys):
        """Test logging debug messages"""
        logger = AuditLogger(log_level="DEBUG")
        
        logger.log_debug("Processing file", filename="test.yaml", line_count=10)
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["level"] == "DEBUG"
        assert log_entry["message"] == "Processing file"
        assert log_entry["filename"] == "test.yaml"
    
    def test_log_level_filtering_info(self, capsys):
        """Test that DEBUG messages are filtered when log level is INFO"""
        logger = AuditLogger(log_level="INFO")
        
        logger.log_debug("This should not appear")
        logger.log_info("This should appear")
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        
        # Only INFO message should be logged
        assert len(lines) == 1
        log_entry = json.loads(lines[0])
        assert log_entry["level"] == "INFO"
    
    def test_log_level_filtering_error(self, capsys):
        """Test that INFO messages are filtered when log level is ERROR"""
        logger = AuditLogger(log_level="ERROR")
        
        logger.log_info("This should not appear")
        logger.log_warning("This should not appear")
        logger.log_error("This should appear")
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        
        # Only ERROR message should be logged
        assert len(lines) == 1
        log_entry = json.loads(lines[0])
        assert log_entry["level"] == "ERROR"
    
    def test_all_log_entries_are_valid_json(self, capsys):
        """Test that multiple log entries are all valid JSON"""
        logger = AuditLogger()
        
        logger.log_info("First message")
        logger.log_warning("Second message")
        logger.log_error("Third message")
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        
        assert len(lines) == 3
        for line in lines:
            log_entry = json.loads(line)  # Should not raise exception
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry
    
    def test_log_project_operation_organization(self, capsys):
        """Test logging an organization project operation"""
        logger = AuditLogger()
        
        logger.log_project_operation(
            action="grant_project_access",
            user="test-user",
            organization="test-org",
            project_number=42,
            permission="write",
            result="success",
            message="Access granted successfully",
            source_team="DevOps Team",
            source_file="devops.yaml",
            project_type="organization"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["action"] == "grant_project_access"
        assert log_entry["user"] == "test-user"
        assert log_entry["repository"] == "test-org"  # Organization stored in repository field
        assert log_entry["role"] == "write"  # Permission stored in role field
        assert log_entry["result"] == "success"
        assert log_entry["message"] == "Access granted successfully"
        assert log_entry["source_team"] == "DevOps Team"
        assert log_entry["source_file"] == "devops.yaml"
        assert log_entry["resource_type"] == "project"
        assert log_entry["project_type"] == "organization"
        assert log_entry["project_number"] == 42
        assert "timestamp" in log_entry
    
    def test_log_project_operation_repository(self, capsys):
        """Test logging a repository project operation"""
        logger = AuditLogger()
        
        logger.log_project_operation(
            action="update_project_permission",
            user="alice",
            organization="test-org",
            project_number=5,
            permission="admin",
            result="success",
            message="Permission updated",
            project_type="repository",
            project_repository="my-repo"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["action"] == "update_project_permission"
        assert log_entry["user"] == "alice"
        assert log_entry["resource_type"] == "project"
        assert log_entry["project_type"] == "repository"
        assert log_entry["project_number"] == 5
        assert log_entry["project_repository"] == "my-repo"
        assert log_entry["role"] == "admin"
    
    def test_log_operation_with_resource_type_repository(self, capsys):
        """Test that repository operations have resource_type=repository"""
        logger = AuditLogger()
        
        logger.log_operation(
            action="add_collaborator",
            user="bob",
            repository="test-repo",
            role="write",
            result="success",
            resource_type="repository"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["resource_type"] == "repository"
        assert "project_type" not in log_entry
        assert "project_number" not in log_entry
        assert "project_repository" not in log_entry
    
    def test_log_operation_with_resource_type_project(self, capsys):
        """Test that project operations have resource_type=project with project fields"""
        logger = AuditLogger()
        
        logger.log_operation(
            action="grant_project_access",
            user="charlie",
            repository="org-name",
            role="read",
            result="success",
            resource_type="project",
            project_type="organization",
            project_number=10
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["resource_type"] == "project"
        assert log_entry["project_type"] == "organization"
        assert log_entry["project_number"] == 10
    
    def test_log_operation_result_with_project_fields(self, capsys):
        """Test logging an OperationResult with project-specific fields"""
        logger = AuditLogger()
        
        result = OperationResult(
            success=True,
            action="grant_project_access",
            user="dave",
            repository="test-org",
            role="write",
            message="Project access granted"
        )
        
        logger.log_operation_result(
            result,
            source_team="Backend Team",
            source_file="backend.yaml",
            resource_type="project",
            project_type="organization",
            project_number=7
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["action"] == "grant_project_access"
        assert log_entry["user"] == "dave"
        assert log_entry["resource_type"] == "project"
        assert log_entry["project_type"] == "organization"
        assert log_entry["project_number"] == 7
        assert log_entry["source_team"] == "Backend Team"
        assert log_entry["source_file"] == "backend.yaml"
    
    def test_log_project_operation_failure(self, capsys):
        """Test logging a failed project operation"""
        logger = AuditLogger()
        
        logger.log_project_operation(
            action="grant_project_access",
            user="eve",
            organization="test-org",
            project_number=99,
            permission="admin",
            result="failure",
            message="Project not found",
            level="ERROR"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["result"] == "failure"
        assert log_entry["message"] == "Project not found"
        assert log_entry["resource_type"] == "project"
    
    def test_project_fields_consistency(self, capsys):
        """Test that project-specific fields are consistently formatted"""
        logger = AuditLogger()
        
        # Test organization project
        logger.log_project_operation(
            action="grant_project_access",
            user="user1",
            organization="org1",
            project_number=1,
            permission="read",
            result="success",
            project_type="organization"
        )
        
        # Test repository project
        logger.log_project_operation(
            action="grant_project_access",
            user="user2",
            organization="org2",
            project_number=2,
            permission="write",
            result="success",
            project_type="repository",
            project_repository="repo2"
        )
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        
        assert len(lines) == 2
        
        # Verify organization project
        org_log = json.loads(lines[0])
        assert org_log["resource_type"] == "project"
        assert org_log["project_type"] == "organization"
        assert org_log["project_number"] == 1
        assert "project_repository" not in org_log
        
        # Verify repository project
        repo_log = json.loads(lines[1])
        assert repo_log["resource_type"] == "project"
        assert repo_log["project_type"] == "repository"
        assert repo_log["project_number"] == 2
        assert repo_log["project_repository"] == "repo2"
    
    def test_mixed_repository_and_project_operations(self, capsys):
        """Test logging both repository and project operations in sequence"""
        logger = AuditLogger()
        
        # Log repository operation
        logger.log_operation(
            action="add_collaborator",
            user="user1",
            repository="repo1",
            role="write",
            result="success",
            resource_type="repository"
        )
        
        # Log project operation
        logger.log_project_operation(
            action="grant_project_access",
            user="user2",
            organization="org1",
            project_number=5,
            permission="admin",
            result="success"
        )
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        
        assert len(lines) == 2
        
        # Verify repository operation
        repo_log = json.loads(lines[0])
        assert repo_log["resource_type"] == "repository"
        assert repo_log["action"] == "add_collaborator"
        assert "project_type" not in repo_log
        
        # Verify project operation
        project_log = json.loads(lines[1])
        assert project_log["resource_type"] == "project"
        assert project_log["action"] == "grant_project_access"
        assert project_log["project_number"] == 5

# Made with Bob
