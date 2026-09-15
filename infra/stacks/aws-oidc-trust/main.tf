# GitHub OIDC trust for AWS.
#
# ADR-007: this is the only thing in the programme that grants access to a
# cloud, and it grants it to a workflow rather than to a person or a key.
#
# This stack is the one exception to the evidence-window rule. It is applied
# once, by hand, and it PERSISTS — an OIDC provider and a role cost nothing
# and there is nothing to bill. Everything else is ephemeral.

terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  backend "s3" {
    # Populated by -backend-config at init. The bucket name is an account
    # detail, not a decision, and hardcoding it here would make this stack
    # unusable in any other account.
    key    = "bootstrap/aws-oidc-trust.tfstate"
    region = "ap-southeast-2"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      programme = "mined"
      stack     = "aws-oidc-trust"
      managedby = "terraform"
      # deliberately NOT mined-ephemeral: the sweep must not delete the
      # thing that grants the sweep its permissions.
    }
  }
}

# ---------------------------------------------------------------------------
# The provider
# ---------------------------------------------------------------------------

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

# ---------------------------------------------------------------------------
# The trust condition — the part worth reviewing
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    # Audience. Without this, a token minted for any audience would be
    # accepted.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Subject. This is the condition that actually scopes the role, and it
    # is the one that gets written too broadly.
    #
    #   repo:<owner>/<repo>:ref:refs/heads/main      one branch
    #   repo:<owner>/<repo>:environment:evidence     one environment
    #   repo:<owner>/<repo>:*                        ANY branch, any fork PR
    #
    # The third form is what most tutorials show. It means an untrusted
    # branch can assume this role, which is the whole attack. StringEquals
    # against explicit subjects — never StringLike with a wildcard.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = var.allowed_subjects
    }
  }
}

resource "aws_iam_role" "evidence_window" {
  name                 = "mined-evidence-window"
  description          = "Assumed by the evidence-window workflow. Short-lived, scoped by subject."
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  max_session_duration = 3600
}

# ---------------------------------------------------------------------------
# What the role may do
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "permissions" {
  # The evidence window creates and destroys. It must be able to do both,
  # and the destroy permission is the one people forget — a role that can
  # create but not delete produces exactly the orphaned infrastructure this
  # programme exists to avoid.
  statement {
    effect = "Allow"
    actions = [
      "s3:*",
      "iot:*",
      "timestream:*",
      "logs:*",
      "cloudwatch:*",
      "ec2:Describe*",
      "sts:GetCallerIdentity",
      "tag:GetResources",
    ]
    resources = ["*"]
  }

  # A belt-and-braces deny on the resources FF-13 already refuses to plan.
  # FF-13 catches them before apply; this catches anything that reaches the
  # API another way. Two controls at different layers, and the cheaper one
  # runs first.
  statement {
    effect = "Deny"
    actions = [
      "ec2:CreateNatGateway",
      "rds:CreateDBInstance",
      "redshift:CreateCluster",
      "sagemaker:CreateEndpoint",
      "elasticloadbalancing:CreateLoadBalancer",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "evidence_window" {
  name   = "mined-evidence-window"
  role   = aws_iam_role.evidence_window.id
  policy = data.aws_iam_policy_document.permissions.json
}
