variable "repositories" {
  description = "List of repositories with their external collaborators"
  type = list(object({
    name = string
    collaborators = list(object({
      username   = string
      permission = string
    }))
  }))
  default = []
}