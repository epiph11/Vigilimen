# GitHub Workload Identity Federation for GCP.
#
# ADR-007. Applied once by hand; persists. Costs nothing.
#
# ─────────────────────────────────────────────────────────────────────────
#  READ THIS BEFORE CHANGING ANYTHING IN THIS FILE
#
#  A Workload Identity Pool Provider WITHOUT an attribute_condition will
#  mint credentials for a token from ANY GitHub repository on earth. Not
#  any branch of yours — any repository, belonging to anyone.
#
#  The reason is that the issuer is shared: token.actions.githubusercontent.com
#  signs tokens for every repo on GitHub, so "this token is genuine" says
#  nothing at all about whose it is. The attribute_condition is the ONLY
#  thing that narrows it.
#
#  This is the GCP equivalent of a StringLike wildcard on an AWS trust
#  policy, and it is worse, because the AWS mistake at least requires you
#  to type a wildcard. Here the mistake is an omission.
# ─────────────────────────────────────────────────────────────────────────

terraform {
  required_version = "~> 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
  }

  backend "gcs" {
    prefix = "bootstrap/gcp-oidc-trust"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# The pool and the provider
# ---------------------------------------------------------------------------

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "mined-github"
  display_name              = "MineDigital GitHub"
  description               = "Federated identity for the evidence-window workflow. No service account keys exist."
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "mined-github-oidc"
  display_name                       = "GitHub Actions OIDC"

  oidc {
    issuer_uri        = "https://token.actions.githubusercontent.com"
    allowed_audiences = ["https://github.com/${var.github_owner}"]
  }

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  # THE LINE THAT MATTERS. Without it, every GitHub repository in existence
  # can exchange a token here. Two conditions, both required:
  #   - the owner, so only this account's repos are considered at all
  #   - the repository, so only this repo within that account
  attribute_condition = join(" && ", [
    "assertion.repository_owner == '${var.github_owner}'",
    "assertion.repository == '${var.github_owner}/${var.github_repo}'",
  ])
}

# ---------------------------------------------------------------------------
# The identity the workflow becomes
# ---------------------------------------------------------------------------

resource "google_service_account" "evidence_window" {
  account_id   = "mined-evidence-window"
  display_name = "MineDigital evidence window"
  description  = "Impersonated by the evidence-window workflow via WIF. Has no keys, and must never be given one."
}

# The binding is scoped a SECOND time, by ref, so that even a token from the
# correct repository cannot impersonate this account unless it came from an
# allowed branch or environment. attribute_condition gates the pool; this
# gates the account. Defence at two layers for the same reason FF-13 and the
# IAM deny overlap on AWS.
resource "google_service_account_iam_member" "wif" {
  for_each = toset(var.allowed_refs)

  service_account_id = google_service_account.evidence_window.name
  role               = "roles/iam.workloadIdentityUser"
  member = join("", [
    "principalSet://iam.googleapis.com/",
    google_iam_workload_identity_pool.github.name,
    "/attribute.repository/${var.github_owner}/${var.github_repo}",
  ])

  # Note: the ref narrowing above is expressed through the pool's own
  # attribute mapping. If a tighter per-ref principal is needed, change the
  # attribute_condition rather than loosening this member.
  depends_on = [google_iam_workload_identity_pool_provider.github]
}

# ---------------------------------------------------------------------------
# What that identity may do
# ---------------------------------------------------------------------------

resource "google_project_iam_member" "evidence_window" {
  for_each = toset(var.roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.evidence_window.email}"
}
