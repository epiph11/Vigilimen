variable "subscription_id" {
  description = "Azure subscription id."
  type        = string
}

variable "location" {
  description = "australiaeast — New South Wales. Region is residency, not the clock (ADR-010)."
  type        = string
  default     = "australiaeast"
}

variable "evidence_resource_group" {
  description = "The single resource group every evidence window builds into. scripts/sweep.sh deletes this group as its unit of teardown, so nothing else may live here."
  type        = string
  default     = "rg-VIGILIMEN-evidence"
}

variable "federated_subjects" {
  description = <<-EOT
    Federated identity credentials, one per subject. Azure matches the
    subject EXACTLY — there is no wildcard syntax, which removes the
    failure mode that AWS trust policies and GCP attribute conditions both
    have.

    Subject forms:
      repo:<owner>/<repo>:ref:refs/heads/main
      repo:<owner>/<repo>:environment:evidence
      repo:<owner>/<repo>:pull_request

    Prefer the environment form. An environment can require a reviewer
    before the workflow runs; a branch cannot. Twenty credentials is the
    hard limit per application, and that limit is a nudge toward
    environments rather than a problem to work around.

    Do NOT add the pull_request form unless you intend a fork's PR to be
    able to assume this identity.
  EOT

  type = list(object({
    name        = string
    subject     = string
    description = optional(string, "Federated credential for the evidence-window workflow")
  }))

  validation {
    condition     = length(var.federated_subjects) > 0
    error_message = "At least one federated credential is required, or the workflow can never authenticate."
  }

  validation {
    condition     = length(var.federated_subjects) <= 20
    error_message = "Azure allows at most 20 federated identity credentials per application. Federate on environments rather than on branches."
  }

  validation {
    condition     = alltrue([for s in var.federated_subjects : startswith(s.subject, "repo:")])
    error_message = "Each subject must begin with 'repo:<owner>/<repo>:'."
  }

  validation {
    condition     = alltrue([for s in var.federated_subjects : !strcontains(s.subject, "*")])
    error_message = "Azure does not support wildcards in a federated subject, and a literal asterisk would simply never match. List each subject explicitly."
  }
}
