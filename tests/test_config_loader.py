"""Tests for configuration loading and validation."""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

from github_collab_manager.config_loader import (
    load_yaml_file,
    validate_yaml_schema,
    validate_role_names,
    validate_project_config,
    parse_project_configs,
    load_team_configs,
    VALID_ROLES,
    VALID_PROJECT_PERMISSIONS
)
from github_collab_manager.models import TeamConfig, ValidationResult, ProjectConfig, ProjectPermission


class TestLoadYamlFile:
    """Test suite for load_yaml_file function."""
    
    def test_load_valid_yaml_file(self):
        """Test loading a valid YAML file."""
        result = load_yaml_file('tests/fixtures/sample_teams/valid-team.yaml')
        
        assert isinstance(result, dict)
        assert result['team_name'] == 'Test Team'
        assert 'users' in result
        assert 'roles' in result
    
    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_yaml_file('tests/fixtures/nonexistent.yaml')
        
        assert 'not found' in str(exc_info.value).lower()
    
    def test_load_invalid_yaml_syntax(self):
        """Test loading a file with invalid YAML syntax."""
        with pytest.raises(yaml.YAMLError) as exc_info:
            load_yaml_file('tests/fixtures/sample_teams/invalid-syntax.yaml')
        
        assert 'invalid yaml syntax' in str(exc_info.value).lower()
    
    def test_load_empty_yaml_file(self):
        """Test loading an empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('')
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                load_yaml_file(temp_path)
            
            assert 'empty' in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)
    
    def test_load_yaml_with_non_dict_root(self):
        """Test loading YAML file with non-dictionary root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('- item1\n- item2\n')
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                load_yaml_file(temp_path)
            
            assert 'dictionary' in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)
    
    def test_load_directory_instead_of_file(self):
        """Test loading a directory path instead of file."""
        with pytest.raises(ValueError) as exc_info:
            load_yaml_file('tests/fixtures/sample_teams')
        
        assert 'not a file' in str(exc_info.value).lower()


class TestValidateYamlSchema:
    """Test suite for validate_yaml_schema function."""
    
    def test_validate_complete_valid_schema(self):
        """Test validation of complete valid schema."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice', 'bob'],
            'roles': {
                'push': ['repo-a'],
                'pull': ['repo-b']
            }
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_missing_team_name(self):
        """Test validation with missing team_name field."""
        data = {
            'users': ['alice'],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('team_name' in error for error in result.errors)
    
    def test_validate_missing_users(self):
        """Test validation with missing users field."""
        data = {
            'team_name': 'Test',
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('users' in error for error in result.errors)
    
    def test_validate_missing_roles(self):
        """Test validation with missing roles field."""
        data = {
            'team_name': 'Test',
            'users': ['alice']
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('roles' in error for error in result.errors)
    
    def test_validate_empty_team_name(self):
        """Test validation with empty team_name."""
        data = {
            'team_name': '   ',
            'users': ['alice'],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('empty' in error.lower() for error in result.errors)
    
    def test_validate_non_string_team_name(self):
        """Test validation with non-string team_name."""
        data = {
            'team_name': 123,
            'users': ['alice'],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('string' in error.lower() for error in result.errors)
    
    def test_validate_non_list_users(self):
        """Test validation with non-list users field."""
        data = {
            'team_name': 'Test',
            'users': 'alice',
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('list' in error.lower() for error in result.errors)
    
    def test_validate_empty_users_list(self):
        """Test validation with empty users list."""
        data = {
            'team_name': 'Test',
            'users': [],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is True  # Valid but should have warning
        assert len(result.warnings) > 0
        assert any('empty' in warning.lower() for warning in result.warnings)
    
    def test_validate_non_string_user(self):
        """Test validation with non-string user in list."""
        data = {
            'team_name': 'Test',
            'users': ['alice', 123, 'bob'],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('users[1]' in error for error in result.errors)
    
    def test_validate_empty_user_string(self):
        """Test validation with empty user string."""
        data = {
            'team_name': 'Test',
            'users': ['alice', '  ', 'bob'],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('users[1]' in error and 'empty' in error.lower() for error in result.errors)
    
    def test_validate_non_dict_roles(self):
        """Test validation with non-dictionary roles field."""
        data = {
            'team_name': 'Test',
            'users': ['alice'],
            'roles': ['push', 'pull']
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('dictionary' in error.lower() for error in result.errors)
    
    def test_validate_empty_roles_dict(self):
        """Test validation with empty roles dictionary."""
        data = {
            'team_name': 'Test',
            'users': ['alice'],
            'roles': {}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is True  # Valid but should have warning
        assert len(result.warnings) > 0
        assert any('empty' in warning.lower() for warning in result.warnings)
    
    def test_validate_non_list_repositories(self):
        """Test validation with non-list repositories."""
        data = {
            'team_name': 'Test',
            'users': ['alice'],
            'roles': {'push': 'repo-a'}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any('list' in error.lower() for error in result.errors)
    
    def test_validate_empty_repository_list(self):
        """Test validation with empty repository list."""
        data = {
            'team_name': 'Test',
            'users': ['alice'],
            'roles': {'push': []}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is True  # Valid but should have warning
        assert len(result.warnings) > 0
    
    def test_validate_non_string_repository(self):
        """Test validation with non-string repository."""
        data = {
            'team_name': 'Test',
            'users': ['alice'],
            'roles': {'push': ['repo-a', 123, 'repo-b']}
        }
        
        result = validate_yaml_schema(data, 'test.yaml')
        
        assert result.valid is False
        assert any("roles['push'][1]" in error for error in result.errors)


class TestValidateRoleNames:
    """Test suite for validate_role_names function."""
    
    def test_validate_all_valid_roles(self):
        """Test validation with all valid GitHub roles."""
        data = {
            'roles': {
                'pull': ['repo-a'],
                'triage': ['repo-b'],
                'push': ['repo-c'],
                'maintain': ['repo-d'],
                'admin': ['repo-e']
            }
        }
        
        result = validate_role_names(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_invalid_role_name(self):
        """Test validation with invalid role name."""
        data = {
            'roles': {
                'superuser': ['repo-a'],
                'push': ['repo-b']
            }
        }
        
        result = validate_role_names(data, 'test.yaml')
        
        assert result.valid is False
        assert any('superuser' in error for error in result.errors)
        assert any('valid roles are' in error.lower() for error in result.errors)
    
    def test_validate_multiple_invalid_roles(self):
        """Test validation with multiple invalid role names."""
        data = {
            'roles': {
                'superuser': ['repo-a'],
                'owner': ['repo-b'],
                'push': ['repo-c']
            }
        }
        
        result = validate_role_names(data, 'test.yaml')
        
        assert result.valid is False
        assert len(result.errors) >= 2
        assert any('superuser' in error for error in result.errors)
        assert any('owner' in error for error in result.errors)
    
    def test_validate_missing_roles_field(self):
        """Test validation when roles field is missing."""
        data = {'team_name': 'Test'}
        
        result = validate_role_names(data, 'test.yaml')
        
        # Should pass - schema validation handles missing fields
        assert result.valid is True
    
    def test_validate_non_dict_roles(self):
        """Test validation when roles is not a dictionary."""
        data = {'roles': ['push', 'pull']}
        
        result = validate_role_names(data, 'test.yaml')
        
        # Should pass - schema validation handles type errors
        assert result.valid is True


class TestLoadTeamConfigs:
    """Test suite for load_team_configs function."""
    
    def test_load_valid_team_config(self):
        """Test loading valid team configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid YAML file
            yaml_path = Path(temp_dir) / 'team.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Test Team',
                    'users': ['alice', 'bob'],
                    'roles': {'push': ['repo-a']}
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is True
            assert len(configs) == 1
            assert configs[0].team_name == 'Test Team'
            assert configs[0].users == ['alice', 'bob']
            assert configs[0].roles == {'push': ['repo-a']}
            assert str(yaml_path) in configs[0].source_file
    
    def test_load_multiple_team_configs(self):
        """Test loading multiple team configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple YAML files
            for i in range(3):
                yaml_path = Path(temp_dir) / f'team{i}.yaml'
                with open(yaml_path, 'w') as f:
                    yaml.dump({
                        'team_name': f'Team {i}',
                        'users': [f'user{i}'],
                        'roles': {'push': [f'repo{i}']}
                    }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is True
            assert len(configs) == 3
            assert [c.team_name for c in configs] == ['Team 0', 'Team 1', 'Team 2']
    
    def test_load_from_nonexistent_directory(self):
        """Test loading from directory that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_team_configs('/nonexistent/directory')
    
    def test_load_from_file_instead_of_directory(self):
        """Test loading from file path instead of directory."""
        with pytest.raises(NotADirectoryError):
            load_team_configs('tests/fixtures/sample_teams/valid-team.yaml')
    
    def test_load_from_empty_directory(self):
        """Test loading from directory with no YAML files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is False
            assert len(configs) == 0
            assert any('no yaml files' in error.lower() for error in result.errors)
    
    def test_load_skips_invalid_files(self):
        """Test that invalid files are skipped with errors reported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create one valid and one invalid file
            valid_path = Path(temp_dir) / 'valid.yaml'
            with open(valid_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Valid Team',
                    'users': ['alice'],
                    'roles': {'push': ['repo-a']}
                }, f)
            
            invalid_path = Path(temp_dir) / 'invalid.yaml'
            with open(invalid_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Invalid Team',
                    # Missing users and roles
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is False  # Has errors from invalid file
            assert len(configs) == 1  # Only valid file loaded
            assert configs[0].team_name == 'Valid Team'
            assert len(result.errors) > 0
    
    def test_load_reports_invalid_role_names(self):
        """Test that invalid role names are reported as errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = Path(temp_dir) / 'team.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Bad Role Team',
                    'users': ['alice'],
                    'roles': {'superuser': ['repo-a']}
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is False
            assert len(configs) == 0  # Invalid role prevents loading
            assert any('superuser' in error for error in result.errors)
    
    def test_load_alphabetical_order(self):
        """Test that files are processed in alphabetical order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with names that sort differently
            for name in ['zebra', 'alpha', 'beta']:
                yaml_path = Path(temp_dir) / f'{name}.yaml'
                with open(yaml_path, 'w') as f:
                    yaml.dump({
                        'team_name': name,
                        'users': ['user'],
                        'roles': {'push': ['repo']}
                    }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is True
            assert len(configs) == 3
            # Should be in alphabetical order
            assert [c.team_name for c in configs] == ['alpha', 'beta', 'zebra']
    
    def test_load_handles_both_yaml_and_yml_extensions(self):
        """Test that both .yaml and .yml files are loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .yaml file
            yaml_path = Path(temp_dir) / 'team1.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Team YAML',
                    'users': ['alice'],
                    'roles': {'push': ['repo-a']}
                }, f)
            
            # Create .yml file
            yml_path = Path(temp_dir) / 'team2.yml'
            with open(yml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Team YML',
                    'users': ['bob'],
                    'roles': {'push': ['repo-b']}
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is True
            assert len(configs) == 2
            team_names = {c.team_name for c in configs}
            assert team_names == {'Team YAML', 'Team YML'}


class TestIntegrationWithFixtures:
    """Integration tests using actual fixture files."""
    
    def test_load_valid_team_fixture(self):
        """Test loading the valid-team.yaml fixture."""
        data = load_yaml_file('tests/fixtures/sample_teams/valid-team.yaml')
        schema_result = validate_yaml_schema(data, 'valid-team.yaml')
        role_result = validate_role_names(data, 'valid-team.yaml')
        
        assert schema_result.valid is True
        assert role_result.valid is True
    
    def test_load_missing_fields_fixture(self):
        """Test loading the missing-fields.yaml fixture."""
        data = load_yaml_file('tests/fixtures/sample_teams/missing-fields.yaml')
        result = validate_yaml_schema(data, 'missing-fields.yaml')
        
        assert result.valid is False
        assert any('users' in error for error in result.errors)
    
    def test_load_invalid_role_fixture(self):
        """Test loading the invalid-role.yaml fixture."""
        data = load_yaml_file('tests/fixtures/sample_teams/invalid-role.yaml')
        schema_result = validate_yaml_schema(data, 'invalid-role.yaml')
        role_result = validate_role_names(data, 'invalid-role.yaml')
        
        assert schema_result.valid is True  # Schema is valid

class TestValidateProjectConfig:
    """Test suite for validate_project_config function."""
    
    def test_validate_missing_projects_section(self):
        """Test validation when projects section is missing (backward compatibility)."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']}
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_valid_organization_projects(self):
        """Test validation with valid organization projects."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': 1, 'permission': 'read'},
                    {'number': 5, 'permission': 'write'},
                    {'number': 10, 'permission': 'admin'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_valid_repository_projects(self):
        """Test validation with valid repository projects."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'repository_projects': [
                    {'repository': 'org/repo-a', 'number': 2, 'permission': 'read'},
                    {'repository': 'org/repo-b', 'number': 3, 'permission': 'write'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_mixed_project_types(self):
        """Test validation with both organization and repository projects."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': 1, 'permission': 'read'}
                ],
                'repository_projects': [
                    {'repository': 'org/repo-a', 'number': 2, 'permission': 'write'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_projects_not_dict(self):
        """Test validation when projects is not a dictionary."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': ['project1', 'project2']
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('dictionary' in error.lower() for error in result.errors)
    
    def test_validate_empty_projects_section(self):
        """Test validation with empty projects section."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {}
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is True
        assert len(result.warnings) > 0
        assert any('empty' in warning.lower() for warning in result.warnings)
    
    def test_validate_org_projects_not_list(self):
        """Test validation when organization_projects is not a list."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': {'number': 1, 'permission': 'read'}
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('list' in error.lower() for error in result.errors)
    
    def test_validate_org_project_missing_number(self):
        """Test validation when organization project missing number field."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('number' in error.lower() for error in result.errors)
    
    def test_validate_org_project_invalid_number_type(self):
        """Test validation when organization project number is not an integer."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': '1', 'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('integer' in error.lower() for error in result.errors)
    
    def test_validate_org_project_negative_number(self):
        """Test validation when organization project number is negative."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': -1, 'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('positive' in error.lower() for error in result.errors)
    
    def test_validate_org_project_zero_number(self):
        """Test validation when organization project number is zero."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': 0, 'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('positive' in error.lower() for error in result.errors)
    
    def test_validate_org_project_missing_permission(self):
        """Test validation when organization project missing permission field."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': 1}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('permission' in error.lower() for error in result.errors)
    
    def test_validate_org_project_invalid_permission(self):
        """Test validation when organization project has invalid permission."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': 1, 'permission': 'superuser'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('superuser' in error for error in result.errors)
        assert any('valid permissions' in error.lower() for error in result.errors)
    
    def test_validate_repo_project_missing_repository(self):
        """Test validation when repository project missing repository field."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'repository_projects': [
                    {'number': 2, 'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('repository' in error.lower() for error in result.errors)
    
    def test_validate_repo_project_empty_repository(self):
        """Test validation when repository project has empty repository string."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'repository_projects': [
                    {'repository': '  ', 'number': 2, 'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('empty' in error.lower() for error in result.errors)
    
    def test_validate_repo_project_invalid_repository_type(self):
        """Test validation when repository project repository is not a string."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'repository_projects': [
                    {'repository': 123, 'number': 2, 'permission': 'read'}
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert any('string' in error.lower() for error in result.errors)
    
    def test_validate_multiple_errors(self):
        """Test validation with multiple errors in different projects."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']},
            'projects': {
                'organization_projects': [
                    {'number': -1, 'permission': 'read'},  # Invalid number
                    {'number': 2, 'permission': 'superuser'}  # Invalid permission
                ],
                'repository_projects': [
                    {'repository': '', 'number': 3, 'permission': 'read'}  # Empty repo
                ]
            }
        }
        
        result = validate_project_config(data, 'test.yaml')
        
        assert result.valid is False
        assert len(result.errors) >= 3


class TestParseProjectConfigs:
    """Test suite for parse_project_configs function."""
    
    def test_parse_missing_projects_section(self):
        """Test parsing when projects section is missing."""
        data = {
            'team_name': 'Test Team',
            'users': ['alice'],
            'roles': {'push': ['repo-a']}
        }
        
        result = parse_project_configs(data)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_parse_organization_projects(self):
        """Test parsing organization projects."""
        data = {
            'projects': {
                'organization_projects': [
                    {'number': 1, 'permission': 'read'},
                    {'number': 5, 'permission': 'write'},
                    {'number': 10, 'permission': 'admin'}
                ]
            }
        }
        
        result = parse_project_configs(data)
        
        assert len(result) == 3
        assert all(isinstance(p, ProjectConfig) for p in result)
        assert result[0].number == 1
        assert result[0].permission == ProjectPermission.READ
        assert result[0].repository is None
        assert result[1].number == 5
        assert result[1].permission == ProjectPermission.WRITE
        assert result[2].number == 10
        assert result[2].permission == ProjectPermission.ADMIN
    
    def test_parse_repository_projects(self):
        """Test parsing repository projects."""
        data = {
            'projects': {
                'repository_projects': [
                    {'repository': 'org/repo-a', 'number': 2, 'permission': 'read'},
                    {'repository': 'org/repo-b', 'number': 3, 'permission': 'write'}
                ]
            }
        }
        
        result = parse_project_configs(data)
        
        assert len(result) == 2
        assert all(isinstance(p, ProjectConfig) for p in result)
        assert result[0].repository == 'org/repo-a'
        assert result[0].number == 2
        assert result[0].permission == ProjectPermission.READ
        assert result[1].repository == 'org/repo-b'
        assert result[1].number == 3
        assert result[1].permission == ProjectPermission.WRITE
    
    def test_parse_mixed_project_types(self):
        """Test parsing both organization and repository projects."""
        data = {
            'projects': {
                'organization_projects': [
                    {'number': 1, 'permission': 'read'}
                ],
                'repository_projects': [
                    {'repository': 'org/repo-a', 'number': 2, 'permission': 'write'}
                ]
            }
        }
        
        result = parse_project_configs(data)
        
        assert len(result) == 2
        assert result[0].repository is None  # Org project
        assert result[1].repository == 'org/repo-a'  # Repo project
    
    def test_parse_handles_malformed_data_gracefully(self):
        """Test that parsing handles malformed data without crashing."""
        data = {
            'projects': {
                'organization_projects': [
                    {'number': 1, 'permission': 'read'},
                    {'number': 'invalid'},  # Missing permission, invalid number
                    {'number': 3, 'permission': 'write'}
                ]
            }
        }
        
        result = parse_project_configs(data)
        
        # Should skip invalid entry but parse valid ones
        assert len(result) == 2
        assert result[0].number == 1
        assert result[1].number == 3
    
    def test_parse_empty_projects_section(self):
        """Test parsing empty projects section."""
        data = {
            'projects': {}
        }
        
        result = parse_project_configs(data)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestLoadTeamConfigsWithProjects:
    """Test suite for load_team_configs with projects section."""
    
    def test_load_config_with_projects(self):
        """Test loading team configuration with projects section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = Path(temp_dir) / 'team.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Test Team',
                    'users': ['alice'],
                    'roles': {'push': ['repo-a']},
                    'projects': {
                        'organization_projects': [
                            {'number': 1, 'permission': 'read'}
                        ]
                    }
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is True
            assert len(configs) == 1
            assert len(configs[0].projects) == 1
            assert configs[0].projects[0].number == 1
            assert configs[0].projects[0].permission == ProjectPermission.READ
    
    def test_load_config_without_projects_backward_compatibility(self):
        """Test loading team configuration without projects section (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = Path(temp_dir) / 'team.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Test Team',
                    'users': ['alice'],
                    'roles': {'push': ['repo-a']}
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is True
            assert len(configs) == 1
            assert len(configs[0].projects) == 0  # Empty projects list
    
    def test_load_config_with_invalid_projects(self):
        """Test loading team configuration with invalid projects section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = Path(temp_dir) / 'team.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump({
                    'team_name': 'Test Team',
                    'users': ['alice'],
                    'roles': {'push': ['repo-a']},
                    'projects': {
                        'organization_projects': [
                            {'number': -1, 'permission': 'read'}  # Invalid number
                        ]
                    }
                }, f)
            
            configs, result = load_team_configs(temp_dir)
            
            assert result.valid is False
            assert len(configs) == 0  # Invalid projects prevent loading
            assert any('positive' in error.lower() for error in result.errors)
    
    def test_load_real_test_fixture(self):
        """Test loading the actual test-with-projects.yaml fixture."""
        configs, result = load_team_configs('teams')
        
        # Find the test-with-projects config
        test_config = None
        for config in configs:
            if config.team_name == 'test-team-with-projects':
                test_config = config
                break
        
        assert test_config is not None
        assert len(test_config.projects) == 6  # 3 org + 3 repo projects
        
        # Verify organization projects
        org_projects = [p for p in test_config.projects if p.repository is None]
        assert len(org_projects) == 3
        assert org_projects[0].number == 1
        assert org_projects[0].permission == ProjectPermission.READ
        
        # Verify repository projects
        repo_projects = [p for p in test_config.projects if p.repository is not None]
        assert len(repo_projects) == 3
        assert repo_projects[0].repository == 'observability-s/obs-s-access'
        assert repo_projects[0].number == 2

        assert role_result.valid is False  # But role name is invalid
        assert any('superuser' in error for error in role_result.errors)

# Made with Bob
