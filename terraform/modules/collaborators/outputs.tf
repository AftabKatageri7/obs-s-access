output "collaborator_ids" {
  description = "Map of collaborator identifiers to their details"
  value = {
    for key, collab in github_repository_collaborator.collaborator :
    key => {
      repository = collab.repository
      username   = collab.username
      permission = collab.permission
    }
  }
}