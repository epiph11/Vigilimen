# Evidence stack — industrial telemetry ingestion on AWS.
#
# This stack exists to be applied, photographed and destroyed inside a single
# workflow run (ADR-004). Nothing depends on it. Nothing outlives it except
# the evidence directory it produces.
#
# What it demonstrates: a plant device authenticating to IoT Core with a
# certificate, publishing on a topic, and a rule routing that message onward.
# That is the AWS half of "AWS senses" (ADR-001), and it is the smallest
# thing that proves the path end to end.

terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  backend "s3" {
    key    = "evidence/aws-telemetry.tfstate"
    region = "ap-southeast-2"
  }
}

provider "aws" {
  region = var.region

  # Applied to every resource this provider creates, so the sweep's tag
  # filter cannot be defeated by someone forgetting a tag block.
  default_tags {
    tags = {
      programme         = "limen"
      stack             = "aws-telemetry"
      managedby         = "terraform"
      "limen-ephemeral" = "true"
    }
  }
}

locals {
  name = "limen-aws-telemetry"
}

# ---------------------------------------------------------------------------
# Where the telemetry lands
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "landing" {
  bucket = "${local.name}-landing-${var.suffix}"
  # This bucket exists for forty minutes. A destroy that fails because the
  # bucket is not empty is the most common way an evidence window fails to
  # close, and force_destroy is what prevents it.
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "landing" {
  bucket                  = aws_s3_bucket.landing.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "landing" {
  bucket = aws_s3_bucket.landing.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ---------------------------------------------------------------------------
# The device identity
# ---------------------------------------------------------------------------

resource "aws_iot_thing" "conveyor" {
  name = "${local.name}-CONV-001"
}

# Per-device policy, scoped to this device's own topic. A single shared
# policy permitting `topic/*` is the IoT equivalent of a shared credential,
# and it is what makes one compromised device a compromise of the fleet.
resource "aws_iot_policy" "conveyor" {
  name = "${local.name}-CONV-001"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:Connect"]
        Resource = ["arn:aws:iot:${var.region}:${data.aws_caller_identity.current.account_id}:client/${aws_iot_thing.conveyor.name}"]
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Publish"]
        Resource = ["arn:aws:iot:${var.region}:${data.aws_caller_identity.current.account_id}:topic/limen/plant/CONV-001/*"]
      },
      # No iot:Subscribe and no iot:Receive. The device publishes; it does
      # not listen. That is ADR-005 expressed at the device rather than at
      # the architecture diagram — a device that cannot subscribe cannot be
      # commanded from the cloud, by construction rather than by policy.
    ]
  })
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# The route onward
# ---------------------------------------------------------------------------

resource "aws_iot_topic_rule" "to_landing" {
  name        = replace("${local.name}_to_landing", "-", "_")
  enabled     = true
  sql         = "SELECT *, timestamp() AS ingest_utc_ms FROM 'limen/plant/CONV-001/+'"
  sql_version = "2016-03-23"

  # ingest_utc_ms is epoch milliseconds — UTC by definition. Rendering to
  # Australia/Brisbane happens at the presentation layer and nowhere else
  # (ADR-010).

  s3 {
    bucket_name = aws_s3_bucket.landing.id
    key         = "CONV-001/$${timestamp()}.json"
    role_arn    = aws_iam_role.iot_to_s3.arn
  }
}

resource "aws_iam_role" "iot_to_s3" {
  name = "${local.name}-iot-to-s3"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "iot.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "iot_to_s3" {
  name = "${local.name}-iot-to-s3"
  role = aws_iam_role.iot_to_s3.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.landing.arn}/*"
    }]
  })
}
