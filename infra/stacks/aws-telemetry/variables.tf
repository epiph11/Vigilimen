variable "region" {
  description = "AWS region. Sydney for residency; the clock is a separate decision (ADR-010)."
  type        = string
  default     = "ap-southeast-2"
}

variable "suffix" {
  description = <<-EOT
    Short unique suffix for globally-unique names. Supply the workflow run id.

    S3 bucket names are global, and a destroyed bucket's name is not
    immediately reusable — so a second evidence window run within the same
    hour fails on a name collision unless the suffix changes.
  EOT
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{4,20}$", var.suffix))
    error_message = "Suffix must be 4-20 lowercase alphanumeric characters — S3 bucket naming rules."
  }
}
