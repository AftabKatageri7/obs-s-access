# Data Model: GitHub Projects Access Manager

**Feature**: GitHub Projects (v2) Access Management  
**Date**: 2026-03-24  
**Status**: Complete

## Overview

This document defines the data entities and their relationships for managing GitHub Projects v2 access. The model extends the existing repository collaborator management system with project-specific entities.

---

## Core Entities

### ProjectConfig

Container for project access configuration within a team definition.

**Attributes**:
- `org_projects`: Dictionary mapping permission levels to lists of organization project numbers
- `repo_projects`: Dictionary mapping permission levels to lists of repository project specifications

**Relationships**:
- Contains multiple `OrganizationProject` entries
- Contains multiple `RepositoryProject` entries
- Belongs to one `TeamConfig`

**Validation Rules**:
- At least one of `org_projects` or `repo_projects` must be present if `ProjectConfig` exists
- Permission levels must be valid: `read`, `write`, or `admin`
- Project numbers must be positive integers

**Example**:
```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ProjectConfig:
    org_projects: Optional[Dict[str, List[int]]] = None
    repo_projects: Optional[Dict[str, List['RepositoryProject']]] = None
    
    def validate(self):
        if not self.org_projects and not self.repo_projects:
            raise ValueError("ProjectConfig must have at least org_projects or repo_projects")
        
        valid_permissions = {'read', 'write', 'admin'}
        if self.org_projects:
            for perm in self.org_projects.keys():
                if perm not in valid_permissions:
                    raise ValueError(f"Invalid permission: {perm}")
        
        if self.repo_projects:
            for perm in self.repo_projects.keys():
                if perm not in valid_permissions:
                    raise ValueError(f"Invalid permission: {perm}")
```

---

### OrganizationProject

Represents an organization-level GitHub Project (v2).

**Attributes**:
- `number`: Project number (visible in URL)
- `id`: GraphQL node ID (fetched from API)
- `title`: Human-readable project title (optional)
- `permission`: Permission level for this project (`read`, `write`, `admin`)

**Relationships**:
- Belongs to one organization
- Can have multiple `ProjectAccessGrant` entries (one per user)

**Validation Rules**:
- `number` must be positive integer
- `permission` must be one of: `read`, `write`, `admin`
- `id` must be valid GraphQL node ID format

**Example**:
```python
@dataclass
class OrganizationProject:
    number: int
    permission: str
    id: Optional[str] = None
    title: Optional[str] = None
    
    def __post_init__(self):
        if self.number <= 0:
            raise ValueError(f"Project number must be positive: {self.number}")
        if self.permission not in {'read', 'write', 'admin'}:
            raise ValueError(f"Invalid permission: {self.permission}")
    
    @property
    def identifier(self) -> str:
        """Unique identifier for logging and reporting"""
        return f"org-project-{self.number}"
```

---

### RepositoryProject

Represents a repository-level GitHub Project (v2).

**Attributes**:
- `repository`: Repository name
- `number`: Project number within the repository
- `id`: GraphQL node ID (fetched from API)
- `title`: Human-readable project title (optional)
- `permission`: Permission level for this project (`read`, `write`, `admin`)

**Relationships**:
- Belongs to one repository
- Can have multiple `ProjectAccessGrant` entries (one per user)

**Validation Rules**:
- `repository` must be non-empty string
- `number` must be positive integer
- `permission` must be one of: `read`, `write`, `admin`
- `id` must be valid GraphQL node ID format

**Example**:
```python
@dataclass
class RepositoryProject:
    repository: str
    number: int
    permission: str
    id: Optional[str] = None
    title: Optional[str] = None
    
    def __post_init__(self):
        if not self.repository:
            raise ValueError("Repository name cannot be empty")
        if self.number <= 0:
            raise ValueError(f"Project number must be positive: {self.number}")
        if self.permission not in {'read', 'write', 'admin'}:
            raise ValueError(f"Invalid permission: {self.permission}")
    
    @property
    def identifier(self) -> str:
        """Unique identifier for logging and reporting"""
        return f"repo-project-{self.repository}-{self.number}"
```

---

### ProjectAccessGrant

Represents a specific permission assignment for a user on a project.

**Attributes**:
- `username`: GitHub username
- `project_type`: Type of project (`organization` or `repository`)
- `project_number`: Project number
- `repository`: Repository name (null for org projects)
- `permission`: Permission level (`read`, `write`, `admin`)
- `project_id`: GraphQL node ID of the project
- `user_id`: GraphQL node ID of the user

**Relationships**:
- References one user (by username)
- References one project (org or repo)
- Represents one permission assignment

**Validation Rules**:
- `username` must be non-empty string
- `project_type` must be `organization` or `repository`
- `project_number` must be positive integer
- `repository` must be non-null if `project_type` is `repository`
- `repository` must be null if `project_type` is `organization`
- `permission` must be one of: `read`, `write`, `admin`

**Example**:
```python
@dataclass
class ProjectAccessGrant:
    username: str
    project_type: str
    project_number: int
    permission: str
    project_id: str
    user_id: str
    repository: Optional[str] = None
    
    def __post_init__(self):
        if not self.username:
            raise ValueError("Username cannot be empty")
        if self.project_type not in {'organization', 'repository'}:
            raise ValueError(f"Invalid project_type: {self.project_type}")
        if self.project_number <= 0:
            raise ValueError(f"Project number must be positive: {self.project_number}")
        if self.permission not in {'read', 'write', 'admin'}:
            raise ValueError(f"Invalid permission: {self.permission}")
        
        # Validate repository field based on project_type
        if self.project_type == 'repository' and not self.repository:
            raise ValueError("Repository must be specified for repository projects")
        if self.project_type == 'organization' and self.repository:
            raise ValueError("Repository must be null for organization projects")
    
    def to_log_dict(self) -> dict:
        """Convert to dictionary for audit logging"""
        return {
            'username': self.username,
            'project_type': self.project_type,
            'project_number': self.project_number,
            'repository': self.repository,
            'permission': self.permission
        }
```

---

### ProjectPermission (Enum)

Enumeration of valid GitHub Projects v2 permission levels.

**Values**:
- `READ`: View-only access to project
- `WRITE`: Can edit project items and views
- `ADMIN`: Full control including project settings

**Mapping**:
- YAML `read` → GraphQL `READ` → Enum `ProjectPermission.READ`
- YAML `write` → GraphQL `WRITE` → Enum `ProjectPermission.WRITE`
- YAML `admin` → GraphQL `ADMIN` → Enum `ProjectPermission.ADMIN`

**Example**:
```python
from enum import Enum

class ProjectPermission(str, Enum):
    READ = 'read'
    WRITE = 'write'
    ADMIN = 'admin'
    
    def to_graphql(self) -> str:
        """Convert to GraphQL ProjectV2Roles enum value"""
        return self.value.upper()
    
    @classmethod
    def from_yaml(cls, value: str) -> 'ProjectPermission':
        """Parse from YAML configuration"""
        value_lower = value.lower()
        if value_lower not in {'read', 'write', 'admin'}:
            raise ValueError(f"Invalid permission: {value}")
        return cls(value_lower)
    
    @classmethod
    def from_graphql(cls, value: str) -> 'ProjectPermission':
        """Parse from GraphQL response"""
        return cls(value.lower())
```

---

## Entity Relationships

```
TeamConfig
  └── ProjectConfig (0..1)
        ├── OrganizationProject (0..*)
        │     └── ProjectAccessGrant (0..*)
        └── RepositoryProject (0..*)
              └── ProjectAccessGrant (0..*)

User (GitHub)
  └── ProjectAccessGrant (0..*)
```

**Cardinality**:
- One `TeamConfig` has zero or one `ProjectConfig`
- One `ProjectConfig` has zero or more `OrganizationProject` entries
- One `ProjectConfig` has zero or more `RepositoryProject` entries
- One project (org or repo) has zero or more `ProjectAccessGrant` entries
- One user has zero or more `ProjectAccessGrant` entries

---

## State Transitions

### Project Access Grant Lifecycle

```
[Not Configured] 
    ↓ (Add to YAML)
[Configured]
    ↓ (Script execution)
[Pending]
    ↓ (GraphQL API call)
[Active] ←→ [Updated] (Permission change)
    ↓ (Remove from YAML)
[Removed]
```

**States**:
1. **Not Configured**: User-project combination not in any YAML file
2. **Configured**: Defined in YAML but not yet applied
3. **Pending**: API call in progress
4. **Active**: Permission successfully granted in GitHub
5. **Updated**: Permission level changed
6. **Removed**: Access revoked

---

## Data Flow

### Configuration Loading
```
YAML File
  ↓ (parse)
TeamConfig
  ↓ (extract)
ProjectConfig
  ↓ (expand)
List[OrganizationProject] + List[RepositoryProject]
  ↓ (combine with users)
List[ProjectAccessGrant]
```

### Access Synchronization
```
List[ProjectAccessGrant]
  ↓ (validate projects exist)
List[ValidatedProjectAccessGrant]
  ↓ (fetch current permissions)
List[ProjectAccessGrant] (with current state)
  ↓ (compute diff)
List[ProjectAccessGrant] (to add/update/remove)
  ↓ (execute GraphQL mutations)
List[ProjectAccessGrant] (with results)
  ↓ (log)
Audit Log Entries
```

---

## Validation Rules Summary

### At Configuration Load Time
- ✅ YAML syntax is valid
- ✅ Required fields present (team_name, users)
- ✅ Permission levels are valid strings
- ✅ Project numbers are positive integers
- ✅ Repository names are non-empty strings

### At Execution Time
- ✅ GitHub token has `project` scope
- ✅ Organization projects exist
- ✅ Repositories exist (for repo projects)
- ✅ Repository projects exist
- ✅ Users are valid GitHub usernames
- ✅ Users are outside collaborators (not org members)

### At API Call Time
- ✅ Project IDs are valid GraphQL node IDs
- ✅ User IDs are valid GraphQL node IDs
- ✅ Permission levels map to GraphQL enum values
- ✅ API responses contain expected fields

---

## Example Data Instances

### Organization Project
```python
org_project = OrganizationProject(
    number=1,
    permission='write',
    id='PVT_kwDOABCDEF4AABCD',
    title='Main Development Board'
)
```

### Repository Project
```python
repo_project = RepositoryProject(
    repository='dashboard-app',
    number=2,
    permission='admin',
    id='PVT_kwDOXYZABC4AAXYZ',
    title='Dashboard Features'
)
```

### Project Access Grant
```python
access_grant = ProjectAccessGrant(
    username='alice-dev',
    project_type='organization',
    project_number=1,
    permission='write',
    project_id='PVT_kwDOABCDEF4AABCD',
    user_id='U_kgDOABCDEF',
    repository=None
)
```

---

## Database Schema (Not Applicable)

This system does not use a database. All state is:
- **Configuration**: Stored in YAML files (version controlled)
- **Runtime State**: Held in memory during execution
- **Persistent State**: Stored in GitHub via GraphQL API
- **Audit Trail**: Written to stdout as structured logs

---

**Data Model Version**: 1.0  
**Last Updated**: 2026-03-24  
**Status**: Complete and ready for implementation