# hermes_ops

Custom Frappe app implementing the ERPNext-side data model required by the
Hermes Agent + Telegram integration plan (mục 5.5, 5.7, 8.4 of
`Ke hoach trien khai he thong AI quan tri noi bo`).

## What this app adds

- Custom fields on Project, Task, CRM Lead and Opportunity (mục 8.1–8.3):
  `ai_summary`, `ai_risk_level`, `blocked_reason`, `telegram_group_id`, etc.
  See `hermes_ops/fixtures/custom_field.json`.
- DocType **Telegram Identity** — maps a Telegram numeric user ID to an
  ERPNext User/Employee (onboarding `/link` flow, mục 5.5).
- DocType **AI Approval Request** — the only path for a Hermes skill to
  perform an action that the approval matrix (mục 12.4) marks as
  "Cần duyệt" (reassign, deadline change, submit quotation, create Sales
  Order, adjust stock, cancel a document).
- DocType **Telegram Message Route** + **Telegram Message Event** — the
  cross-message routing table and anti-loop ledger (mục 5.6–5.8):
  `hop_count`, `event_id` dedup, no reprocessing.

## What this app deliberately does NOT do

- It does not call the Telegram API or the OpenRouter/TokenHub APIs. That
  logic lives in the ERPNext API Bridge (`integration/erpnext-bridge`),
  which is the only component allowed to read/write these DocTypes over
  REST on behalf of a Hermes profile.
- It does not grant any role Administrator-equivalent access. Roles are
  defined in `hermes_ops/fixtures/custom_role.json` and match the
  role/approval matrix in the plan (mục 6, 12.3, 12.4) — read-only for most
  ERPNext data, write access limited to the DocTypes above.

## Install

```bash
bench get-app hermes_ops /opt/apps/erpnext/custom-apps/hermes_ops
bench --site erp.example.com install-app hermes_ops
bench --site erp.example.com migrate
```

The Ansible role `roles/erpnext-app` in this repo automates this: it copies
the app into the frappe_docker build context, rebuilds the custom image
with `bench get-app`/`install-app` baked in (per frappe_docker's
"Custom Apps" documented workflow using `apps.json` + custom build), then
runs `bench migrate` as part of `playbooks/create_site.yml`.

## Provisioning API users (mục 12.3)

After `install-app`, run:

```bash
ansible-playbook playbooks/provision_erpnext.yml --ask-vault-pass
```

This creates `hermes-ops@company.local`, `hermes-staff@company.local`,
`hermes-sales@company.local`, assigns the matching custom Role, generates
API Key/Secret and writes them into Ansible Vault output (you copy them into
`vault.yml` — the playbook never prints secrets to stdout, `no_log: true`).
