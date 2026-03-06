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

# Made with Bob
