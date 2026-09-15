output "role_arn" {
  description = "Set this as the repository variable AWS_OIDC_ROLE_ARN. It is a `vars`, not a `secrets` — an ARN is an identifier, and storing identifiers as secrets trains everyone to stop reading the secrets list (ADR-007)."
  value       = aws_iam_role.evidence_window.arn
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github.arn
}

output "allowed_subjects" {
  description = "Echoed back so the applied trust condition can be reviewed against intent. A trust policy that is too broad is invisible until someone tests it."
  value       = var.allowed_subjects
}
