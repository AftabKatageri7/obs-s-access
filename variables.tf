variable "github_obs_s_automation_token" {
  description = "GitHub personal access token with appropriate permissions for observability-s automation"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_organization" {
  description = "GitHub organization name"
  type        = string
  default     = "observability-s"
}

variable "teams_config_file" {
  description = "Path to the YAML file containing team configurations"
  type        = string
  default     = "teams.yaml"
}

variable "collaborators_config_file" {
  description = "Path to the YAML file containing external collaborator configurations"
  type        = string
  default     = "collaborators.yaml"
}