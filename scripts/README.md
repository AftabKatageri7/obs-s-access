# Helper Scripts

This directory contains helper scripts to import existing GitHub organization resources into Terraform configuration.

## Prerequisites

- Python 3.x
- GitHub personal access token with appropriate permissions

## Quick Setup with Virtual Environment (Recommended)

Use the provided setup script to create an isolated Python environment:

```bash
# Run the setup script
./scripts/setup-venv.sh

# Activate the virtual environment
source venv/bin/activate

# Now you can run the scripts
python3 scripts/generate-teams-config.py observability-s $GITHUB_TOKEN > teams.yaml

# When done, deactivate
deactivate
```

## Manual Installation

If you prefer to install dependencies globally or in your own environment:

```bash
pip install -r requirements.txt
```

Or install packages directly:
```bash
pip install requests pyyaml
```

## Scripts

### 1. fetch-repos.sh

Simple bash script to list all repositories in an organization.

**Usage:**
```bash
./scripts/fetch-repos.sh observability-s YOUR_GITHUB_TOKEN
```

Or with environment variable:
```bash
export GITHUB_TOKEN=your_token_here
./scripts/fetch-repos.sh observability-s
```

### 2. generate-repo-config.py

Generate `repositories.yaml` from existing GitHub organization repositories.

**Usage:**
```bash
python3 scripts/generate-repo-config.py observability-s YOUR_GITHUB_TOKEN
```

This script will:
- Fetch all repositories from the organization
- Retrieve current settings for each repository
- Fetch team permissions for each repository
- Generate a complete `repositories.yaml` configuration
- **Prompt you to save the output to `repositories.yaml`**

**Note:** The script sets `auto_init: false` for existing repositories to prevent re-initialization.

**Interactive Features:**
- Prompts to save directly to `repositories.yaml` in the parent directory
- Warns if the file already exists and asks for confirmation to overwrite
- Falls back to stdout if you decline to save

### 3. generate-teams-config.py

Generate `teams.yaml` from existing GitHub organization teams.

**Usage:**
```bash
python3 scripts/generate-teams-config.py observability-s YOUR_GITHUB_TOKEN
```

This script will:
- Fetch all teams from the organization
- Retrieve team members and their roles
- Generate a complete `teams.yaml` configuration
- **Prompt you to save the output to `teams.yaml`**

**Interactive Features:**
- Prompts to save directly to `teams.yaml` in the parent directory
- Warns if the file already exists and asks for confirmation to overwrite
- Falls back to stdout if you decline to save

### 4. generate-collaborators-config.py

Generate `collaborators.yaml` from existing GitHub repository collaborators.

**Usage:**
```bash
python3 scripts/generate-collaborators-config.py observability-s YOUR_GITHUB_TOKEN
```

This script will:
- Fetch all repositories from the organization
- Retrieve external collaborators for each repository (excluding organization members)
- Fetch permission levels for each collaborator
- Generate a complete `collaborators.yaml` configuration
- **Prompt you to save the output to `collaborators.yaml`**

**Interactive Features:**
- Prompts to save directly to `collaborators.yaml` in the parent directory
- Warns if the file already exists and asks for confirmation to overwrite
- Falls back to stdout if you decline to save
- Automatically filters out organization members (only external collaborators are included)

**Note:** This script only captures external collaborators (users not in the organization). Organization members should be managed through teams in `teams.yaml`.

## Complete Workflow

To import your existing GitHub organization into Terraform:

```bash
# 1. Setup Python virtual environment
./scripts/setup-venv.sh
source venv/bin/activate

# 2. Set your GitHub token
export GITHUB_TOKEN=your_token_here
ORG_NAME=observability-s

# 3. Generate teams configuration (will prompt to save)
python3 scripts/generate-teams-config.py $ORG_NAME $GITHUB_TOKEN

# 4. Generate repositories configuration (will prompt to save)
python3 scripts/generate-repo-config.py $ORG_NAME $GITHUB_TOKEN

# 5. Generate collaborators configuration (will prompt to save)
python3 scripts/generate-collaborators-config.py $ORG_NAME $GITHUB_TOKEN

# 6. Deactivate virtual environment
deactivate

# 7. Review the generated files
cat teams.yaml
cat repositories.yaml
cat collaborators.yaml

# 8. Configure Terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 9. Initialize Terraform
terraform init

# 10. Import existing resources (recommended)
# Use the automated import script
python3 scripts/import-resources.py $ORG_NAME

# 11. Plan and apply
terraform plan
terraform apply
```

## Automated Import Script

The `import-resources.py` script automates the import of existing GitHub resources into Terraform state:

```bash
# Set your GitHub token
export GITHUB_TOKEN=your_token_here

# Run the import script
python3 scripts/import-resources.py observability-s
```

This script will automatically import:
- Teams
- Team members
- Repositories
- Team repository permissions
- Repository collaborators

**Note:** The script checks if resources are already in state before importing to avoid errors.

## Manual Import (Alternative)

If you prefer to import resources manually:

```bash
# Import teams
terraform import 'module.teams.github_team.teams["team-name"]' team-id

# Import repositories
terraform import 'module.repositories["repo-name"].github_repository.repo' repo-name

# Import team repository permissions
terraform import 'module.repositories["repo-name"].github_team_repository.team_repo["team-name"]' team-id:repo-name

# Import collaborators
terraform import 'module.collaborators.github_repository_collaborator.collaborator["repo-name-username"]' repo-name:username
```

You can get team IDs and other information from the GitHub API or by running:
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/orgs/$ORG_NAME/teams
```

## Troubleshooting

### Rate Limiting

If you hit GitHub API rate limits:
- Wait for the rate limit to reset (check headers in error response)
- Use a token with higher rate limits
- The scripts will show the error message from GitHub

### Authentication Errors

If you get 401 or 403 errors:
- Verify your token is valid
- Ensure the token has the required scopes:
  - `repo` (full control)
  - `admin:org` (read:org at minimum)
  - `read:user` for user information

### Missing Dependencies

If you get import errors:
```bash
pip install requests pyyaml
```

Or use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install requests pyyaml
```

## Security Notes

- Never commit your GitHub token to version control
- Use environment variables for tokens
- Rotate tokens regularly
- Use tokens with minimum required permissions