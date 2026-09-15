#!/usr/bin/env bash
# FF-03 — no static cloud credential anywhere in the tree.
#
# ADR-007: every credential is federated and short-lived. The only way that
# claim stays true is if a build fails the day someone pastes a key into a
# tfvars file "just to test something".
#
# This checks SHAPES, not entropy. A secret scanner that alerts on high
# entropy alerts on hashes, UUIDs and base64 test fixtures, and a scanner
# nobody believes is a scanner nobody reads.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

scan() {
  local name="$1" pattern="$2"
  # shellcheck disable=SC2086
  local hits
  hits=$(grep -rInE "$pattern" \
          --exclude-dir=.git \
          --exclude-dir=evidence \
          --exclude-dir=node_modules \
          --exclude="ff03_no_static_credentials.sh" \
          . 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "FF-03 FAIL — $name"
    echo "$hits" | sed 's/^/    /'
    echo
    fail=1
  fi
}

# --- credential shapes -----------------------------------------------------

scan "AWS access key id"          '\b(AKIA|ASIA)[0-9A-Z]{16}\b'
scan "AWS secret access key"      'aws_secret_access_key[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{20,}'
scan "Azure client secret"        'client_secret[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{8,}'
scan "GCP service account key"    '"type":[[:space:]]*"service_account"'
scan "private key block"          'BEGIN( RSA| EC| OPENSSH| PGP)? PRIVATE KEY'
scan "hardcoded password"         '(password|passwd)[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"'$][^"'"'"']{5,}'

# --- credential FILES that must never be committed -------------------------

for f in $(git ls-files 2>/dev/null || find . -type f -not -path './.git/*'); do
  case "$f" in
    *.pem|*.p12|*.pfx|*.jks|*credentials.json|*.tfvars|.env|*/.env)
      echo "FF-03 FAIL — credential-bearing file is tracked: $f"
      fail=1
      ;;
  esac
done

# --- the positive assertion ------------------------------------------------
#
# The absence of a secret is not proof that federation is configured. Check
# that the workflow actually asks for an OIDC token, because a workflow that
# quietly lost `id-token: write` will fall back to whatever is in the
# environment — which is precisely the failure this fitness function exists
# to catch.

if [ -d .github/workflows ]; then
  for wf in .github/workflows/*.yml; do
    [ -e "$wf" ] || continue
    if grep -qE 'aws-actions/configure-aws-credentials|azure/login|google-github-actions/auth' "$wf"; then
      if ! grep -q 'id-token: write' "$wf"; then
        echo "FF-03 FAIL — $wf authenticates to a cloud without requesting an OIDC token"
        echo "    add 'permissions: { id-token: write }' or the run will look for a stored credential"
        fail=1
      fi
    fi
  done
fi

if [ "$fail" -eq 0 ]; then
  echo "FF-03 pass — no static credential shape found; every cloud login requests an OIDC token"
fi
exit "$fail"
