# GCP Billing Kill Switch

GCP has no hard spending cap — only budget alerts that arrive after the money is already spent, and only if you're watching your inbox.

This project adds what GCP is missing: a real kill switch. When your monthly spend crosses a limit you set, billing is automatically disabled and all services stop. No manual action, no inbox monitoring, no surprises.

> 📖 **Full context and architecture walkthrough:** [GCP Has No Hard Spending Cap. Here's How to Add One in 15 Minutes.](https://paragmajithia.com/blog/gcp-bills-post/))

---

## How It Works

```
Monthly spend hits your configured limit
        ↓
Budget Alert fires → Pub/Sub topic (billing-killswitch)
        ↓
Cloud Run Function wakes up → checks: am I over budget?
        ↓ YES
Billing account unlinked from project
        ↓
All services stop. Zero further charges.
```

> **⚠️ Platform delay:** GCP records costs with a ~1–2 hour lag before alerts fire.
> You may see a small overage before the kill triggers. This is a GCP limitation, not a bug in this code.

---

## Architecture

![High-level flow diagram](./diagram.svg)

---

## Files

| File | What it does |
|------|--------------|
| `main.py` | The Cloud Run Function — runs automatically when triggered |
| `requirements.txt` | Python dependencies for `main.py` |
| `deploy.md` | Step-by-step setup guide — GCP Console only, no local CLI needed |
| `blog/` | Backup of the blog post published on Hashnode |

---

## Deploy in 15 Minutes

→ **[deploy.md](./deploy.md)** — full step-by-step guide with verification commands and a test procedure.

No local tools needed. No Terraform. The entire setup is done through the GCP Console.

---

## What Happens When the Kill Switch Fires

| | |
|--|--|
| ✅ | All services pause — Cloud Run, Firestore, GCS, Vertex AI |
| ✅ | No further charges accrue |
| ✅ | **Your data is safe** — Firestore documents and GCS files are not deleted |
| ✅ | Services are paused, not destroyed |

### To Re-enable (2 minutes)

1. GCP Console → **Billing**
2. Click your project → **"Link a billing account"**
3. Select your billing account → Save
4. Services restart automatically

---

## Alert Thresholds

| Spend | What happens |
|-------|-------------|
| 50% of limit | Email warning — early heads up |
| 90% of limit | Email warning — act now |
| 100% of limit | **Kill switch fires, billing disabled** |

You set the limit during deploy. The deploy guide uses ₹2,000 as an example.

---

## Prerequisites

- A GCP account with a project created
- A billing account linked to that project
- Owner or Editor role on the project
