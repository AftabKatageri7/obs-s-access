terraform {
  required_version = ">= 1.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

provider "github" {
  token = var.github_obs_s_automation_token != "" ? var.github_obs_s_automation_token : null
  owner = var.github_organization != "" ? var.github_organization : null
}

# Load configurations from YAML files
locals {
  teams_config         = yamldecode(file(var.teams_config_file))
  collaborators_config = yamldecode(file(var.collaborators_config_file))
}

# Create teams
module "teams" {
  source = "./modules/teams"

  teams = local.teams_config.teams
}

# Manage external collaborators
module "collaborators" {
  source = "./modules/collaborators"

  repositories = lookup(local.collaborators_config, "repositories", [])
}