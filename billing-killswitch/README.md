# GCP Billing Kill Switch

Automatically disables your GCP billing when monthly spend crosses ₹2,000.
No more fear of runaway bills.

---

## How It Works

```
Your GCP usage costs money
        ↓
Budget Alert fires at ₹2,000
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

---

## Files in This Folder

| File | What it does |
|------|--------------|
| `main.py` | The Cloud Function code. Lives in GCP, runs automatically. |
| `requirements.txt` | Python libraries needed by `main.py`. |
| `deploy.md` | Step-by-step console setup guide. Read this to set up. |

---

## What Happens When Kill Switch Fires

- All GCP services stop (Cloud Run, Firestore, GCS, Vertex AI — everything)
- No further charges accrue
- **Your data is NOT deleted** — Firestore, GCS files are all safe
- Services are paused, not destroyed

### To Re-enable After a Kill (takes 2 minutes)
1. GCP Console → **Billing**
2. Click your project → **"Link a billing account"**
3. Select your billing account → Save
4. Services restart automatically

---

## Alert Thresholds (set during deploy)

| Spend | What happens |
|-------|-------------|
| ₹1 | **TEST ONLY** — used during testing phase, then changed to ₹2,000 |
| ₹1,000 (50%) | You get an email warning |
| ₹1,800 (90%) | You get an email warning |
| ₹2,000 (100%) | Kill switch fires, billing disabled |

---

## Important Caveat

There is a ~1–2 hour delay between GCP recording costs and the budget alert firing.
So you might see ₹2,100–2,200 before the kill fires. This is a GCP platform limitation.
