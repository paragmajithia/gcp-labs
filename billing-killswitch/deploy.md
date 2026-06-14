# Deploy Guide — GCP Billing Kill Switch

**Time required:** ~15 minutes | **Setup:** GCP Console only | **Cloud Shell:** verification & testing only

---

## Before You Start

| What | Where to find it | Example |
|------|-----------------|---------|
| **Project ID** | GCP Console → top bar project dropdown | `your-project-id` |
| **Billing Account ID** | Billing → Account management → ID field | `01489A-10A50B-0CFF2D` |

---

## Architecture

```
Monthly spend hits ₹1,000
        ↓
Budget Alert → Pub/Sub topic (billing-killswitch)
        ↓
Cloud Run Function wakes up → checks: am I over budget?
        ↓ YES
Billing account unlinked from project → All GCP services stop
```

---

## Step 1 — Enable Required APIs

**GCP Console → APIs & Services → Enable APIs and Services**

| API | Why |
|-----|-----|
| `Cloud Run API` | Runs your kill switch function |
| `Cloud Billing API` | Lets function disable billing |
| `Cloud Pub/Sub API` | Receives budget alert messages |
| `Cloud Billing Budget API` | Creates and monitors your budget |
| `Cloud Resource Manager API` | Required by Billing API |

✅ **Done when:** all five APIs show as Enabled

---

## Step 2 — Create Pub/Sub Topic

1. GCP Console → **Pub/Sub → Create Topic**
2. Topic ID: `billing-killswitch` | Uncheck "Add a default subscription"
3. Click **Create**

✅ **Done when:** `billing-killswitch` appears in your topics list

---

## Step 3 — Create Budget Alert

**Billing → Budgets & alerts → Create Budget**

- Name: `killswitch-budget` | Time range: Monthly | Projects: `your-project-id` | Amount: `₹1000`
- Thresholds: `50%` (email only), `90%` (email only), `100%` (triggers kill switch)

> The function only acts at 100% — it ignores 50% and 90% messages.

Under **Manage notifications**:
- ✅ Email alerts to billing admins and users
- ✅ Email alerts to project owners
- ✅ Connect a Pub/Sub topic → select `billing-killswitch`

✅ **Done when:** `killswitch-budget` appears in Budgets & alerts

---

## Step 4 — Deploy the Cloud Run Function

> GCP has unified Cloud Functions into Cloud Run. Searching "Cloud Functions" lands on Cloud Run — that is correct.

### 4a — Create the service

**GCP Console → Cloud Run → "Write a function" section → Python**

- Service name: `billing-killswitch` | Region: `asia-south1` (Mumbai)

### 4b — Add Pub/Sub trigger

**Trigger → + Add trigger → Cloud Pub/Sub**

- Topic: `billing-killswitch`
- Service account: leave as `Compute Engine default service account`
- When yellow warning appears: click **"Grant all"** → **Save**

### 4c — Paste the code

- Runtime: `Python 3.14` (or latest available) | Entry point: `stop_billing`
- **main.py** tab: replace with contents of `main.py`
- **requirements.txt** tab: replace with contents of `requirements.txt`

### 4d — Environment variable

**Environment variables → Add variable:**
- Name: `PROJECT_ID` | Value: your project ID (e.g. `your-project-id`)

### 4e — Settings

| Section | Setting | Value |
|---------|---------|-------|
| Authentication | Mode | Require authentication + IAM |
| Billing | Type | Request-based |
| Service Scaling | Min instances | `0` |
| Ingress | Access | Internal |

Click **Create** and wait ~2–3 minutes for the green tick.

✅ **Done when:** `billing-killswitch` shows as **Ready** in Cloud Run → Services

---

## Step 5 — Grant Billing Permission to the Function

The function runs as a **service account** (robot identity), not as you. That robot needs explicit permission to disable billing.

> `your-email@gmail.com` = you (already in billing IAM — leave it).  
> `xxxx-compute@developer.gserviceaccount.com` = the robot — this is what you need to add.

### 5a — Find the service account email

**Fastest — YAML tab:**
1. Cloud Run → click `billing-killswitch` → **YAML** tab
2. Search for `serviceAccountName:` — the email is right there

It looks like: `PROJECT_NUMBER-compute@developer.gserviceaccount.com`

### 5b — Add to Billing IAM

**Billing → Account management → Add principal**
- New principal: paste service account email
- Role: **Billing Account Administrator** → **Save**

### 5c — Add to Project IAM

**IAM & Admin → IAM → Grant access**
- New principal: same service account email
- Role: **Project Billing Manager** → **Save**

> Without this project-level role, the function fails with `HttpError 403: The caller does not have permission`.
> `Project Billing Manager` is the minimal role — it only allows linking/unlinking billing on a project, unlike `Owner` which grants full project control.

✅ **Done when:** service account has **Billing Account Administrator** (Billing IAM) + **Project Billing Manager** (Project IAM)

---

## Step 6 — Verify the Setup

Open **Cloud Shell** (`>_` icon in top right bar). Set your project first:

```bash
gcloud config set project YOUR_PROJECT_ID
```

```bash
# Check 1 — function is deployed (replace asia-south1 if you chose a different region)
gcloud run services list --region=asia-south1
# Expected: billing-killswitch ... READY

# Check 2 — Pub/Sub topic exists
gcloud pubsub topics list
# Expected: name: projects/YOUR_PROJECT/topics/billing-killswitch

# Check 3 — no errors in logs yet
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=billing-killswitch" \
  --limit=20 --format="table(timestamp, textPayload)"
```

✅ **Done when:** all three commands return expected output

---

## Step 7 — End-to-End Test

> ⚠️ Both options actually disable billing. Re-enable immediately after.

### Option A — ₹1 Test Budget (use when you have some spend this month)

Since your project has already spent more than ₹1, the alert fires automatically within minutes.

1. Repeat Step 3 with: Name `killswitch-TEST` | Amount `₹1` | Threshold `100%` only | same Pub/Sub topic
2. Watch logs:
   ```bash
   watch -n 30 "gcloud logging read \
     'resource.type=cloud_run_revision AND resource.labels.service_name=billing-killswitch' \
     --limit=10 --format='table(timestamp,textPayload)'"
   ```
3. Expected output:
   ```
   Budget check → Spent: ₹X | Limit: ₹1
   OVER BUDGET! ₹X > ₹1. Disabling billing now...
   ✅ Billing DISABLED for project: your-project-id
   ```
4. Confirm disabled: `gcloud beta billing projects describe YOUR_PROJECT_ID | grep billingEnabled`
5. **Re-enable:** Billing → Account management → Link a billing account → `your-billing-account` → Save
6. **Delete test budget:** Billing → Budgets & alerts → `killswitch-TEST` → Delete

---

### Option B — Fake Pub/Sub Message (use when current spend is ₹0)

```bash
# Publish a fake over-budget message
gcloud pubsub topics publish billing-killswitch \
  --message='{"costAmount": 1500, "budgetAmount": 1000, "budgetDisplayName": "killswitch-budget"}'

# Watch logs
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=billing-killswitch" \
  --limit=10 --format="table(timestamp, textPayload)" --freshness=5m
```

Expected:
```
Budget check → Spent: ₹1500.0 | Limit: ₹1000.0
OVER BUDGET! ₹1500.0 > ₹1000.0. Disabling billing now...
✅ Billing DISABLED for project: your-project-id
```

**Re-enable:** Billing → Account management → Link a billing account → Save

---

## ✅ You're Done

Kill switch is live. You never need to touch this again unless you want to change the limit.

---

## Quick Reference

| Task | How |
|------|-----|
| Change budget limit | Billing → Budgets & alerts → `killswitch-budget` → Edit |
| Re-enable billing after kill | Billing → Account management → Link billing account |
| Check if kill switch fired | Cloud Run → `billing-killswitch` → Logs tab |
| Check current spend | Billing → Reports → filter by date range on right panel |
