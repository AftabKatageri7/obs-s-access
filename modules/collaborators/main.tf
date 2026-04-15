terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# Flatten the nested structure to create a map of collaborators
locals {
  # Transform repositories list into flat list of collaborators
  collaborators_flat = flatten([
    for repo in var.repositories : [
      for collab in repo.collaborators : {
        repository = repo.name
        username   = collab.username
        permission = collab.permission
      }
    ]
  ])
}

# Add external collaborator permissions to repositories
resource "github_repository_collaborator" "collaborator" {
  for_each = { for collab in local.collaborators_flat : "${collab.repository}-${collab.username}" => collab }

  repository                  = each.value.repository
  username                    = each.value.username
  permission                  = each.value.permission
}