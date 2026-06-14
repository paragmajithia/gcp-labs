# GCP Billing Kill Switch

GCP has no built-in hard spending cap — only email alerts you can ignore. This project adds a real kill switch: when your monthly spend crosses a threshold you set, billing is automatically disabled and all services stop. No manual action needed, no surprise bills.

Built for developers running personal GCP projects, learning Vertex AI, or experimenting with Cloud Run — where runaway costs are a real risk.

---

## How It Works

```
Your GCP usage costs money
        ↓
Budget Alert fires at your configured limit
        ↓
Pub/Sub topic receives the alert
        ↓
Cloud Function wakes up
        ↓
Checks: am I over budget?
        ↓ YES
Disables billing on your project
        ↓
All services stop. Zero further charges.
```

> **⚠️ Platform delay:** GCP records costs with a ~1–2 hour lag before budget alerts fire.
> You may see ₹100–200 of overage before the kill switch triggers. This is a GCP limitation, not a bug in this code.

---

## Architecture

![High-level flow diagram](./billing-killswitch.drawio.svg)

---

## Files

| File | What it does |
|------|--------------|
| `main.py` | The Cloud Function — runs automatically in GCP when triggered |
| `requirements.txt` | Python dependencies for `main.py` |
| `deploy.md` | Step-by-step setup guide (GCP Console, no CLI needed) |

---

## What Happens When the Kill Switch Fires

| | |
|--|--|
| ✅ | All GCP services stop (Cloud Run, Firestore, GCS, Vertex AI — everything) |
| ✅ | No further charges accrue |
| ✅ | **Your data is safe** — Firestore documents, GCS files are not deleted |
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
| 50% of limit | Email warning to you |
| 90% of limit | Email warning to you |
| 100% of limit | **Kill switch fires, billing disabled** |

You set the limit during deploy. The guide uses ₹2,000 as an example.

---

## Prerequisites

- A GCP account with a project created
- A billing account linked to that project
- Owner or Editor role on the project
