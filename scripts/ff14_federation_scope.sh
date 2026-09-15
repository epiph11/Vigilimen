#!/usr/bin/env bash
# FF-14 — federation trust conditions stay narrow.
#
# ADR-007 names the failure mode of Sprint 1 explicitly: "a trust condition
# that is too broad rather than too narrow — which is invisible until
# someone tests it."
#
# This is the test. It is static — it reads the Terraform source rather than
# the applied state — so it catches the mistake in the pull request rather
# than after a role has already been created.
#
# Every check reads CODE, never comments or output descriptions. The first
# version of this script failed on its own explanatory comments and on the
# word "attribute_condition" appearing in an output block, which is a good
# illustration of why a grep-based check needs its input narrowed before it
# needs its patterns tightened.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
say() { printf '  %s\n' "$*"; }
bad() { printf '  ✗ %s\n' "$*"; fail=1; }

# Terraform code with comment lines and trailing comments removed.
code() {
  local f="$1"
  [ -f "$f" ] || return 1
  sed -e 's/[[:space:]]#.*$//' -e '/^[[:space:]]*#/d' "$f"
}

echo "FF-14 — federation trust scope"
echo

# ---------------------------------------------------------------------------
# AWS — a wildcard subject, or StringLike instead of StringEquals, lets any
# branch (including a fork's pull request) assume the role.
# ---------------------------------------------------------------------------
AWS_MAIN=infra/stacks/aws-oidc-trust/main.tf
if [ -f "$AWS_MAIN" ]; then
  C=$(code "$AWS_MAIN")

  if echo "$C" | grep -q 'githubusercontent.com:sub'; then
    if echo "$C" | grep -B4 'githubusercontent.com:sub' | grep -q 'StringLike'; then
      bad "AWS: the sub condition uses StringLike. Use StringEquals against explicit subjects."
    else
      say "✓ AWS: sub condition uses StringEquals"
    fi
  else
    bad "AWS: no sub condition on the trust policy — audience alone scopes nothing."
  fi

  if echo "$C" | grep -qE '"repo:[^"]*\*'; then
    bad "AWS: a literal wildcard appears in a repo subject."
  else
    say "✓ AWS: no wildcard in a repo subject"
  fi

  # The guard that survives a change of default: a variable validation that
  # refuses a wildcard before the plan is even produced.
  if code infra/stacks/aws-oidc-trust/variables.tf | grep -q 'strcontains(s, "\*")'; then
    say "✓ AWS: variable validation refuses a wildcard subject"
  else
    bad "AWS: no variable validation refusing a wildcard subject."
  fi
else
  say "· AWS federation stack not present"
fi

# ---------------------------------------------------------------------------
# GCP — a pool provider with no attribute_condition mints credentials for a
# token from ANY GitHub repository. The issuer is shared, so "this token is
# genuine" says nothing about whose it is.
# ---------------------------------------------------------------------------
GCP_MAIN=infra/stacks/gcp-oidc-trust/main.tf
if [ -f "$GCP_MAIN" ]; then
  C=$(code "$GCP_MAIN")

  if echo "$C" | grep -q 'google_iam_workload_identity_pool_provider'; then
    if echo "$C" | grep -q '^[[:space:]]*attribute_condition[[:space:]]*='; then
      say "✓ GCP: provider carries an attribute_condition"
      if echo "$C" | grep -q 'assertion.repository_owner'; then
        say "✓ GCP: attribute_condition constrains repository_owner"
      else
        bad "GCP: attribute_condition does not constrain repository_owner — it may match another account's repo."
      fi
    else
      bad "GCP: workload identity pool provider has NO attribute_condition. Any GitHub repository on earth can exchange a token here."
    fi
  fi

  # Again the guard rather than today's value.
  if code infra/stacks/gcp-oidc-trust/variables.tf | grep -q 'contains(var.roles, "roles/owner")'; then
    say "✓ GCP: variable validation refuses owner and editor"
  else
    bad "GCP: no variable validation refusing roles/owner and roles/editor."
  fi
else
  say "· GCP federation stack not present"
fi

# ---------------------------------------------------------------------------
# Azure — no wildcard syntax exists, so the risks are a deliberately widened
# subject, a client secret, or a role assigned above the evidence group.
# ---------------------------------------------------------------------------
AZ_MAIN=infra/stacks/azure-oidc-trust/main.tf
if [ -f "$AZ_MAIN" ]; then
  C=$(code "$AZ_MAIN")
  V=$(code infra/stacks/azure-oidc-trust/variables.tf || true)

  if echo "$C$V" | grep -qE 'subject[[:space:]]*=[[:space:]]*"[^"]*pull_request'; then
    bad "Azure: a federated subject accepts pull_request — a fork's PR could authenticate."
  else
    say "✓ Azure: no pull_request subject federated"
  fi

  if echo "$C" | grep -qE '(azuread_application_password|client_secret[[:space:]]*=)'; then
    bad "Azure: a client secret is created in the federation stack. Its absence is the point (ADR-007)."
  else
    say "✓ Azure: no client secret created"
  fi

  if echo "$C" | grep -qE '^[[:space:]]*scope[[:space:]]*=[[:space:]]*data\.azurerm_subscription'; then
    bad "Azure: a role is assigned at SUBSCRIPTION scope. Scope it to the evidence resource group."
  else
    say "✓ Azure: role assignment is not at subscription scope"
  fi
else
  say "· Azure federation stack not present"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "FF-14 pass — every federation trust is scoped to this repository."
else
  echo "FF-14 FAIL — a trust condition is wider than this repository."
  echo
  echo "This is the Sprint 1 failure mode named in ADR-007. It breaks nothing,"
  echo "it produces no plan diff, and nothing goes wrong until somebody notices"
  echo "they can assume the role. Fix it before apply."
fi
exit "$fail"
