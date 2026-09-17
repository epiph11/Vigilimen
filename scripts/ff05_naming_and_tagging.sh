#!/usr/bin/env bash
# FF-05 — naming and tagging standard.
#
# The sweep (scripts/sweep.sh) and the verification (verify_empty.sh) both
# key off a tag. A resource created without that tag is invisible to both,
# which means it survives the evidence window and bills until somebody
# notices — and nobody notices, because nothing reports it.
#
# So this is not a tidiness check. The tag IS the teardown mechanism, and
# this fitness function is what stops the teardown mechanism from having
# holes in it.
#
# Every check reads code, not comments.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
say() { printf '  %s\n' "$*"; }
bad() { printf '  ✗ %s\n' "$*"; fail=1; }

code() { sed -e 's/[[:space:]]#.*$//' -e '/^[[:space:]]*#/d' "$1"; }

echo "FF-05 — naming and tagging standard"
echo

STACKS=$(find infra/stacks -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)
if [ -z "$STACKS" ]; then
  echo "  no stacks found — nothing to check, which is not the same as a pass"
  exit 1
fi

for dir in $STACKS; do
  stack=$(basename "$dir")
  main="$dir/main.tf"
  [ -f "$main" ] || { bad "$stack: no main.tf"; continue; }
  C=$(code "$main")

  # ---- is this stack ephemeral or bootstrap? -----------------------------
  # Bootstrap stacks (the federation trusts) persist deliberately and must
  # NOT carry the ephemeral tag — the sweep must never delete the thing that
  # grants the sweep its permissions.
  case "$stack" in
    *oidc-trust) kind=bootstrap ;;
    *)           kind=ephemeral ;;
  esac

  # ---- provider-level default tagging ------------------------------------
  if echo "$C" | grep -q 'provider "aws"'; then
    if echo "$C" | grep -q 'default_tags'; then
      say "✓ $stack: aws provider sets default_tags"
    else
      bad "$stack: aws provider has no default_tags — a resource whose own tag block is forgotten is invisible to the sweep."
    fi
  fi

  # ---- the ephemeral marker ----------------------------------------------
  if [ "$kind" = ephemeral ]; then
    if echo "$C" | grep -qE '"VIGILIMEN-ephemeral"|VIGILIMEN-ephemeral'; then
      say "✓ $stack: carries the VIGILIMEN-ephemeral marker"
    else
      bad "$stack: is an evidence stack and does not set VIGILIMEN-ephemeral. sweep.sh will not see anything it creates."
    fi
  else
    if echo "$C" | grep -qE '"VIGILIMEN-ephemeral"[[:space:]]*='; then
      bad "$stack: is a bootstrap stack and sets VIGILIMEN-ephemeral. The sweep would delete the federation that lets the sweep run."
    else
      say "✓ $stack: bootstrap, correctly not marked ephemeral"
    fi
  fi

  # ---- programme tag ------------------------------------------------------
  #
  # GCP IAM resources are the genuine exception: google_service_account,
  # google_iam_workload_identity_pool and its provider accept NO labels
  # argument at all. Demanding a label the platform will not accept is a
  # check that is wrong rather than a stack that is wrong, so the standard
  # falls back to the naming prefix for those — which is why the prefix is
  # enforced separately below and not treated as decoration.
  if echo "$C" | grep -qE 'programme[[:space:]]*=[[:space:]]*"mined"'; then
    say "✓ $stack: tagged programme = mined"
  elif echo "$C" | grep -q 'google_iam_workload_identity_pool\|google_service_account'; then
    say "~ $stack: GCP IAM resources accept no labels — attribution falls back to the VIGILIMEN- name prefix"
  else
    bad "$stack: no programme tag. Cross-account cost attribution depends on it."
  fi

  # ---- naming prefix ------------------------------------------------------
  # Names are built from a local, so check the local rather than every
  # resource — a standard enforced at one place is a standard that holds.
  if echo "$C" | grep -qE 'name[[:space:]]*=[[:space:]]*"VIGILIMEN-'; then
    say "✓ $stack: names built from an VIGILIMEN- prefix"
  elif echo "$C" | grep -qE 'account_id[[:space:]]*=[[:space:]]*"VIGILIMEN-|display_name[[:space:]]*=[[:space:]]*"VIGILIMEN-|name[[:space:]]*=[[:space:]]*var\.'; then
    say "✓ $stack: names built from an VIGILIMEN- prefix or a validated variable"
  else
    bad "$stack: no VIGILIMEN- naming prefix found."
  fi

  echo
done

# ---------------------------------------------------------------------------
# The sweep and the verification must agree on the tag they use.
# ---------------------------------------------------------------------------
SWEEP_KEY=$(grep -oE 'TAG_KEY:-[a-z0-9-]+' scripts/sweep.sh | head -1 | cut -d- -f2-)
if [ "$SWEEP_KEY" = "VIGILIMEN-ephemeral" ]; then
  say "✓ sweep.sh defaults to the same tag key the stacks set"
else
  bad "sweep.sh defaults to tag key '$SWEEP_KEY' but the stacks set 'VIGILIMEN-ephemeral'. The sweep would find nothing."
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "FF-05 pass — the teardown mechanism has no holes in it."
else
  echo "FF-05 FAIL — something created by an evidence window would be invisible to the sweep."
  echo "That is not a naming problem. It is a resource that survives the window and bills."
fi
exit "$fail"
