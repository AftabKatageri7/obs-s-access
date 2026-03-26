# Research: GitHub Projects Access Manager

**Feature**: GitHub Projects (v2) Access Management  
**Date**: 2026-03-24  
**Status**: Complete

## Overview

This document consolidates research findings for implementing GitHub Projects v2 access management using the GraphQL API. All technical unknowns from the planning phase have been resolved.

---

## R001: GitHub Projects v2 GraphQL API Patterns

### Decision
Use `gql` library with `requests` transport for GraphQL operations.

### Rationale
- **Type Safety**: `gql` provides query validation and type checking at development time
- **Active Maintenance**: Well-maintained library with strong community support (3.5k+ stars)
- **Clean Integration**: Works seamlessly with existing `requests`-based architecture
- **Query Composition**: Supports fragments and query composition for complex operations
- **Error Handling**: Built-in error parsing for GraphQL-specific error structures

### Alternatives Considered

1. **python-graphql-client**
   - Pros: Simpler API, fewer dependencies
   - Cons: Less type safety, manual query validation, smaller community
   - Rejected: Lack of type safety increases risk of runtime errors

2. **Direct requests with GraphQL**
   - Pros: No additional dependencies, full control
   - Cons: Manual error handling, no query validation, more boilerplate
   - Rejected: Too much manual work for error handling and validation

3. **sgqlc (Schema-based GraphQL Client)**
   - Pros: Full type generation from schema
   - Cons: Code generation overhead, complex setup, overkill for this use case
   - Rejected: Unnecessary complexity for straightforward CRUD operations

### Implementation Notes
```python
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Initialize transport with GitHub token
transport = RequestsHTTPTransport(
    url='https://api.github.com/graphql',
    headers={'Authorization': f'Bearer {token}'},
    retries=3,
)

# Create client
client = Client(transport=transport, fetch_schema_from_transport=True)

# Execute query
query = gql('''
    query($org: String!) {
        organization(login: $org) {
            projectsV2(first: 100) {
                nodes {
                    id
                    number
                    title
                }
            }
        }
    }
''')
result = client.execute(query, variable_values={'org': 'observability-s'})
```

---

## R002: GraphQL Query Structure for Projects v2

### Decision
Use separate query patterns for organization-level and repository-level projects.

### Rationale
- **Different Node Types**: Organization and repository projects have different GraphQL node structures
- **Parallel Processing**: Enables concurrent fetching of org and repo projects
- **Clear Separation**: Matches the YAML schema structure (`org_projects` vs `repo_projects`)
- **Efficient Pagination**: Can paginate org and repo projects independently

### Query Patterns

#### List Organization Projects
```graphql
query ListOrgProjects($org: String!, $cursor: String) {
  organization(login: $org) {
    projectsV2(first: 100, after: $cursor) {
      nodes {
        id
        number
        title
        closed
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

#### List Repository Projects
```graphql
query ListRepoProjects($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    projectsV2(first: 100, after: $cursor) {
      nodes {
        id
        number
        title
        closed
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

#### Get Project Collaborators
```graphql
query GetProjectCollaborators($projectId: ID!, $cursor: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      collaborators(first: 100, after: $cursor) {
        nodes {
          login
          role
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
```

#### Add/Update Project Collaborator
```graphql
mutation UpdateProjectCollaborator($projectId: ID!, $userId: ID!, $role: ProjectV2Roles!) {
  updateProjectV2Collaborators(
    input: {
      projectId: $projectId
      collaborators: [{userId: $userId, role: $role}]
    }
  ) {
    collaborators {
      userId
      role
    }
  }
}
```

#### Remove Project Collaborator
```graphql
mutation RemoveProjectCollaborator($projectId: ID!, $userId: ID!) {
  updateProjectV2Collaborators(
    input: {
      projectId: $projectId
      collaborators: [{userId: $userId, role: NONE}]
    }
  ) {
    collaborators {
      userId
    }
  }
}
```

### Permission Level Mapping
- YAML `read` → GraphQL `READ`
- YAML `write` → GraphQL `WRITE`
- YAML `admin` → GraphQL `ADMIN`

---

## R003: Error Handling for GraphQL API

### Decision
Implement structured error handling with specific error categories and retry logic.

### Rationale
- **GraphQL Error Structure**: Errors returned in `errors` array alongside `data`
- **Multiple Error Types**: Need to distinguish network, auth, business logic errors
- **Rate Limiting**: GraphQL uses cost-based rate limiting requiring smart retry
- **Graceful Degradation**: Invalid projects should not block valid operations

### Error Categories

#### 1. Network Errors
**Symptoms**: Connection timeout, DNS failure, network unreachable  
**Handling**: Retry with exponential backoff (max 3 attempts)  
**Example**:
```python
try:
    result = client.execute(query)
except TransportQueryError as e:
    if is_network_error(e):
        retry_with_backoff()
```

#### 2. Authentication Errors
**Symptoms**: 401 Unauthorized, invalid token, missing scopes  
**Handling**: Fail fast with clear message about token requirements  
**Example**:
```python
if 'FORBIDDEN' in error_message or 'UNAUTHORIZED' in error_message:
    raise AuthenticationError(
        "GitHub token lacks required 'project' scope. "
        "Update token at https://github.com/settings/tokens"
    )
```

#### 3. Not Found Errors
**Symptoms**: Project number doesn't exist, repository not found  
**Handling**: Log warning, skip project, continue processing  
**Example**:
```python
if 'NOT_FOUND' in error_type:
    logger.warning(f"Project {project_num} not found, skipping")
    continue
```

#### 4. Permission Errors
**Symptoms**: Token lacks access to specific project  
**Handling**: Log error, skip project, continue processing  
**Example**:
```python
if 'FORBIDDEN' in error_type:
    logger.error(f"No permission to access project {project_num}")
    continue
```

#### 5. Rate Limit Errors
**Symptoms**: Rate limit exceeded, cost limit reached  
**Handling**: Retry with exponential backoff, respect `Retry-After` header  
**Example**:
```python
if 'RATE_LIMITED' in error_type:
    retry_after = response.headers.get('Retry-After', 60)
    time.sleep(int(retry_after))
    retry_request()
```

### Error Response Structure
```python
{
    'errors': [
        {
            'type': 'NOT_FOUND',
            'path': ['organization', 'projectsV2'],
            'message': 'Could not resolve to a Project with number 999',
            'locations': [{'line': 3, 'column': 5}]
        }
    ],
    'data': {
        'organization': None
    }
}
```

---

## R004: YAML Schema Extension Strategy

### Decision
Add optional `projects:` section at same level as `roles:` in team configuration.

### Rationale
- **Backward Compatibility**: Existing files without `projects:` continue to work
- **Logical Grouping**: `roles:` for repositories, `projects:` for projects
- **Clear Separation**: Repository and project access are independent concerns
- **Easy Validation**: Can validate each section independently

### Schema Structure
```yaml
team_name: <string>
users: [<username>, ...]
roles:                    # Existing - repository access
  <permission>: [<repo>, ...]
projects:                 # NEW - project access
  org_projects:           # Organization-level projects
    <permission>: [<project_number>, ...]
  repo_projects:          # Repository-level projects
    <permission>:
      - repo: <repo_name>
        project: <project_number>
```

### Validation Rules
1. **Optional Sections**: `projects:`, `org_projects:`, `repo_projects:` all optional
2. **Permission Levels**: Must be one of `read`, `write`, `admin`
3. **Project Numbers**: Must be positive integers
4. **Repository Names**: Must match existing repositories (validated at runtime)
5. **Empty Roles**: `roles: {}` is valid (project-only access)

### Pydantic Models
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class RepositoryProject(BaseModel):
    repo: str
    project: int = Field(gt=0)

class ProjectConfig(BaseModel):
    org_projects: Optional[Dict[str, List[int]]] = None
    repo_projects: Optional[Dict[str, List[RepositoryProject]]] = None

class TeamConfig(BaseModel):
    team_name: str
    users: List[str]
    roles: Dict[str, List[str]]
    projects: Optional[ProjectConfig] = None
```

---

## R005: Audit Logging Format Consistency

### Decision
Extend existing structured log format with project-specific fields while maintaining backward compatibility.

### Rationale
- **Unified Analysis**: Same log parsing tools work for both repository and project logs
- **Clear Distinction**: `resource_type` field distinguishes operation type
- **Complete Context**: All relevant information for audit trail
- **JSON Structure**: Machine-readable for log aggregation systems

### Extended Log Format

#### Repository Operation (Existing)
```json
{
  "timestamp": "2026-03-24T19:00:00Z",
  "resource_type": "repository",
  "action": "add_collaborator",
  "repository": "observability-api",
  "username": "alice-dev",
  "permission": "write",
  "result": "success",
  "error": null
}
```

#### Organization Project Operation (New)
```json
{
  "timestamp": "2026-03-24T19:00:00Z",
  "resource_type": "project",
  "project_type": "organization",
  "project_number": 1,
  "project_title": "Main Development Board",
  "repository": null,
  "action": "add_collaborator",
  "username": "alice-dev",
  "permission": "write",
  "result": "success",
  "error": null
}
```

#### Repository Project Operation (New)
```json
{
  "timestamp": "2026-03-24T19:00:00Z",
  "resource_type": "project",
  "project_type": "repository",
  "project_number": 2,
  "project_title": "Dashboard Features",
  "repository": "dashboard-app",
  "action": "update_collaborator",
  "username": "bob-engineer",
  "permission": "admin",
  "previous_permission": "write",
  "result": "success",
  "error": null
}
```

### Log Fields

**Common Fields** (all operations):
- `timestamp`: ISO 8601 UTC timestamp
- `resource_type`: "repository" or "project"
- `action`: Operation type (add_collaborator, update_collaborator, remove_collaborator)
- `username`: GitHub username
- `permission`: Permission level granted
- `result`: "success" or "error"
- `error`: Error message if result is "error"

**Project-Specific Fields**:
- `project_type`: "organization" or "repository"
- `project_number`: Project number from YAML
- `project_title`: Human-readable project title (optional)
- `repository`: Repository name for repo projects, null for org projects
- `previous_permission`: Previous permission level (for updates)

### Implementation
```python
def log_project_operation(
    action: str,
    project_type: str,
    project_number: int,
    username: str,
    permission: str,
    result: str,
    repository: Optional[str] = None,
    project_title: Optional[str] = None,
    previous_permission: Optional[str] = None,
    error: Optional[str] = None
):
    log_entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'resource_type': 'project',
        'project_type': project_type,
        'project_number': project_number,
        'repository': repository,
        'action': action,
        'username': username,
        'permission': permission,
        'result': result,
        'error': error
    }
    if project_title:
        log_entry['project_title'] = project_title
    if previous_permission:
        log_entry['previous_permission'] = previous_permission
    
    print(json.dumps(log_entry))
```

---

## R006: GraphQL Rate Limiting Strategy

### Decision
Implement cost-aware retry logic with exponential backoff and rate limit detection.

### Rationale
- **Cost-Based Limits**: GraphQL uses query cost calculation (different from REST)
- **Proactive Throttling**: Check remaining rate limit before expensive operations
- **Graceful Degradation**: Slow down rather than fail completely
- **Respect Headers**: Honor `X-RateLimit-*` and `Retry-After` headers

### Rate Limit Headers
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4950
X-RateLimit-Reset: 1711305600
X-RateLimit-Used: 50
X-RateLimit-Resource: graphql
```

### Implementation Strategy
```python
class RateLimitHandler:
    def __init__(self, min_remaining=100):
        self.min_remaining = min_remaining
        self.backoff_seconds = 1
        self.max_backoff = 60
    
    def check_rate_limit(self, response):
        remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
        if remaining < self.min_remaining:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), self.backoff_seconds)
            logger.warning(f"Rate limit low ({remaining}), waiting {wait_time}s")
            time.sleep(wait_time)
    
    def handle_rate_limit_error(self):
        retry_after = self.backoff_seconds
        logger.warning(f"Rate limited, retrying after {retry_after}s")
        time.sleep(retry_after)
        self.backoff_seconds = min(self.backoff_seconds * 2, self.max_backoff)
```

---

## Summary

All technical research is complete. Key decisions:

1. ✅ **GraphQL Client**: Use `gql` library for type-safe operations
2. ✅ **Query Structure**: Separate queries for org vs repo projects
3. ✅ **Error Handling**: Structured error categories with retry logic
4. ✅ **YAML Schema**: Optional `projects:` section with backward compatibility
5. ✅ **Audit Logging**: Extended format with project-specific fields
6. ✅ **Rate Limiting**: Cost-aware retry with exponential backoff

No blocking issues identified. Ready to proceed with implementation.

---

**Research Complete**: 2026-03-24  
**Status**: All clarifications resolved  
**Next Step**: Generate design artifacts (data-model.md, contracts/, quickstart.md)