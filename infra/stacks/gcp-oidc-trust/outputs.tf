output "workload_identity_provider" {
  description = "Set as the repository variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "service_account" {
  description = "Set as the repository variable GCP_SERVICE_ACCOUNT."
  value       = google_service_account.evidence_window.email
}

output "attribute_condition" {
  description = "Echoed so the applied condition can be read against intent. This single expression is what stops any GitHub repository on earth from minting credentials here — review it, do not assume it."
  value       = google_iam_workload_identity_pool_provider.github.attribute_condition
}
