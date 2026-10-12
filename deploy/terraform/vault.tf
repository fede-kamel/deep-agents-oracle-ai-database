# Secrets for the demo host live in OCI Vault. Terraform creates the vault,
# its key and the VM's read access; it never sees a secret value (those are
# stored by deploy/server/operator/vault-put.sh, so state stays clean). The VM
# reads them with its instance principal during provisioning.

resource "oci_kms_vault" "demo" {
  compartment_id = var.compartment_id
  display_name   = "deepagents-vault"
  vault_type     = "DEFAULT"
}

resource "oci_kms_key" "demo" {
  compartment_id      = var.compartment_id
  display_name        = "deepagents-secrets"
  management_endpoint = oci_kms_vault.demo.management_endpoint
  protection_mode     = "SOFTWARE"

  key_shape {
    algorithm = "AES"
    length    = 32
  }
}

# The demo VM, and only it, as an IAM principal.
resource "oci_identity_dynamic_group" "demo" {
  compartment_id = var.tenancy_id
  name           = "deepagents-demo-vm"
  description    = "The deepagents demo VM (reads its secrets from deepagents-vault)"
  matching_rule  = "instance.id = '${oci_core_instance.demo.id}'"
}

resource "oci_identity_policy" "demo_secrets" {
  compartment_id = var.compartment_id
  name           = "deepagents-demo-secrets"
  description    = "The demo VM reads the secrets of its own vault, nothing else"
  statements = [
    "allow dynamic-group ${oci_identity_dynamic_group.demo.name} to read secret-family in compartment id ${var.compartment_id} where target.vault.id = '${oci_kms_vault.demo.id}'",
  ]
}

output "vault_id" {
  value = oci_kms_vault.demo.id
}

output "vault_key_id" {
  value = oci_kms_key.demo.id
}
