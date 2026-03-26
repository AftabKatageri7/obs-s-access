# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using the GitHub Collaborator Manager with Projects v2 support.

## Table of Contents

- [Authentication Issues](#authentication-issues)
- [Permission Errors](#permission-errors)
- [Project Access Issues](#project-access-issues)
- [Repository Access Issues](#repository-access-issues)
- [Rate Limiting](#rate-limiting)
- [Configuration Issues](#configuration-issues)
- [Network and Connectivity](#network-and-connectivity)
- [Debugging Tips](#debugging-tips)
- [FAQ](#faq)

---

## Authentication Issues

### "Authentication failed" or "Unauthorized"

**Symptoms:**
- Error message: "Authentication failed. Please verify your GitHub token is valid and not expired."
- HTTP 401 Unauthorized errors

**Causes:**
1. Invalid or expired GitHub token
2. Token not properly set in environment
3. Token revoked or deleted

**Solutions:**

1. **Verify token is set correctly:**
   ```bash
   # Check if token is set
   echo $GITHUB_TOKEN
   
   # Or check .env file
   cat .env | grep GITHUB_TOKEN
   ```

2. **Generate a new token:**
   - Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
   - Click "Generate new token" (classic) or "Generate new token" (fine-grained)
   - Select required scopes (see [Token Scopes](#required-token-scopes))
   - Copy the token and update your `.env` file:
     ```bash
     GITHUB_TOKEN=ghp_your_new_token_here
     ```

3. **Test token validity:**
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```
   Should return your user information if token is valid.

### Required Token Scopes

**For repository access only:**
- `repo` (for private repositories) or `public_repo` (for public repositories)

**For repository + project access:**
- `repo` (for private repositories) or `public_repo` (for public repositories)
- `project` with **read and write** permissions
- `read:org` (for private organization access)

**How to check token scopes:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" -I https://api.github.com/user | grep X-OAuth-Scopes
```

---

## Permission Errors

### "Permission denied for project access"

**Symptoms:**
- Error message: "Permission denied for project access. Your token must have 'project' scope (read/write) enabled."
- Operations fail with 403 Forbidden

**Causes:**
1. Token missing `project` scope
2. Token has `project` scope but only read permission (write required)
3. User doesn't have admin access to the project

**Solutions:**

1. **Update token scopes:**
   - Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
   - Edit your token
   - Enable `project` scope with **read and write** permissions
   - Save changes

2. **Verify project permissions:**
   - Go to the project on GitHub
   - Check Settings > Manage access
   - Ensure your account has admin access to manage collaborators

3. **Test with dry-run:**
   ```bash
   github-collab-manager sync teams/ --dry-run
   ```
   This will show what would happen without making changes.

### "Forbidden" or "Resource not accessible"

**Symptoms:**
- Error message: "Permission denied. Please verify your token has the required scopes."
- Cannot access organization or repository

**Causes:**
1. Token lacks required scopes for private resources
2. User not a member of the organization
3. Organization has SSO enabled but token not authorized

**Solutions:**

1. **For private organizations:**
   - Ensure token has `read:org` scope
   - Verify you're a member of the organization

2. **For SSO-enabled organizations:**
   - Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
   - Click "Configure SSO" next to your token
   - Authorize the token for your organization

3. **Verify organization access:**
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/orgs/YOUR_ORG
   ```

---

## Project Access Issues

### "Project not found"

**Symptoms:**
- Error message: "Project with ID 'XXX' not found. The project may have been deleted or your token may not have access to it."
- Project number in YAML doesn't work

**Causes:**
1. Incorrect project number
2. Project was deleted or archived
3. Project is in a different organization/repository
4. Token doesn't have access to the project

**Solutions:**

1. **Verify project number:**
   - Go to the project on GitHub
   - Check the URL: `https://github.com/orgs/ORG/projects/NUMBER`
   - The number at the end is what you need in your YAML

2. **Check project status:**
   - Ensure project is not closed or archived
   - Open projects have a green "Open" badge

3. **Verify project location:**
   - **Organization-level projects:** Don't include `repository` field
   - **Repository-level projects:** Must include `repository` field matching a repo in your YAML

4. **Test project access:**
   ```bash
   # List organization projects
   github-collab-manager sync teams/ --validate-only
   ```

### "Repository not found" for repository-level projects

**Symptoms:**
- Error message: "Repository 'owner/repo' not found."
- Repository-level project access fails

**Causes:**
1. Repository not listed in `repositories:` section
2. Incorrect repository name
3. Token doesn't have access to repository

**Solutions:**

1. **Add repository to YAML:**
   ```yaml
   repositories:
     - name: "my-repo"
       permission: "pull"  # Minimum permission needed
   projects:
     - number: 10
       repository: "my-repo"  # Must match repository name above
       permission: "write"
   ```

2. **Verify repository name:**
   - Check exact spelling and capitalization
   - Repository name should not include owner (just "repo", not "owner/repo")

3. **Test repository access:**
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/OWNER/REPO
   ```

### Project collaborator already has access

**Symptoms:**
- Warning: "Collaborator already has access to project"
- No error, but permission not updated

**Causes:**
1. Collaborator already has the same or higher permission
2. Collaborator is an organization member (not outside collaborator)

**Solutions:**

1. **Check current permissions:**
   - Go to project Settings > Manage access
   - Verify current collaborator permissions

2. **Note:** This tool only manages **outside collaborators**, not organization members. Organization members' project access is managed through organization settings.

---

## Repository Access Issues

### "Repository not found"

**Symptoms:**
- Error message: "Repository 'owner/repo' not found."
- Cannot access repository

**Causes:**
1. Incorrect repository name or owner
2. Repository is private and token lacks access
3. Repository was deleted or renamed

**Solutions:**

1. **Verify repository exists:**
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/OWNER/REPO
   ```

2. **Check repository name:**
   - Verify spelling and capitalization
   - Check if repository was renamed

3. **For private repositories:**
   - Ensure token has `repo` scope
   - Verify you have access to the repository

### "User not found"

**Symptoms:**
- Error message: "User 'username' not found on GitHub."
- Cannot add collaborator

**Causes:**
1. Username misspelled
2. User account doesn't exist
3. User account was deleted or renamed

**Solutions:**

1. **Verify username:**
   - Check spelling and capitalization
   - Visit `https://github.com/USERNAME` to verify account exists

2. **Check user type:**
   - This tool only works with **user accounts**, not organization accounts
   - For organization members, use GitHub's organization settings

---

## Rate Limiting

### "GitHub API rate limit exceeded"

**Symptoms:**
- Error message: "GitHub API rate limit exceeded. Please wait a few minutes before retrying."
- Operations slow down or fail

**Causes:**
1. Too many API requests in short time
2. Authenticated rate limit (5000/hour) exceeded
3. Secondary rate limits triggered

**Solutions:**

1. **Wait for rate limit reset:**
   - Check when rate limit resets:
     ```bash
     curl -H "Authorization: token $GITHUB_TOKEN" -I https://api.github.com/user | grep X-RateLimit
     ```
   - Wait until `X-RateLimit-Reset` time

2. **Reduce request frequency:**
   - Process fewer teams at once
   - Use `--dry-run` to test without consuming rate limit
   - Batch operations when possible

3. **Monitor rate limits:**
   - Tool logs warnings when rate limit is low
   - Check logs for rate limit information

### Secondary rate limits

**Symptoms:**
- Error message: "Rate limit hit, retrying in Xs..."
- Automatic retries with exponential backoff

**Causes:**
1. Too many concurrent requests
2. Too many requests to same endpoint

**Solutions:**
- Tool automatically handles retries with exponential backoff
- If persistent, reduce operation frequency
- Wait a few minutes between large operations

---

## Configuration Issues

### YAML syntax errors

**Symptoms:**
- Error message: "Error parsing YAML file"
- Configuration not loaded

**Causes:**
1. Invalid YAML syntax
2. Incorrect indentation
3. Missing required fields

**Solutions:**

1. **Validate YAML syntax:**
   ```bash
   # Use online validator or Python
   python -c "import yaml; yaml.safe_load(open('teams/team.yaml'))"
   ```

2. **Check indentation:**
   - Use spaces, not tabs
   - Consistent indentation (2 or 4 spaces)

3. **Verify required fields:**
   ```yaml
   team_name: "Required"
   organization: "Required"
   members:  # Required, at least one member
     - username: "required"
       role: "outside"  # Required
   ```

### Invalid permission values

**Symptoms:**
- Error message: "Invalid permission value"
- Configuration validation fails

**Causes:**
1. Incorrect permission value
2. Typo in permission name

**Solutions:**

1. **Repository permissions:** Must be one of:
   - `pull` (read-only)
   - `push` (read-write)
   - `admin` (full access)

2. **Project permissions:** Must be one of:
   - `read` (read-only)
   - `write` (read-write)
   - `admin` (full access)

3. **Case-insensitive:** Permissions are case-insensitive (`READ`, `read`, `Read` all work)

### Missing environment variables

**Symptoms:**
- Error message: "GITHUB_TOKEN environment variable not set"
- Tool cannot authenticate

**Solutions:**

1. **Set environment variable:**
   ```bash
   export GITHUB_TOKEN=ghp_your_token_here
   ```

2. **Use .env file:**
   ```bash
   echo "GITHUB_TOKEN=ghp_your_token_here" > .env
   ```

3. **Verify .env file is loaded:**
   - Ensure `.env` file is in the current directory
   - Check file permissions (should be readable)

---

## Network and Connectivity

### "Network connection error"

**Symptoms:**
- Error message: "Network connection error. Please check your internet connection."
- Timeouts or connection refused

**Causes:**
1. No internet connection
2. Firewall blocking GitHub API
3. Proxy configuration issues
4. GitHub API temporarily unavailable

**Solutions:**

1. **Check internet connection:**
   ```bash
   ping github.com
   ```

2. **Test GitHub API access:**
   ```bash
   curl https://api.github.com
   ```

3. **Check proxy settings:**
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   ```

4. **Verify GitHub status:**
   - Visit [GitHub Status](https://www.githubstatus.com/)
   - Check for ongoing incidents

### SSL/TLS certificate errors

**Symptoms:**
- Error message: "SSL certificate verification failed"
- HTTPS connection errors

**Causes:**
1. Outdated CA certificates
2. Corporate proxy with SSL inspection
3. System time incorrect

**Solutions:**

1. **Update CA certificates:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # macOS
   brew install ca-certificates
   ```

2. **For corporate proxies:**
   - Install corporate CA certificate
   - Configure proxy settings

3. **Check system time:**
   ```bash
   date
   ```
   Ensure system time is correct.

---

## Debugging Tips

### Enable verbose logging

Set log level to DEBUG for detailed output:

```bash
export LOG_LEVEL=DEBUG
github-collab-manager sync teams/
```

### Use dry-run mode

Preview changes without applying them:

```bash
github-collab-manager sync teams/ --dry-run
```

### Validate configuration only

Check YAML files without making API calls:

```bash
github-collab-manager sync teams/ --validate-only
```

### Test with single team file

Isolate issues by testing one team at a time:

```bash
github-collab-manager sync teams/single-team.yaml
```

### Check API responses

Use curl to test API endpoints directly:

```bash
# Test authentication
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Test organization access
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/orgs/YOUR_ORG

# Test repository access
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/repos/OWNER/REPO
```

### Review audit logs

Check audit logs for detailed operation history:

```bash
# Logs are written to audit.log by default
tail -f audit.log
```

---

## FAQ

### Q: Can I manage organization members with this tool?

**A:** No, this tool only manages **outside collaborators**. Organization members' access is managed through GitHub's organization settings.

### Q: Do I need to add projects to my YAML files?

**A:** No, the `projects:` section is completely optional. If you only need repository access management, you can omit it entirely.

### Q: Can I use the same token for multiple organizations?

**A:** Yes, as long as the token has access to all organizations and the required scopes are enabled.

### Q: What happens if I remove a collaborator from all team files?

**A:** By default, nothing. Use `--remove-stale` flag to automatically remove collaborators not defined in any team file.

### Q: Can I manage both public and private repositories?

**A:** Yes, but your token needs `repo` scope for private repositories. For public repositories only, `public_repo` scope is sufficient.

### Q: How do I find a project's number?

**A:** Look at the project URL on GitHub:
- Organization project: `https://github.com/orgs/ORG/projects/42` → number is `42`
- Repository project: `https://github.com/OWNER/REPO/projects/15` → number is `15`

### Q: Can I manage classic GitHub Projects (v1)?

**A:** No, this tool only supports GitHub Projects v2 (the new project experience). Classic projects use a different API.

### Q: What's the difference between organization and repository projects?

**A:** 
- **Organization projects:** Attached to the organization, accessible without repository access
- **Repository projects:** Attached to a specific repository, require repository access

### Q: How do I handle conflicts between team files?

**A:** Team files are processed in alphabetical order. The last file processed wins. Use unique team names and avoid overlapping definitions.

### Q: Can I use wildcards in repository names?

**A:** No, repository names must be exact matches. Wildcards are not supported.

### Q: How often should I run the sync command?

**A:** It depends on your needs. Common patterns:
- **Manual:** Run when team changes occur
- **Scheduled:** Daily or weekly via cron/CI
- **On-demand:** As part of onboarding/offboarding process

---

## Getting More Help

If you're still experiencing issues:

1. **Check the logs:** Review `audit.log` for detailed error messages
2. **Search existing issues:** [GitHub Issues](https://github.com/observability-s/obs-s-access/issues)
3. **Create a new issue:** Include:
   - Error message (sanitize tokens!)
   - Steps to reproduce
   - YAML configuration (sanitize sensitive data)
   - Log output with DEBUG level
4. **Read the documentation:** [README.md](../README.md) and [MIGRATION.md](MIGRATION.md)

---

## Quick Reference

### Common Commands

```bash
# Sync all teams
github-collab-manager sync teams/

# Dry-run (preview changes)
github-collab-manager sync teams/ --dry-run

# Remove stale collaborators
github-collab-manager sync teams/ --remove-stale

# Validate configuration only
github-collab-manager sync teams/ --validate-only

# Report stale collaborators
github-collab-manager sync teams/ --report-stale
```

### Environment Variables

```bash
# Required
export GITHUB_TOKEN=ghp_your_token_here

# Optional
export LOG_LEVEL=DEBUG
export GITHUB_API_URL=https://api.github.com
```

### Token Scopes Quick Reference

| Feature | Required Scopes |
|---------|----------------|
| Public repository access | `public_repo` |
| Private repository access | `repo` |
| Organization projects | `project` (read/write), `read:org` |
| Repository projects | `project` (read/write), `repo` |

<!-- Made with Bob -->