# Quickstart Guide: GitHub Projects Access Manager

**Feature**: GitHub Projects (v2) Access Management  
**Date**: 2026-03-24  
**Status**: Ready for Implementation

## Overview

This guide provides step-by-step instructions for setting up and using the GitHub Projects access management feature once implemented.

---

## Prerequisites

### 1. GitHub Token with Project Scope

Your GitHub Personal Access Token must have the `project` scope in addition to the existing `repo` scope.

**Update your token**:
1. Go to https://github.com/settings/tokens
2. Find your existing token or create a new one
3. Ensure these scopes are selected:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `project` (Full control of projects) **← NEW**
4. Click "Update token" or "Generate token"
5. Copy the token and update your `GITHUB_TOKEN` environment variable

### 2. Python Environment

```bash
# Ensure Python 3.8+ is installed
python --version

# Install/upgrade dependencies
pip install -r requirements.txt
```

### 3. GitHub Projects v2 Enabled

Verify that GitHub Projects v2 is enabled for your organization:
- Go to https://github.com/orgs/observability-s/projects
- You should see Projects v2 boards (not legacy project boards)

---

## Configuration

### Step 1: Extend Team YAML Files

Add a `projects:` section to your existing team configuration files.

**Example**: `teams/backend-team.yaml`

```yaml
team_name: Backend Engineering Team
users:
  - alice-dev
  - bob-engineer
  - charlie-backend

# Existing repository access (unchanged)
roles:
  write:
    - observability-api
    - metrics-collector
  read:
    - shared-utils

# NEW: Project access configuration
projects:
  org_projects:
    write:
      - 1    # Main development board
      - 5    # Backend sprint planning
    read:
      - 3    # Company-wide roadmap
  repo_projects:
    admin:
      - repo: observability-api
        project: 1    # API feature tracking
```

### Step 2: Validate Configuration

Run the script in dry-run mode to validate your configuration:

```bash
# Set your GitHub token
export GITHUB_TOKEN="ghp_your_token_here"

# Validate configuration without making changes
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/ \
  --dry-run
```

**Expected output**:
```
[DRY RUN] Would add alice-dev to org project 1 with write permission
[DRY RUN] Would add alice-dev to org project 5 with write permission
[DRY RUN] Would add alice-dev to org project 3 with read permission
[DRY RUN] Would add alice-dev to repo project observability-api/1 with admin permission
...
Summary: 12 project operations planned (0 errors)
```

### Step 3: Apply Configuration

Once validated, apply the configuration:

```bash
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/
```

**Expected output**:
```
{"timestamp":"2026-03-24T19:00:00Z","resource_type":"project","project_type":"organization","project_number":1,"action":"add_collaborator","username":"alice-dev","permission":"write","result":"success"}
{"timestamp":"2026-03-24T19:00:01Z","resource_type":"project","project_type":"organization","project_number":5,"action":"add_collaborator","username":"alice-dev","permission":"write","result":"success"}
...
Summary: 12 project operations completed (0 errors)
```

---

## Common Scenarios

### Scenario 1: Grant Project Access Only (No Repository Access)

Some users may need project access without repository access (e.g., project managers).

**Configuration**: `teams/project-managers.yaml`

```yaml
team_name: Project Management Team
users:
  - pm-alice
  - pm-bob

roles: {}    # No repository access

projects:
  org_projects:
    admin:
      - 1    # Main development board
      - 5    # Backend sprint planning
      - 6    # Frontend sprint planning
    write:
      - 3    # Company-wide roadmap
```

### Scenario 2: Different Permissions Across Projects

Users can have different permission levels for different projects.

**Configuration**: `teams/devops-team.yaml`

```yaml
team_name: DevOps Team
users:
  - frank-ops
  - grace-sre

roles:
  admin:
    - observability-api
    - metrics-collector

projects:
  org_projects:
    admin:
      - 1    # Main development board (full control)
    write:
      - 5    # Backend sprint planning (can edit)
    read:
      - 3    # Company-wide roadmap (view only)
```

### Scenario 3: Repository-Level Projects

Grant access to projects associated with specific repositories.

**Configuration**: `teams/frontend-team.yaml`

```yaml
team_name: Frontend Team
users:
  - diana-ui
  - evan-frontend

roles:
  write:
    - dashboard-app

projects:
  org_projects:
    read:
      - 1    # Main development board
  repo_projects:
    write:
      - repo: dashboard-app
        project: 2    # Dashboard feature tracking
    read:
      - repo: shared-utils
        project: 1    # Shared components roadmap
```

### Scenario 4: Update Existing Permissions

To change a user's project permission, simply update the YAML file and re-run the script.

**Before**: `teams/backend-team.yaml`
```yaml
projects:
  org_projects:
    read:
      - 1    # alice-dev has read access
```

**After**: `teams/backend-team.yaml`
```yaml
projects:
  org_projects:
    write:
      - 1    # alice-dev now has write access
```

**Run**:
```bash
python -m github_collab_manager.cli --org observability-s --teams-dir teams/
```

**Output**:
```json
{"timestamp":"2026-03-24T19:00:00Z","resource_type":"project","project_type":"organization","project_number":1,"action":"update_collaborator","username":"alice-dev","permission":"write","previous_permission":"read","result":"success"}
```

---

## Verification

### Verify via GitHub UI

1. Go to your project: https://github.com/orgs/observability-s/projects/1
2. Click "..." menu → "Settings"
3. Click "Manage access"
4. Verify that users have the correct permission levels

### Verify via GraphQL API

```bash
# Query project collaborators
curl -H "Authorization: bearer $GITHUB_TOKEN" \
  -X POST \
  -d '{"query":"query{node(id:\"PVT_kwDOABCDEF4AABCD\"){...on ProjectV2{collaborators(first:10){nodes{login role}}}}}"}' \
  https://api.github.com/graphql
```

---

## Troubleshooting

### Error: "Token lacks 'project' scope"

**Problem**: Your GitHub token doesn't have the `project` scope.

**Solution**:
1. Go to https://github.com/settings/tokens
2. Update your token to include the `project` scope
3. Update your `GITHUB_TOKEN` environment variable

### Error: "Project number X not found"

**Problem**: The project number in your YAML file doesn't exist.

**Solution**:
1. Go to https://github.com/orgs/observability-s/projects
2. Find the correct project number in the URL
3. Update your YAML file with the correct number

### Error: "Repository 'repo-name' not found"

**Problem**: The repository specified for a repo project doesn't exist.

**Solution**:
1. Verify the repository name is correct
2. Ensure your token has access to the repository
3. Update your YAML file with the correct repository name

### Warning: "User X is an organization member, skipping"

**Problem**: The script only manages outside collaborators, not organization members.

**Solution**: This is expected behavior. Organization members' project access should be managed through GitHub's organization settings or teams.

---

## Best Practices

### 1. Use Dry-Run Mode First

Always validate your configuration with `--dry-run` before applying changes:

```bash
python -m github_collab_manager.cli --org observability-s --teams-dir teams/ --dry-run
```

### 2. Version Control Your Configuration

Keep your team YAML files in version control:

```bash
git add teams/
git commit -m "feat: add project access for backend team"
git push
```

### 3. Document Project Numbers

Add comments in your YAML files to document what each project number represents:

```yaml
projects:
  org_projects:
    write:
      - 1    # Main development board
      - 5    # Backend sprint planning
    read:
      - 3    # Company-wide roadmap
```

### 4. Regular Access Reviews

Periodically review project access to ensure it's still appropriate:

```bash
# Generate a report of current access
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/ \
  --dry-run > access-report.txt
```

### 5. Use Descriptive Team Names

Use clear team names that indicate the purpose:

```yaml
team_name: Backend Engineering Team  # Good
team_name: Team A                    # Bad
```

---

## Migration from Manual Management

If you're currently managing project access manually:

### Step 1: Document Current Access

1. Go to each project's settings
2. Note which users have access and their permission levels
3. Create a spreadsheet or document

### Step 2: Create YAML Configurations

Convert your documented access to YAML format:

```yaml
team_name: Existing Project Access
users:
  - user1
  - user2
projects:
  org_projects:
    write:
      - 1
      - 2
```

### Step 3: Validate with Dry-Run

Run in dry-run mode to see what changes would be made:

```bash
python -m github_collab_manager.cli --org observability-s --teams-dir teams/ --dry-run
```

### Step 4: Apply Gradually

Apply changes to one team at a time to minimize risk:

```bash
# Apply only backend team
python -m github_collab_manager.cli --org observability-s --teams-dir teams/backend-team.yaml
```

---

## Advanced Usage

### Cleanup Stale Collaborators

Remove project collaborators who are no longer in any team configuration:

```bash
# Report stale collaborators (doesn't remove)
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/ \
  --report-stale

# Remove stale collaborators
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/ \
  --cleanup-stale
```

### Process Specific Team Files

Process only specific team files:

```bash
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/backend-team.yaml teams/frontend-team.yaml
```

### JSON Output for Automation

Output structured JSON for log aggregation:

```bash
python -m github_collab_manager.cli \
  --org observability-s \
  --teams-dir teams/ \
  --format json | tee project-access.log
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the full specification: `specs/002-github-projects-access/spec.md`
3. Check the implementation plan: `specs/002-github-projects-access/plan.md`
4. Open an issue in the repository

---

**Quickstart Version**: 1.0  
**Last Updated**: 2026-03-24  
**Status**: Ready for use after implementation