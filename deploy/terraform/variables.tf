variable "oci_profile" {
  description = "Profile in ~/.oci/config"
  type        = string
}

variable "region" {
  description = "Region of the VCN and the database"
  type        = string
}

variable "compartment_id" {
  description = "Compartment for the security group and the VM"
  type        = string
}

variable "vcn_id" {
  description = "Existing VCN"
  type        = string
}

variable "nat_gateway_id" {
  description = "Existing NAT gateway in that VCN (outbound internet for the private VM)"
  type        = string
}

variable "public_subnet_id" {
  description = "Existing public subnet for the Network Load Balancer"
  type        = string
}

variable "public_subnet_cidr" {
  description = "CIDR of that public subnet (where load balancer traffic comes from)"
  type        = string
}

variable "service_gateway_id" {
  description = "Existing service gateway in that VCN (all Oracle services in the region)"
  type        = string
}

variable "oracle_services_cidr" {
  description = "Service CIDR label of that gateway, e.g. all-yyz-services-in-oracle-services-network"
  type        = string
}

variable "availability_domain" {
  type = string
}

variable "image_id" {
  description = "Oracle Linux 9 aarch64 platform image"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR for the private demo subnet (free in the VCN); SSH is allowed only from here (OCI Bastion)"
  type        = string
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_ed25519.pub"
}

variable "ocpus" {
  type    = number
  default = 4
}

variable "memory_gbs" {
  type    = number
  default = 24
}

variable "tenancy_id" {
  description = "Tenancy OCID (dynamic groups live at the tenancy)"
  type        = string
}
