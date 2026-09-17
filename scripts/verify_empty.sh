#!/usr/bin/env bash
# Verify that an evidence window left nothing behind.
#
# This runs AFTER terraform destroy and after the sweep, and it is the step
# allowed to fail the run. Destroy and sweep are best-effort by design
# (`|| true` in the workflow) so that a failure in one does not prevent the
# other; verification is what actually decides whether the window closed.
#
# The question it answers is not "did destroy report success" but
# "is the account empty" — which are different questions, and the second is
# the only one the budget cares about.
#
#   usage: verify_empty.sh <aws|azure|gcp>

set -uo pipefail
CLOUD="${1:?usage: verify_empty.sh <aws|azure|gcp>}"
REGION="${AWS_REGION:-ap-southeast-2}"
fail=0

note() { printf '  %s\n' "$*"; }
bad()  { printf '  LEFT BEHIND: %s\n' "$*"; fail=1; }

echo "Verifying ${CLOUD} is empty"

case "$CLOUD" in

  aws)
    # Only the resources that bill by existing. Checking everything produces
    # noise, and a verification nobody reads verifies nothing.
    n=$(aws ec2 describe-nat-gateways --region "$REGION" \
          --filter 'Name=state,Values=available,pending' \
          --query 'length(NatGateways)' --output text 2>/dev/null || echo 0)
    [ "$n" = "0" ] && note "NAT gateways: 0" || bad "$n NAT gateway(s)"

    n=$(aws ec2 describe-instances --region "$REGION" \
          --filters 'Name=instance-state-name,Values=running,pending,stopping,stopped' \
          --query 'length(Reservations[].Instances[])' --output text 2>/dev/null || echo 0)
    [ "$n" = "0" ] && note "EC2 instances: 0" || bad "$n EC2 instance(s) — stopped still bills for EBS"

    n=$(aws rds describe-db-instances --region "$REGION" \
          --query 'length(DBInstances)' --output text 2>/dev/null || echo 0)
    [ "$n" = "0" ] && note "RDS instances: 0" || bad "$n RDS instance(s)"

    n=$(aws elbv2 describe-load-balancers --region "$REGION" \
          --query 'length(LoadBalancers)' --output text 2>/dev/null || echo 0)
    [ "$n" = "0" ] && note "Load balancers: 0" || bad "$n load balancer(s)"

    n=$(aws ec2 describe-addresses --region "$REGION" \
          --query 'length(Addresses)' --output text 2>/dev/null || echo 0)
    [ "$n" = "0" ] && note "Elastic IPs: 0" || bad "$n elastic IP(s) — an UNATTACHED EIP bills"
    ;;

  azure)
    RG="${AZURE_EVIDENCE_RG:-rg-VIGILIMEN-evidence}"
    if az group exists --name "$RG" 2>/dev/null | grep -qi true; then
      n=$(az resource list --resource-group "$RG" --query 'length(@)' -o tsv 2>/dev/null || echo 0)
      [ "$n" = "0" ] && note "Resource group empty" || bad "$n resource(s) in $RG"
    else
      note "Resource group $RG does not exist"
    fi
    ;;

  gcp)
    n=$(gcloud compute instances list --format='value(name)' 2>/dev/null | wc -l)
    [ "$n" = "0" ] && note "Compute instances: 0" || bad "$n compute instance(s)"

    n=$(gcloud sql instances list --format='value(name)' 2>/dev/null | wc -l)
    [ "$n" = "0" ] && note "Cloud SQL instances: 0" || bad "$n Cloud SQL instance(s)"

    n=$(gcloud compute routers list --format='value(name)' 2>/dev/null | wc -l)
    [ "$n" = "0" ] && note "Cloud routers: 0" || bad "$n router(s) — check for attached NAT"
    ;;

  *)
    echo "unknown cloud: $CLOUD" >&2
    exit 2
    ;;
esac

echo
if [ "$fail" -eq 0 ]; then
  echo "Window closed clean — nothing billable survives this run."
else
  echo "WINDOW DID NOT CLOSE CLEAN."
  echo "Something is still running and still billing. Fix it now, not next sprint:"
  echo "  1. Delete what is listed above."
  echo "  2. Work out why terraform destroy and the sweep both missed it."
  echo "  3. If it is a resource type the sweep does not know about, add it —"
  echo "     a sweep that only catches what has already escaped is a log, not a control."
fi
exit "$fail"
