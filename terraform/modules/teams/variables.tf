variable "teams" {
  description = "List of teams to create with their members"
  type = list(object({
    name        = string
    description = optional(string)
    privacy     = optional(string)
    members = optional(list(object({
      username = string
      role     = optional(string)
    })))
  }))
}