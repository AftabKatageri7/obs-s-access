output "team_ids" {
  description = "Map of team names to their GitHub IDs"
  value = {
    for name, team in github_team.team :
    name => team.id
  }
}

output "team_slugs" {
  description = "Map of team names to their slugs"
  value = {
    for name, team in github_team.team :
    name => team.slug
  }
}

output "team_node_ids" {
  description = "Map of team names to their node IDs"
  value = {
    for name, team in github_team.team :
    name => team.node_id
  }
}