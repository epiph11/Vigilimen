#!/usr/bin/env bash
# FF-01 — governance documents stay under the cut line.
#
# The Sprint 0 top risk was documentation over-engineering, and the response
# was a two-page cap on governance documents. A cap enforced by intention is
# a cap that erodes; this is the machinery.
#
# Assessment and specification artifacts are EXEMPT. They are the deliverable,
# not the overhead, and capping them would be capping the work itself.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ~55 lines of rendered markdown per page is a fair approximation once tables
# and headings are counted. Two pages is therefore ~110. The number is a
# convention, not a measurement, and it is written here rather than argued
# about in a review.
LIMIT=115

GOVERNED=(
  "docs/charter.md"
  "docs/governance"
  "docs/architecture/characteristics.md"
  "docs/architecture/environments.md"
  "docs/architecture/threat-model-v1.md"
  "docs/compliance"
)

fail=0
echo "FF-01 — governance cut line: ${LIMIT} lines"
echo

while IFS= read -r f; do
  [ -e "$f" ] || continue
  n=$(wc -l < "$f")
  if [ "$n" -gt "$LIMIT" ]; then
    printf '  ✗ %-52s %4d lines  (+%d over)\n' "$f" "$n" "$((n - LIMIT))"
    fail=1
  else
    printf '  ✓ %-52s %4d lines\n' "$f" "$n"
  fi
done < <(
  for g in "${GOVERNED[@]}"; do
    if [ -d "$g" ]; then find "$g" -name '*.md'; else echo "$g"; fi
  done | sort -u
)

# ADRs get their own, tighter cap. An ADR is one decision. An ADR that needs
# three pages is either two decisions or a design document wearing an ADR's
# filename, and both are worth catching early.
ADR_LIMIT=80
echo
echo "FF-01 — ADR cut line: ${ADR_LIMIT} lines (an ADR is ONE decision)"
echo
for f in docs/adr/*.md; do
  [ -e "$f" ] || continue
  n=$(wc -l < "$f")
  if [ "$n" -gt "$ADR_LIMIT" ]; then
    printf '  ✗ %-52s %4d lines  (+%d over)\n' "$f" "$n" "$((n - ADR_LIMIT))"
    fail=1
  else
    printf '  ✓ %-52s %4d lines\n' "$f" "$n"
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "FF-01 pass"
else
  echo "FF-01 FAIL — cut, or split, or move the detail into the artifact it belongs to."
  echo "Raising the limit requires an ADR, because it is a decision to spend"
  echo "the reader's attention rather than the author's."
fi
exit "$fail"
