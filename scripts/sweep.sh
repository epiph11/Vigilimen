#!/usr/bin/env bash
# Sweep — delete anything the evidence window created that Terraform did not own.
#
# Terraform destroys what is in its state. It does not destroy what a service
# created on its own behalf: a log group a Lambda made, an ENI a NAT left, a
# snapshot taken automatically, a bucket that refused to delete because it was
# not empty. Those are what survive a "successful" destroy.
#
# Everything here is scoped by TAG. A sweep that deletes by resource type
# deletes things it did not create, and a sweep you are afraid to run is a
# sweep that does not run.
#
#   usage: sweep.sh <aws|azure|gcp>

set -uo pipefail
CLOUD="${1:?usage: sweep.sh <aws|azure|gcp>}"
TAG_KEY="${MD360_TAG_KEY:-md360-ephemeral}"
TAG_VALUE="${MD360_TAG_VALUE:-true}"
REGION="${AWS_REGION:-ap-southeast-2}"

echo "Sweeping ${CLOUD} for ${TAG_KEY}=${TAG_VALUE}"

case "$CLOUD" in

  aws)
    # Everything created inside an evidence window carries the tag by
    # default_tags on the provider, so the tag is not something an author
    # has to remember per resource.
    ids=$(aws resourcegroupstaggingapi get-resources \
            --region "$REGION" \
            --tag-filters "Key=${TAG_KEY},Values=${TAG_VALUE}" \
            --query 'ResourceTagMappingList[].ResourceARN' --output text 2>/dev/null || true)

    if [ -z "$ids" ]; then
      echo "  nothing tagged remains"
    else
      echo "  tagged resources still present:"
      for arn in $ids; do echo "    $arn"; done
      # Deliberately does not mass-delete by ARN. Each service needs its own
      # delete call and its own ordering, and a loop that guesses is how a
      # sweep script becomes the most dangerous file in a repository.
      # verify_empty.sh is what fails the run; this reports what to look at.
    fi

    # Log groups are the exception worth automating: they are created by the
    # service rather than by Terraform, they are never in state, and they
    # accumulate silently across every run.
    for lg in $(aws logs describe-log-groups --region "$REGION" \
                  --log-group-name-prefix /aws/md360 \
                  --query 'logGroups[].logGroupName' --output text 2>/dev/null || true); do
      echo "    deleting log group $lg"
      aws logs delete-log-group --region "$REGION" --log-group-name "$lg" || true
    done
    ;;

  azure)
    # Azure makes this easy and the design leans on it: every evidence window
    # builds into ONE resource group, and the group is the unit of teardown.
    RG="${AZURE_EVIDENCE_RG:-rg-md360-evidence}"
    if az group exists --name "$RG" 2>/dev/null | grep -qi true; then
      echo "  deleting resource group $RG"
      az group delete --name "$RG" --yes --no-wait || true
    else
      echo "  resource group $RG does not exist"
    fi
    ;;

  gcp)
    for i in $(gcloud compute instances list \
                 --filter="labels.${TAG_KEY}=${TAG_VALUE}" \
                 --format='value(name,zone)' 2>/dev/null | tr '\t' ',' || true); do
      name="${i%%,*}"; zone="${i##*,}"
      echo "  deleting instance $name in $zone"
      gcloud compute instances delete "$name" --zone "$zone" --quiet || true
    done
    ;;

  *)
    echo "unknown cloud: $CLOUD" >&2
    exit 2
    ;;
esac

echo "Sweep finished. verify_empty.sh decides whether the window closed."
