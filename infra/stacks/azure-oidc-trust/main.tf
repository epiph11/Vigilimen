# GitHub federated credentials for Azure.
#
# ADR-007. Applied once by hand; persists. Costs nothing.
#
# Azure is the strictest of the three, and that is a feature. A federated
# identity credential matches ONE subject exactly — there is no wildcard
# syntax, so the AWS and GCP failure mode is not available here. The cost is
# one credential resource per branch or environment, and a hard limit of
# twenty per application.
#
# That limit is worth knowing before it is hit: it is a design constraint
# that pushes you toward federating on ENVIRONMENTS rather than on branches,
# which is the better shape anyway. An environment can carry required
# reviewers; a branch cannot.

terraform {
  required_version = "~> 1.9"

  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.8"
    }
  }

  backend "azurerm" {
    key = "bootstrap/azure-oidc-trust.tfstate"
  }
}

provider "azuread" {}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

data "azurerm_subscription" "current" {}

# ---------------------------------------------------------------------------
# The application and its identity
# ---------------------------------------------------------------------------

resource "azuread_application" "evidence_window" {
  display_name = "limen-evidence-window"
  description  = "Federated to GitHub Actions. Has no client secret, and must never be given one."

  # No password / no client_secret resource anywhere in this stack. That
  # absence is the whole point, and FF-03 fails the build if one appears.
}

resource "azuread_service_principal" "evidence_window" {
  client_id = azuread_application.evidence_window.client_id
}

# ---------------------------------------------------------------------------
# One credential per subject — exact match, no patterns
# ---------------------------------------------------------------------------

resource "azuread_application_federated_identity_credential" "github" {
  for_each = { for s in var.federated_subjects : s.name => s }

  application_id = azuread_application.evidence_window.id
  display_name   = each.value.name
  description    = each.value.description
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = each.value.subject
}

# ---------------------------------------------------------------------------
# What it may do
# ---------------------------------------------------------------------------

# Scoped to ONE resource group, not to the subscription. Every evidence
# window builds into that group and the group is the unit of teardown
# (scripts/sweep.sh), so scoping the role here means a federation mistake
# cannot reach anything outside the blast radius the sweep already covers.
resource "azurerm_resource_group" "evidence" {
  name     = var.evidence_resource_group
  location = var.location

  tags = {
    programme = "limen"
    managedby = "terraform"
  }
}

resource "azurerm_role_assignment" "evidence_window" {
  scope                = azurerm_resource_group.evidence.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.evidence_window.object_id
}
