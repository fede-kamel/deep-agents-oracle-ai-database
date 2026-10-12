# The server-side demo host, private: an Ampere VM in its own private subnet,
# reached by browsers through a Network Load Balancer and by the operator
# through OCI Bastion. Existing VCN, gateways and public subnet are reused,
# not modified. The VM is prepared by deploy/server/provision.sh; secrets are
# copied by the operator, never by Terraform.

terraform {
  required_version = ">= 1.5"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0"
    }
  }
}

provider "oci" {
  config_file_profile = var.oci_profile
  region              = var.region
}

# ---- network -------------------------------------------------------------

# Oracle services in the region (the database) through the service gateway,
# on OCI's network. Everything else outbound (GenAI in another region,
# Let's Encrypt, packages) through the NAT gateway. Nothing inbound.
resource "oci_core_route_table" "demo" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "deepagents-rt"

  route_rules {
    destination       = var.oracle_services_cidr
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = var.service_gateway_id
  }

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = var.nat_gateway_id
  }
}

# Ingress is handled by network security groups; the subnet list only
# allows egress.
resource "oci_core_security_list" "demo" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "deepagents-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }
}

resource "oci_core_subnet" "demo" {
  compartment_id             = var.compartment_id
  vcn_id                     = var.vcn_id
  cidr_block                 = var.subnet_cidr
  display_name               = "deepagents-private"
  dns_label                  = "deepagents"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.demo.id
  security_list_ids          = [oci_core_security_list.demo.id]
}

# ---- VM security group ----------------------------------------------------

resource "oci_core_network_security_group" "demo" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "deepagents-demo-nsg"
}

# The load balancer does not preserve the client address, so web traffic
# arrives from the public subnet where it lives.
resource "oci_core_network_security_group_security_rule" "https" {
  network_security_group_id = oci_core_network_security_group.demo.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.public_subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "HTTPS from the load balancer"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_network_security_group_security_rule" "http" {
  network_security_group_id = oci_core_network_security_group.demo.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.public_subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "HTTP (ACME challenge, redirect) from the load balancer"
  tcp_options {
    destination_port_range {
      min = 80
      max = 80
    }
  }
}

# SSH only from inside the demo subnet, where OCI Bastion sessions originate.
# The operator connects through the bastion from any network; it
# authenticates with OCI IAM and the SSH key, not the caller's IP address.
resource "oci_core_network_security_group_security_rule" "ssh" {
  network_security_group_id = oci_core_network_security_group.demo.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH from OCI Bastion"
  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "egress" {
  network_security_group_id = oci_core_network_security_group.demo.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "all egress"
}

# ---- VM -------------------------------------------------------------------

resource "oci_core_instance" "demo" {
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  display_name        = "deepagents-demo"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gbs
  }

  source_details {
    source_type             = "image"
    source_id               = var.image_id
    boot_volume_size_in_gbs = 100
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.demo.id
    assign_public_ip = false
    nsg_ids          = [oci_core_network_security_group.demo.id]
  }

  metadata = {
    ssh_authorized_keys = file(pathexpand(var.ssh_public_key_path))
  }

  lifecycle {
    # A newer platform image must not replace a running demo host.
    ignore_changes = [source_details, metadata]
  }
}

resource "oci_bastion_bastion" "demo" {
  compartment_id               = var.compartment_id
  bastion_type                 = "STANDARD"
  name                         = "deepagentsdemo"
  target_subnet_id             = oci_core_subnet.demo.id
  client_cidr_block_allow_list = ["0.0.0.0/0"]
  max_session_ttl_in_seconds   = 10800
}

# ---- load balancer --------------------------------------------------------

resource "oci_core_network_security_group" "nlb" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "deepagents-nlb-nsg"
}

resource "oci_core_network_security_group_security_rule" "nlb_in" {
  for_each                  = toset(["80", "443"])
  network_security_group_id = oci_core_network_security_group.nlb.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  description               = "web from anywhere (TLS and login on the VM)"
  tcp_options {
    destination_port_range {
      min = tonumber(each.value)
      max = tonumber(each.value)
    }
  }
}

resource "oci_core_network_security_group_security_rule" "nlb_out" {
  network_security_group_id = oci_core_network_security_group.nlb.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = var.subnet_cidr
  destination_type          = "CIDR_BLOCK"
  description               = "to the VM"
}

resource "oci_network_load_balancer_network_load_balancer" "demo" {
  compartment_id                 = var.compartment_id
  display_name                   = "deepagents-nlb"
  subnet_id                      = var.public_subnet_id
  is_private                     = false
  is_preserve_source_destination = false
  network_security_group_ids     = [oci_core_network_security_group.nlb.id]
}

# TCP pass-through: Caddy on the VM terminates TLS and asks for the login.
resource "oci_network_load_balancer_backend_set" "web" {
  for_each                 = toset(["80", "443"])
  network_load_balancer_id = oci_network_load_balancer_network_load_balancer.demo.id
  name                     = "web-${each.value}"
  policy                   = "FIVE_TUPLE"
  is_preserve_source       = false

  health_checker {
    protocol = "TCP"
    port     = tonumber(each.value)
  }
}

resource "oci_network_load_balancer_backend" "web" {
  for_each                 = oci_network_load_balancer_backend_set.web
  network_load_balancer_id = oci_network_load_balancer_network_load_balancer.demo.id
  backend_set_name         = each.value.name
  target_id                = oci_core_instance.demo.id
  port                     = tonumber(each.key)
}

resource "oci_network_load_balancer_listener" "web" {
  for_each                 = oci_network_load_balancer_backend_set.web
  network_load_balancer_id = oci_network_load_balancer_network_load_balancer.demo.id
  name                     = "web-${each.key}"
  default_backend_set_name = each.value.name
  protocol                 = "TCP"
  port                     = tonumber(each.key)
}

# ---- outputs --------------------------------------------------------------

locals {
  public_ip = [for a in oci_network_load_balancer_network_load_balancer.demo.ip_addresses : a.ip_address if a.is_public][0]
}

output "bastion_id" {
  value = oci_bastion_bastion.demo.id
}

output "private_ip" {
  value = oci_core_instance.demo.private_ip
}

output "public_ip" {
  value = local.public_ip
}

output "host" {
  value = "${replace(local.public_ip, ".", "-")}.sslip.io"
}

output "url" {
  value = "https://${replace(local.public_ip, ".", "-")}.sslip.io"
}
