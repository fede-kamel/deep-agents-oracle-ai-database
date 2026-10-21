# Run the demo in OCI

Personal work with synthetic data. This puts the whole demo on one Ampere VM
in your own tenancy: the web application, the OpenShell gateway, the
sandboxes and the agents. A browser is all the laptop needs afterwards.

```
browser ──HTTPS──► Network Load Balancer ──► VM (private subnet)
                                              Caddy (TLS + login) → web app → OpenShell → sandbox → Deep Agent
                                              ├─ service gateway ─► Oracle AI Database (OCI network, no internet)
                                              └─ NAT gateway ─────► OCI Generative AI (other region, TLS)
operator ──OCI Bastion──► VM :22 (no public SSH)
```

| Path | What it does |
|---|---|
| `terraform/` | private subnet and route table, security groups, VM, Bastion, load balancer, Vault and the VM's read-only access to it |
| `server/provision.sh` | everything on the VM, from the laptop: code, packages, Landlock, DNS cache, OpenShell, image, web app, secrets from the Vault |
| `server/connect.sh` | SSH tunnel through the Bastion, from any network: `ssh -p 2222 opc@127.0.0.1` |
| `server/operator/vault-put.sh` | stores the secrets in the Vault, once |
| `install.sh` | all of the above, in order |

## Install

Needs `terraform`, `oci`, `jq` and `ssh` on the laptop, an existing VCN with
a public subnet, a NAT gateway and a service gateway, and the local setup of
`codex/SPEC.md` section 4 (the config file and the database users).

```shell
cp deploy/terraform/terraform.tfvars.example deploy/terraform/terraform.tfvars   # fill in
deploy/install.sh
```

`install.sh` applies Terraform, stores any secret not yet in the Vault
(it asks for the web login once and creates the GenAI key itself, straight
into the Vault), then provisions the VM. Rerun it any time. It ends with the
URL. Then lock the database's access control list to the VCN alone.

## Operate

```shell
deploy/server/connect.sh                                   # tunnel for 3 hours
ssh -p 2222 opc@127.0.0.1                                  # shell on the VM
deploy/server/operator/vault-put.sh --genai                # rotate the GenAI key
deploy/server/operator/vault-put.sh --login                # change the web login
deploy/server/provision.sh                                 # redeploy code and secrets
terraform -chdir=deploy/terraform destroy                  # remove it all
```

## Why some steps exist

- **Landlock.** Oracle Linux's kernel ships Landlock but leaves it off;
  OpenShell sandboxes refuse to start without it. `bootstrap.sh` enables it
  and `provision.sh` reboots once.
- **Gateway endpoint.** Sandbox supervisors use the host network, where
  `host.docker.internal` does not resolve on Linux; the gateway listens on and
  is called at `127.0.0.1`.
- **DNS cache.** OpenShell 0.1.2 maps the database host to a synthetic address
  for the DNS answer's remaining TTL, at most 30 s. The VCN resolver often
  answers with a few seconds left, so reconnects hit an expired mapping.
  Unbound keeps answers for 5 minutes and refreshes them early; `agent/db.py`
  retries the rare refusal left.
- **Front end.** `npm ci` crashes on the VM, so `provision.sh` builds `web/dist`
  on the laptop and copies it.
- **HTTP/1.1 only.** The load balancer forwards TCP, so HTTP/3 (UDP) can never
  arrive. HTTP/2 is off as well. It carries every request on one connection,
  and when that connection silently stopped delivering (venue Wi-Fi, during a
  rehearsal) the whole page froze until the browser gave up on it, about a
  minute later. Over HTTP/1.1 a request the page abandons closes its own
  connection, so the page's request timeouts and its stream watchdog recover
  on fresh connections within 45 s. A browser opens at most six HTTP/1.1
  connections to a host and each open tab holds one for its event stream, so
  keep to a few tabs. Caddy also sends `Alt-Svc: clear`, so browsers forget
  the HTTP/3 that earlier deployments advertised, and logs every request to
  the journal (`sudo journalctl -u caddy`).
