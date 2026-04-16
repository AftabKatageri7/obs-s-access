terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# Create GitHub teams
resource "github_team" "team" {
  for_each = { for team in var.teams : team.name => team }

  name        = each.value.name
  description = lookup(each.value, "description", "")
  privacy     = lookup(each.value, "privacy", "closed")
}

# Add team members
resource "github_team_membership" "membership" {
  for_each = merge([
    for team in var.teams :
    lookup(team, "members", null) != null && length(lookup(team, "members", [])) > 0 ? {
      for member in team.members :
      "${team.name}-${member.username}" => {
        team_name = team.name
        username  = member.username
        role      = lookup(member, "role", "member")
      }
    } : {}
  ]...)

  team_id  = github_team.team[each.value.team_name].id
  username = each.value.username
  role     = each.value.role

  depends_on = [github_team.team]
}