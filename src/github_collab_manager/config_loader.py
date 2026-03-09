"""Configuration loading and validation for GitHub Collaborator Manager.

This module handles loading YAML team configuration files, validating their
structure and content, and converting them into TeamConfig objects.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import yaml

from .models import TeamConfig, ValidationResult


# Valid GitHub repository permission levels
VALID_ROLES = {'pull', 'triage', 'push', 'maintain', 'admin'}


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a YAML file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Parsed YAML content as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        ValueError: If file is empty or not a dictionary
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML syntax in {file_path}: {e}")
    
    if content is None:
        raise ValueError(f"Empty YAML file: {file_path}")
    
    if not isinstance(content, dict):
        raise ValueError(f"YAML file must contain a dictionary at root level: {file_path}")
    
    return content


def validate_yaml_schema(data: Dict[str, Any], file_path: str) -> ValidationResult:
    """Validate that YAML data has required fields and correct structure.
    
    Args:
        data: Parsed YAML data
        file_path: Path to file (for error messages)
        
    Returns:
        ValidationResult with errors and warnings
    """
    errors = []
    warnings = []
    
    # Check required fields
    required_fields = ['team_name', 'users', 'roles']
    for field in required_fields:
        if field not in data:
            errors.append(f"{file_path}: Missing required field '{field}'")
    
    # If missing required fields, return early
    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)
    
    # Validate team_name
    if not isinstance(data['team_name'], str):
        errors.append(f"{file_path}: 'team_name' must be a string")
    elif not data['team_name'].strip():
        errors.append(f"{file_path}: 'team_name' cannot be empty")
    
    # Validate users
    if not isinstance(data['users'], list):
        errors.append(f"{file_path}: 'users' must be a list")
    elif len(data['users']) == 0:
        warnings.append(f"{file_path}: 'users' list is empty")
    else:
        for i, user in enumerate(data['users']):
            if not isinstance(user, str):
                errors.append(f"{file_path}: users[{i}] must be a string")
            elif not user.strip():
                errors.append(f"{file_path}: users[{i}] cannot be empty")
    
    # Validate roles
    if not isinstance(data['roles'], dict):
        errors.append(f"{file_path}: 'roles' must be a dictionary")
    elif len(data['roles']) == 0:
        warnings.append(f"{file_path}: 'roles' dictionary is empty")
    else:
        for role, repositories in data['roles'].items():
            if not isinstance(role, str):
                errors.append(f"{file_path}: Role key must be a string")
                continue
            
            if not isinstance(repositories, list):
                errors.append(f"{file_path}: roles['{role}'] must be a list of repositories")
                continue
            
            if len(repositories) == 0:
                warnings.append(f"{file_path}: roles['{role}'] has empty repository list")
            
            for i, repo in enumerate(repositories):
                if not isinstance(repo, str):
                    errors.append(f"{file_path}: roles['{role}'][{i}] must be a string")
                elif not repo.strip():
                    errors.append(f"{file_path}: roles['{role}'][{i}] cannot be empty")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def validate_role_names(data: Dict[str, Any], file_path: str) -> ValidationResult:
    """Validate that role names are valid GitHub permission levels.
    
    Args:
        data: Parsed YAML data
        file_path: Path to file (for error messages)
        
    Returns:
        ValidationResult with errors for invalid roles
    """
    errors = []
    warnings = []
    
    if 'roles' not in data or not isinstance(data['roles'], dict):
        # Schema validation should catch this
        return ValidationResult(valid=True, errors=[], warnings=[])
    
    for role in data['roles'].keys():
        if role not in VALID_ROLES:
            errors.append(
                f"{file_path}: Invalid role '{role}'. "
                f"Valid roles are: {', '.join(sorted(VALID_ROLES))}"
            )
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def load_team_configs(directory: str) -> tuple[List[TeamConfig], ValidationResult]:
    """Load all team configuration files from a directory.
    
    Processes YAML files in alphabetical order. If multiple files define
    access for the same user-repository pair, the last file wins.
    
    Args:
        directory: Path to directory containing YAML files
        
    Returns:
        Tuple of (list of TeamConfig objects, ValidationResult)
        
    Raises:
        FileNotFoundError: If directory doesn't exist
        NotADirectoryError: If path is not a directory
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")
    
    # Find all YAML files
    yaml_files = sorted(dir_path.glob('*.yaml')) + sorted(dir_path.glob('*.yml'))
    
    if not yaml_files:
        return [], ValidationResult(
            valid=False,
            errors=[f"No YAML files found in directory: {directory}"],
            warnings=[]
        )
    
    team_configs = []
    all_errors = []
    all_warnings = []
    
    for yaml_file in yaml_files:
        try:
            # Load YAML file
            data = load_yaml_file(str(yaml_file))
            
            # Validate schema
            schema_result = validate_yaml_schema(data, str(yaml_file))
            all_errors.extend(schema_result.errors)
            all_warnings.extend(schema_result.warnings)
            
            if not schema_result.valid:
                continue  # Skip this file if schema is invalid
            
            # Validate role names
            role_result = validate_role_names(data, str(yaml_file))
            all_errors.extend(role_result.errors)
            all_warnings.extend(role_result.warnings)
            
            if not role_result.valid:
                continue  # Skip this file if roles are invalid
            
            # Create TeamConfig object
            team_config = TeamConfig(
                team_name=data['team_name'],
                users=data['users'],
                roles=data['roles'],
                source_file=str(yaml_file)
            )
            team_configs.append(team_config)
            
        except FileNotFoundError as e:
            all_errors.append(str(e))
        except yaml.YAMLError as e:
            all_errors.append(str(e))
        except ValueError as e:
            all_errors.append(str(e))
        except Exception as e:
            all_errors.append(f"{yaml_file}: Unexpected error: {e}")
    
    validation_result = ValidationResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings
    )
    
    return team_configs, validation_result

# Made with Bob
