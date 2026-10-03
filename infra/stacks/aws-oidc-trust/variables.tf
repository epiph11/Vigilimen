variable "region" {
  description = "AWS region. Sydney — region is chosen for residency and service availability, not for what a clock displays (ADR-010)."
  type        = string
  default     = "ap-southeast-2"
}

variable "allowed_subjects" {
  description = <<-EOT
    Exact OIDC subject claims permitted to assume the evidence-window role.

    Each entry is matched with StringEquals, never StringLike. A wildcard
    here would let any branch — including a branch pushed to a fork in a
    pull request — assume the role.

    Form: repo:<owner>/<repo>:ref:refs/heads/master
       or repo:<owner>/<repo>:environment:evidence
  EOT
  type        = list(string)

  validation {
    condition     = length(var.allowed_subjects) > 0
    error_message = "At least one subject must be allowed, or the role can never be assumed."
  }

  validation {
    condition     = alltrue([for s in var.allowed_subjects : !strcontains(s, "*")])
    error_message = "A wildcard in an OIDC subject grants the role to branches you do not control. List each subject explicitly."
  }

  validation {
    condition     = alltrue([for s in var.allowed_subjects : startswith(s, "repo:")])
    error_message = "Each subject must begin with 'repo:<owner>/<repo>:'."
  }
}
