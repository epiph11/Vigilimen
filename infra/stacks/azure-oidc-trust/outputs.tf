output "client_id" {
  description = "Set as the repository variable AZURE_CLIENT_ID."
  value       = azuread_application.evidence_window.client_id
}

output "tenant_id" {
  description = "Set as the repository variable AZURE_TENANT_ID."
  value       = data.azurerm_subscription.current.tenant_id
}

output "subscription_id" {
  description = "Set as the repository variable AZURE_SUBSCRIPTION_ID."
  value       = data.azurerm_subscription.current.subscription_id
}

output "evidence_resource_group" {
  description = "Export as AZURE_EVIDENCE_RG so sweep.sh and verify_empty.sh act on the same group this stack scoped the role to. If these three ever disagree, the sweep deletes the wrong thing or nothing at all."
  value       = azurerm_resource_group.evidence.name
}

output "federated_subjects" {
  description = "The exact subjects that may authenticate. Read this against intent after every apply."
  value       = [for c in azuread_application_federated_identity_credential.github : c.subject]
}
