# Migration Guide

This guide helps existing users upgrade to version 0.2.0 which adds GitHub Projects v2 access management capabilities.

## Overview

Version 0.2.0 introduces support for managing outside collaborator access to GitHub Projects (v2) in addition to repository access. This is a **backward-compatible** update - existing team YAML files will continue to work without any changes.

## What's New in v0.2.0

- **GitHub Projects v2 Support**: Manage collaborator access to organization-level and repository-level projects
- **Optional Projects Section**: Add a `projects:` section to team YAML files to define project access
- **Dry-run Mode**: Preview changes before applying them with `--dry-run` flag
- **Stale Collaborator Cleanup**: Remove collaborators not defined in any team file with `--remove-stale` flag
- **Enhanced Error Messages**: Comprehensive, actionable error messages for all API failures

## Breaking Changes

**None.** This release is fully backward compatible. Existing team YAML files without a `projects:` section will continue to work exactly as before.

## Upgrade Steps

### 1. Update Dependencies

If you installed via pip:

```bash
pip install --upgrade github-collab-manager
```

If you're using requirements.txt:

```bash
pip install -r requirements.txt --upgrade
```

New dependencies added:
- `gql[requests]>=3.5.0` - GraphQL client for Projects API
- `pydantic>=2.0.0` - Configuration validation
- `python-dotenv>=1.0.0` - Environment variable management

### 2. Update Your GitHub Token

To use the new Projects v2 features, your GitHub Personal Access Token needs additional scopes:

#### Required Token Scopes

**For repository access only (existing functionality):**
- `repo` (for private repositories) or `public_repo` (for public repositories only)

**For repository + project access (new functionality):**
- `repo` (for private repositories) or `public_repo` (for public repositories only)
- `project` with **read and write** permissions
- `read:org` (if managing private organization projects)

#### How to Update Your Token

1. Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click on your existing token or create a new one
3. Ensure the following scopes are enabled:
   - ✅ `repo` (or `public_repo` for public repos only)
   - ✅ `project` (read and write)
   - ✅ `read:org` (if needed for private organizations)
4. Click "Update token" or "Generate token"
5. Copy the new token and update your `.env` file or environment variable

**Important:** If you only update the scopes on an existing token, you don't need to regenerate it. However, if you create a new token, make sure to update your configuration.

### 3. Add Projects to Team YAML Files (Optional)

The `projects:` section is **completely optional**. You can continue using the tool for repository access only without any changes.

To add project access management, add a `projects:` section to your team YAML files:

#### Example: Organization-Level Projects

```yaml
team_name: "DevOps Team"
organization: "observability-s"
repositories:
  - name: "obs-s-infrastructure"
    permission: "write"
projects:
  - number: 1
    permission: "admin"
  - number: 5
    permission: "write"
members:
  - username: "alice-devops"
    role: "outside"
```

#### Example: Repository-Level Projects

```yaml
team_name: "Backend Team"
organization: "observability-s"
repositories:
  - name: "obs-s-backend"
    permission: "read"
projects:
  - number: 3
    repository: "obs-s-backend"
    permission: "write"
members:
  - username: "bob-backend"
    role: "outside"
```

#### Example: Mixed Projects

```yaml
team_name: "Full Stack Team"
organization: "observability-s"
repositories:
  - name: "obs-s-frontend"
    permission: "write"
  - name: "obs-s-backend"
    permission: "write"
projects:
  # Organization-level project
  - number: 1
    permission: "write"
  # Repository-level projects
  - number: 10
    repository: "obs-s-frontend"
    permission: "admin"
  - number: 15
    repository: "obs-s-backend"
    permission: "write"
members:
  - username: "charlie-fullstack"
    role: "outside"
```

### 4. Test with Dry-Run Mode

Before applying changes, use the new `--dry-run` flag to preview what would happen:

```bash
github-collab-manager sync teams/ --dry-run
```

This will show you:
- Which collaborators would be added/updated/removed
- Which repositories would be affected
- Which projects would be affected
- No actual changes will be made

### 5. Apply Changes

Once you're satisfied with the dry-run output, run without the flag:

```bash
github-collab-manager sync teams/
```

## New CLI Features

### Dry-Run Mode

Preview changes before applying them:

```bash
github-collab-manager sync teams/ --dry-run
```

### Stale Collaborator Cleanup

Remove collaborators not defined in any team file:

```bash
# Report stale collaborators without removing them
github-collab-manager sync teams/ --report-stale

# Remove stale collaborators
github-collab-manager sync teams/ --remove-stale

# Dry-run with stale removal
github-collab-manager sync teams/ --remove-stale --dry-run
```

### Validation Only

Validate team YAML files without making any changes:

```bash
github-collab-manager sync teams/ --validate-only
```

## Schema Changes

### New Optional Fields

The team YAML schema now includes an optional `projects:` section:

```yaml
projects:  # Optional - omit if you don't need project access
  - number: 1              # Required - project number from URL
    permission: "write"    # Required - read, write, or admin
    repository: "repo-name" # Optional - only for repository-level projects
```

### Validation Rules

- `number`: Must be a positive integer (project number from GitHub URL)
- `permission`: Must be one of: `read`, `write`, `admin` (case-insensitive)
- `repository`: Required for repository-level projects, must match a repository in the `repositories:` section

## Troubleshooting

### "Permission denied for project access"

**Cause:** Your token lacks the `project` scope.

**Solution:** Update your token to include `project` scope with read/write permissions. See [Update Your GitHub Token](#how-to-update-your-token) above.

### "Project not found"

**Cause:** The project number is incorrect, the project was deleted, or your token doesn't have access.

**Solution:**
1. Verify the project number in the GitHub URL (e.g., `/orgs/myorg/projects/42` → number is 42)
2. Check that the project exists and is not closed/archived
3. Ensure your token has access to the organization/repository

### "Repository not found" for repository-level projects

**Cause:** Repository-level projects require the repository to be listed in the `repositories:` section.

**Solution:** Add the repository to the `repositories:` section with appropriate permissions:

```yaml
repositories:
  - name: "my-repo"
    permission: "read"  # Minimum permission needed
projects:
  - number: 10
    repository: "my-repo"
    permission: "write"
```

### Token validation warnings

If you see warnings about token scopes during initialization, ensure your token has all required scopes. The tool will attempt to proceed but may fail on specific operations.

## Rollback

If you need to rollback to the previous version:

```bash
pip install github-collab-manager==0.1.0
```

Note: Version 0.1.0 does not support project access management. Your team YAML files with `projects:` sections will be ignored (but won't cause errors).

## Getting Help

- **Documentation**: See [README.md](../README.md) for complete usage examples
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- **Issues**: Report bugs at [GitHub Issues](https://github.com/observability-s/obs-s-access/issues)

## Summary

Version 0.2.0 is a **backward-compatible** release that adds powerful new project access management capabilities while maintaining full compatibility with existing configurations. You can adopt the new features at your own pace - there's no requirement to add project access if you only need repository management.

Key points:
- ✅ Existing team YAML files work without changes
- ✅ Projects section is completely optional
- ✅ Token needs additional `project` scope for new features
- ✅ New dry-run and stale cleanup features available
- ✅ Enhanced error messages for better troubleshooting

<!-- Made with Bob -->