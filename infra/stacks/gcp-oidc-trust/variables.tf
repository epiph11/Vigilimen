variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  description = "Sydney. Region is residency and service availability, not the clock (ADR-010)."
  type        = string
  default     = "australia-southeast1"
}

variable "github_owner" {
  description = "GitHub account or organisation that owns the repository."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$", var.github_owner))
    error_message = "Must be a literal GitHub owner name. A pattern here would widen the attribute_condition, which is the one thing standing between this pool and every repository on GitHub."
  }
}

variable "github_repo" {
  description = "Repository name, without the owner."
  type        = string

  validation {
    condition     = !strcontains(var.github_repo, "*") && !strcontains(var.github_repo, "/")
    error_message = "Repository must be a bare name with no wildcard and no owner prefix."
  }
}

variable "allowed_refs" {
  description = <<-EOT
    Git refs permitted to impersonate the evidence-window service account.

    Form: refs/heads/main

    Kept as an explicit list rather than a pattern. The cost of listing
    three refs is three lines; the cost of a pattern that turns out to
    match a fourth is a credential you did not intend to issue.
  EOT
  type        = list(string)
  default     = ["refs/heads/main"]

  validation {
    condition     = length(var.allowed_refs) > 0
    error_message = "At least one ref must be allowed."
  }

  validation {
    condition     = alltrue([for r in var.allowed_refs : startswith(r, "refs/")])
    error_message = "Each ref must be fully qualified, e.g. refs/heads/main."
  }
}

variable "roles" {
  description = <<-EOT
    Project roles granted to the evidence-window service account.

    Deliberately NOT roles/editor. Editor is what every quickstart uses and
    it includes permissions this workflow will never need, on services it
    will never touch — which makes the blast radius of a federation mistake
    the whole project rather than one stack.
  EOT
  type        = list(string)
  default = [
    "roles/storage.admin",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/logging.viewer",
  ]

  validation {
    condition     = !contains(var.roles, "roles/owner") && !contains(var.roles, "roles/editor")
    error_message = "roles/owner and roles/editor are refused. Grant the specific roles the stack needs and add to this list when a stack genuinely needs more."
  }
}
