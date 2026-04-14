# Importing Existing GitHub Access Resources into Terraform

This guide will help you safely import your existing GitHub organization teams and external collaborators into Terraform state, avoiding recreation of existing resources.

## Overview

When Terraform doesn't know about existing resources, it tries to create them, which can cause:
- Errors (resources already exist)
- Unwanted recreation
- Loss of existing data

The solution is to **import** existing resources into Terraform state before running `terraform apply`.

## Prerequisites

1. Ensure your configuration files match your actual GitHub organization
2. Run `terraform init` first
3. Have your GitHub token ready with appropriate permissions (`admin:org` scope)

## Import Process

### Step 1: Verify Configuration Matches Reality

Before importing, ensure your YAML files accurately reflect your current GitHub setup:

```bash
# Review teams
cat teams.yaml

# Review collaborators
cat collaborators.yaml
```

### Step 2: Import Teams

For each team in `teams.yaml`, run:

```bash
# Get team ID from GitHub API
TEAM_ID=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/orgs/observability-s/teams" | \
  jq -r '.[] | select(.name=="TEAM_NAME") | .id')

# Import the team
terraform import 'module.teams.github_team.team["TEAM_NAME"]' $TEAM_ID
```

**Example:**
```bash
# Import IBM-Maintainers team
TEAM_ID=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/orgs/observability-s/teams" | \
  jq -r '.[] | select(.name=="IBM-Maintainers") | .id')

terraform import 'module.teams.github_team.team["IBM-Maintainers"]' $TEAM_ID
```

### Step 3: Import Team Members

For each team member:

```bash
terraform import 'module.teams.github_team_membership.membership["TEAM_NAME-USERNAME"]' TEAM_ID:USERNAME
```

**Example:**
```bash
# Import haberc as member of IBM-Maintainers team
terraform import 'module.teams.github_team_membership.membership["IBM-Maintainers-haberc"]' 12345:haberc
```

### Step 4: Import External Collaborators

For each external collaborator defined in `collaborators.yaml`:

```bash
terraform import 'module.collaborators.github_repository_collaborator.collaborator["REPO_NAME-USERNAME"]' REPO_NAME:USERNAME
```

**Example:**
```bash
# Import jdeiviz as collaborator on sysdig-support repository
terraform import 'module.collaborators.github_repository_collaborator.collaborator["sysdig-support-jdeiviz"]' sysdig-support:jdeiviz
```

## Automated Import Script

We've created a Python script to automate this process. See `scripts/import-resources.py`.

### Usage:

```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Set your GitHub token
export GITHUB_TOKEN=your_token_here

# Run the import script
python3 scripts/import-resources.py observability-s

# Or make it executable and run directly
chmod +x scripts/import-resources.py
./scripts/import-resources.py observability-s
```

The script will:
1. Read your `teams.yaml` and `collaborators.yaml` files
2. Fetch resource IDs from GitHub API
3. Generate and execute import commands
4. Show progress and any errors

## Verification

After importing, verify the state:

```bash
# Check what's in state
terraform state list

# Run plan to see if anything needs to change
terraform plan
```

**Expected Result:** `terraform plan` should show minimal or no changes if your configuration matches reality.

## Common Issues

### Issue: "Resource already exists"
**Solution:** The resource needs to be imported first. Use the import commands above.

### Issue: "No changes" but resources aren't in state
**Solution:** Run `terraform state list` to verify. If empty, imports didn't work. Check resource names match exactly.

### Issue: Plan shows many changes after import
**Solution:** Your configuration doesn't match reality. Common mismatches:
- Team member roles (maintainer vs member)
- Team privacy settings (closed vs secret)
- Collaborator permissions (pull, push, maintain, admin)

Review the plan output carefully and adjust your YAML files to match actual settings.

### Issue: Import fails with "resource not found"
**Solution:** 
- Verify the resource exists in GitHub
- Check spelling of names (case-sensitive)
- Ensure your token has correct permissions (`admin:org` scope)
- For collaborators, verify the repository name is correct

### Issue: Collaborator import fails
**Solution:**
- Verify the user is actually an external collaborator (not an org member)
- Check that the repository exists
- Ensure the collaborator has accepted the invitation
- Verify your token has `repo` scope for private repositories

## Selective Import

If you only want to manage certain resources:

1. Remove unwanted resources from YAML files
2. Only import the resources you want to manage
3. Terraform will ignore resources not in your configuration

**Example:** To manage only specific teams:
```yaml
# teams.yaml - only include teams you want to manage
teams:
  - name: "IBM-Maintainers"
    # ... rest of config
```

## Rollback Plan

If something goes wrong:

```bash
# Backup your state file first
cp terraform.tfstate terraform.tfstate.backup

# If needed, remove all state
rm terraform.tfstate terraform.tfstate.backup

# Start over with imports
```

## Best Practices

1. **Test in a non-production org first** if possible
2. **Backup your state file** before major operations
3. **Import incrementally** - start with teams, then members, then collaborators
4. **Verify each step** with `terraform plan` before proceeding
5. **Use version control** for your Terraform files
6. **Document any manual changes** needed after import
7. **Use remote state** for team collaboration (see README.md)

## Resource Address Reference

Quick reference for import commands:

| Resource Type | Address Format | ID Format |
|--------------|----------------|-----------|
| Team | `module.teams.github_team.team["TEAM_NAME"]` | `TEAM_ID` |
| Team Member | `module.teams.github_team_membership.membership["TEAM_NAME-USERNAME"]` | `TEAM_ID:USERNAME` |
| Collaborator | `module.collaborators.github_repository_collaborator.collaborator["REPO_NAME-USERNAME"]` | `REPO_NAME:USERNAME` |

## Next Steps

After successful import:

1. Run `terraform plan` to verify no unwanted changes
2. If plan looks good, you can now use `terraform apply` for future changes
3. Commit your Terraform files to version control
4. Set up remote state backend for team collaboration (see README.md)
5. Set up CI/CD for automated Terraform runs (optional)

## Getting Help

If you encounter issues:

1. Check the error message carefully
2. Verify resource names match exactly (case-sensitive)
3. Ensure your GitHub token has all required permissions
4. Review the Terraform GitHub provider documentation
5. Check GitHub API responses for the actual resource structure
6. Use `terraform state list` to see what's currently imported
7. Use `terraform state show <resource>` to inspect specific resources