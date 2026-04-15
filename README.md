# GitHub Organization Access Management

This Terraform configuration manages GitHub organization access control including teams and external collaborators for the observability-s organization.

## Features

- **Team Management**: Define teams and their members in a declarative way
- **External Collaborator Management**: Manage external collaborators with repository-specific permissions
- **YAML Configuration**: Define all resources in easy-to-read YAML files
- **Import Scripts**: Helper scripts to generate configuration from existing GitHub organizations

## Prerequisites

- Terraform >= 1.0
- GitHub personal access token with the following scopes:
  - `admin:org` (full control of orgs and teams)
  - `repo` (for managing collaborator access to repositories)

## Project Structure

```
.
├── main.tf                      # Main Terraform configuration
├── variables.tf                 # Input variables
├── teams.yaml                   # Teams configuration
├── collaborators.yaml           # External collaborators configuration
├── modules/
│   ├── teams/                   # Teams module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── collaborators/           # Collaborators module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── scripts/                     # Helper scripts
│   ├── generate-teams-config.py # Generate teams.yaml
│   ├── generate-collaborators-config.py # Generate collaborators.yaml
│   └── README.md                # Scripts documentation
└── README.md
```

## Quick Start

### Option A: Import Existing Organization

If you have an existing GitHub organization with teams and collaborators:

```bash
# Setup Python virtual environment
./scripts/setup-venv.sh
source venv/bin/activate

# Set your GitHub token for the import scripts
export GITHUB_TOKEN=your_token_here

# Generate configuration from existing organization
python3 scripts/generate-teams-config.py observability-s $GITHUB_TOKEN
python3 scripts/generate-collaborators-config.py observability-s $GITHUB_TOKEN

# Deactivate virtual environment
deactivate

# Review and edit the generated files as needed
vim teams.yaml
vim collaborators.yaml

# Set Terraform environment variables (recommended approach)
export TF_VAR_github_token="$GITHUB_TOKEN"
export TF_VAR_github_organization="observability-s"

# Initialize and apply
terraform init
terraform plan
terraform apply
```

**Note:** Using environment variables (`TF_VAR_*`) is more secure than storing credentials in `terraform.tfvars` files.

See [scripts/README.md](scripts/README.md) for detailed import instructions.

### Option B: Start Fresh

If you're creating a new organization or want to start from scratch:

### 1. Configure Environment Variables

Set Terraform environment variables (recommended):
```bash
export TF_VAR_github_token="your_github_token_here"
export TF_VAR_github_organization="observability-s"
```

Or alternatively, use terraform.tfvars (less secure):
```bash
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

### 2. Configure Teams

Edit `teams.yaml` to define your teams and members:

```yaml
teams:
  - name: "platform-team"
    description: "Platform engineering team"
    privacy: "closed"
    members:
      - username: "alice"
        role: "maintainer"
      - username: "bob"
        role: "member"
```

**Team Privacy Options:**
- `closed`: Visible to all organization members
- `secret`: Only visible to team members

**Member Roles:**
- `member`: Regular team member
- `maintainer`: Can manage team membership and settings

### 3. Configure External Collaborators

Edit `collaborators.yaml` to define external collaborators with repository-specific permissions:

```yaml
repositories:
  - name: "my-api"
    collaborators:
      - username: "external-contractor"
        permission: "push"
      - username: "partner-developer"
        permission: "pull"
  - name: "shared-docs"
    collaborators:
      - username: "partner-developer"
        permission: "pull"
```

**Note:** External collaborators are users from outside your organization who need access to specific repositories. GitHub does not allow adding external users to organization teams, so they must be managed separately. See [COLLABORATORS.md](COLLABORATORS.md) for detailed guidance.

**Collaborator Permission Levels:**
- `pull`: Read-only access
- `triage`: Read access + manage issues and pull requests
- `push`: Pull + push access
- `maintain`: Push + manage repository settings (without access to sensitive actions)
- `admin`: Full administrative access

### 4. Initialize and Apply

```bash
# Initialize Terraform
terraform init

# Review the planned changes
terraform plan

# Apply the configuration
terraform apply
```

## Configuration Reference

### Team Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Team name |
| `description` | string | "" | Team description |
| `privacy` | string | "closed" | Team visibility (closed/secret) |
| `members` | list(object) | [] | Team members with roles |

### Collaborator Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Repository name |
| `collaborators` | list(object) | [] | List of external collaborators |
| `username` | string | required | GitHub username |
| `permission` | string | required | Access level (pull/triage/push/maintain/admin) |

## Outputs

After applying the configuration, Terraform provides the following outputs:

- `team_ids`: Map of team names to their GitHub IDs
- `team_slugs`: Map of team names to their slugs
- `collaborator_ids`: Map of collaborator identifiers to their details

View outputs:

```bash
terraform output
```

## Managing Changes

### Adding a New Team

1. Add the team configuration to `teams.yaml`
2. Run `terraform plan` to review changes
3. Run `terraform apply` to create the team

### Adding Team Members

1. Add members to the team's `members` list in `teams.yaml`
2. Run `terraform plan` to review changes
3. Run `terraform apply` to add the members

### Managing External Collaborators

External collaborators are managed in the separate `collaborators.yaml` file. See [COLLABORATORS.md](COLLABORATORS.md) for detailed instructions on:
- Adding external collaborators
- Updating permissions
- Removing access
- Best practices and security considerations

### Removing Resources

1. Remove the configuration from the YAML file
2. Run `terraform plan` to review changes
3. Run `terraform apply` to remove the resource

## Best Practices

1. **Version Control**: Keep your Terraform configuration in version control (excluding `terraform.tfvars`)
2. **Code Review**: Review all changes with `terraform plan` before applying
3. **Secrets Management**: Never commit `terraform.tfvars` or any files containing secrets
4. **Team Structure**: Organize teams by function or project for clear permission boundaries
5. **Least Privilege**: Grant minimum necessary permissions to external collaborators
6. **Regular Audits**: Periodically review team memberships and collaborator access
7. **Access Reviews**: Remove access for users who no longer need it

## Security Considerations

- **Token Security**: Store your GitHub token securely and rotate it regularly
- **Least Privilege**: Grant minimum necessary permissions to teams and collaborators
- **Access Audits**: Regularly review team memberships and collaborator permissions
- **External Collaborators**: Be especially careful with external collaborator permissions
- **Audit Logs**: Regularly review GitHub audit logs for suspicious activity

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

```bash
# Verify your token has the correct scopes
# Check that the token hasn't expired
# Ensure the organization name is correct
```

### Team Not Found

If a team referenced doesn't exist:

1. Verify the team name matches exactly (case-sensitive)
2. Ensure the team is defined in `teams.yaml`
3. Run `terraform apply` to create teams first

### Collaborator Access Issues

If collaborators can't access repositories:

1. Verify the repository name is correct
2. Check that the collaborator has accepted the invitation
3. Ensure the permission level is appropriate
4. Verify the user is not already an organization member (use teams instead)

## Contributing

When contributing to this configuration:

1. Test changes in a non-production environment first
2. Document any new features or changes
3. Follow the existing code style and structure
4. Update this README if adding new functionality

## License

This Terraform configuration is provided as-is for managing GitHub organization access control.

## Support

For issues or questions:
- Review the Terraform GitHub provider documentation
- Check GitHub's API documentation
- Review the scripts/README.md for import tool documentation