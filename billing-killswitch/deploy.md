# Deploy Guide — GCP Billing Kill Switch

**Time required:** ~15 minutes  
**All setup is done via GCP Console** (no CLI needed for setup)  
**Cloud Shell** (browser terminal) is only used for verification and testing at the end

---

## Before You Start

Note these two values — you will need them during setup:

| What | Where to find it | Example |
|------|-----------------|---------|
| **Project ID** | GCP Console → top bar project dropdown | `gcp-labs` |
| **Billing Account ID** | Billing → Account management → ID field | `01489A-10A50B-0CFF2D` |

---

## Overview of What You Are Building

```
Monthly spend hits ₹1,000
        ↓
Budget Alert fires → sends message to Pub/Sub topic
        ↓
Cloud Run Function wakes up → checks: am I over budget?
        ↓ YES
Billing account unlinked from project
        ↓
All GCP services stop. Zero further charges.
```

---

## Step 1 — Enable Required APIs

**Navigate to:** GCP Console → APIs & Services → Enable APIs and Services

Search and enable each of the following one by one:

| API to enable | Why it's needed |
|--------------|-----------------|
| `Cloud Run API` | Runs your kill switch function |
| `Cloud Billing API` | Lets function disable/enable billing on your project |
| `Cloud Pub/Sub API` | Receives budget alert messages |
| `Cloud Billing Budget API` | Creates and monitors your budget |
| `Cloud Resource Manager API` | Required by billing API to look up project info |

> Each has an **Enable** button. Click and wait for the green tick before moving to the next.

✅ **Done when:** all four APIs show as Enabled

---

## Step 2 — Create Pub/Sub Topic

The Pub/Sub topic is the "pipe" through which budget alerts flow to your function.

1. GCP Console → search **"Pub/Sub"** in the top search bar → open it
2. Click **"Create Topic"**
3. Set:
   - Topic ID: `billing-killswitch`
   - Uncheck **"Add a default subscription"** (not needed)
4. Click **Create**

✅ **Done when:** `billing-killswitch` appears in your topics list

---

## Step 3 — Create Budget Alert

This watches your monthly spend and fires a Pub/Sub message when you hit your limit.

1. GCP Console → **Billing → Budgets & alerts → Create Budget**
2. Fill in:
   - Name: `killswitch-budget`
   - Time range: `Monthly`
   - Projects: select your project (`gcp-labs`)
   - Amount: `₹1000` (or your chosen limit)
3. Set alert thresholds:
   - `50%` → ₹500 — early warning email
   - `90%` → ₹900 — final warning email
   - `100%` → ₹1000 — **this one triggers the kill switch**

   > All thresholds share the same notification channels (GCP limitation).
   > The function only acts at 100% — it ignores the 50% and 90% messages.

4. Under **"Manage notifications"**:
   - ✅ Tick **"Email alerts to billing admins and users"**
   - ✅ Tick **"Email alerts to project owners"** ← so you personally get warned
   - ✅ Tick **"Connect a Pub/Sub topic"** → select `billing-killswitch`
5. Click **Save**

✅ **Done when:** `killswitch-budget` appears in your Budgets & alerts list

---

## Step 4 — Deploy the Cloud Run Function

This is the function that actually disables billing when the budget is exceeded.

> **Note:** GCP has unified Cloud Functions into Cloud Run.
> Searching "Cloud Functions" lands you on Cloud Run — that is correct.

### 4a — Create the service

1. GCP Console → search **"Cloud Run"** → open it
2. Scroll to **"Write a function"** section → click **"Python"**
3. Fill in:
   - Service name: `billing-killswitch`
   - Region: `asia-south1` (Mumbai)

### 4b — Add Pub/Sub trigger

4. Scroll to **"Trigger"** → click **"+ Add trigger"** → select **"Cloud Pub/Sub"**
5. In the side panel that opens:
   - Select topic: `billing-killswitch`
   - Service account: leave as `Compute Engine default service account`
   - A yellow warning appears: *"You need to grant the following roles..."*
   - Click **"Grant all"** ← this allows Pub/Sub to invoke your function
   - Click **"Save"** on the side panel

### 4c — Paste the code

6. In the inline code editor:
   - Runtime: `Python 3.14` (or latest available)
   - Entry point: `stop_billing`
   - In the **`main.py`** tab: delete everything → paste contents of `main.py` from this folder
   - In the **`requirements.txt`** tab: delete everything → paste contents of `requirements.txt` from this folder

### 4d — Add environment variable

7. Scroll to **"Environment variables"** → click **"Add variable"**:
   - Name: `PROJECT_ID`
   - Value: your project ID (e.g. `gcp-labs`)

### 4e — Configure remaining settings

Scroll down and set the following:

| Section | Setting | Value | Why |
|---------|---------|-------|-----|
| **Authentication** | Mode | Require authentication + IAM | Only Pub/Sub can call this, not public internet |
| **Billing** | Type | Request-based | Charged only when function runs — near zero cost |
| **Service Scaling** | Min instances | `0` | No idle cost; spins up only when triggered |
| **Service Scaling** | Max instances | leave blank | Default is fine |
| **Ingress** | Access | Internal | Callable only from within GCP, not public internet |

8. Click **"Create"** at the bottom

> Deployment takes 2–3 minutes. Wait for the green tick.

✅ **Done when:** `billing-killswitch` shows as **Ready** in Cloud Run → Services

---

## Step 5 — Grant Billing Permission to the Function

This is the most critical step. The function runs as a **robot identity** (service account),
not as you. That robot needs permission to disable billing — without this, the kill switch silently fails.

> **Your Gmail vs the Service Account**
> - `paraginsights@gmail.com` — that's you, the human. Already in billing IAM. Leave it as is.
> - `xxxx-compute@developer.gserviceaccount.com` — that's the robot your function runs as. This is what you need to add.

### 5a — Find the service account email

The email was shown in the yellow **"Grant all"** warning during Step 4 (Pub/Sub trigger setup).
It looks like:
```
1009281923079-compute@developer.gserviceaccount.com
```
If you did not note it down, find it via either of these:

**Option A — YAML tab (fastest):**
1. GCP Console → **Cloud Run** → click `billing-killswitch`
2. Click the **"YAML"** tab
3. Search for `serviceAccountName:` — the email is right there

**Option B — Edit revision:**
1. GCP Console → **Cloud Run** → click `billing-killswitch`
2. Click **"Edit & deploy new revision"** at the top
3. Scroll to the **"Security"** section in the edit form
4. **"Service account"** field shows the email clearly
5. Copy it → click **Cancel** (do not deploy)
### 5b — Add it to Billing IAM

4. GCP Console → **Billing → Account management**
5. On the right panel, click **"Add principal"**
6. In **"New principals"**: paste the service account email you just copied
7. In **"Role"**: select **Billing Account Administrator**
8. Click **Save**

### 5c — Add it to Project IAM (IMPORTANT)

The Billing Account Administrator role alone is **not sufficient**.
The Cloud Billing API also checks permissions on the project itself.

1. GCP Console → **IAM & Admin → IAM**
2. Click **Grant access**
3. In **New principals**: paste the same service account email
4. In **Role**: select **Owner**
5. Click **Save**

> During testing, if this permission is missing, the function fails with:
>
> ```
> HttpError 403:
> The caller does not have permission
> ```
>
> You can verify the service account roles with:
>
> ```bash
> gcloud projects get-iam-policy YOUR_PROJECT_ID > --flatten="bindings[].members" > --filter="bindings.members:SERVICE_ACCOUNT_EMAIL" > --format="table(bindings.role)"
> ```
>
> If you only see:
>
> ```
> roles/run.builder
> roles/run.invoker
> ```
>
> then the required project permission has not been granted.

✅ **Done when:** the service account appears as:
- Billing Account Administrator (Billing IAM)
- Owner (Project IAM)

---

## Step 6 — Verify the Setup

Open **Cloud Shell** from GCP Console (click the `>_` terminal icon in the top right bar).
Cloud Shell has `gcloud` pre-installed — no local setup needed.

**First — set your active project in Cloud Shell (required before any other command):**
```bash
# List your projects to find the correct project ID
gcloud projects list

# Set the active project (replace with your actual project ID from the list above)
gcloud config set project project-207daf80-c763-429b-8cb
```

> You must do this every time you open a fresh Cloud Shell session. Otherwise commands
> may run against the wrong project or fail with "project not found" errors.

**Check 1 — Function is deployed and ready:**
```bash
gcloud run services list --region=asia-south1
# Expected: billing-killswitch ... READY
```

**Check 2 — Pub/Sub topic exists:**
```bash
gcloud pubsub topics list
# Expected: name: projects/YOUR_PROJECT/topics/billing-killswitch
```

**Check 3 — Function has no errors yet (logs should be empty):**
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=billing-killswitch" \
  --limit=20 \
  --format="table(timestamp, textPayload)"
```

✅ **Done when:** all three commands return expected output with no errors

---

## Step 7 — End-to-End Test (Real Kill Switch Test)

Choose **one** of the two options below based on your current spend.
Both options test the full chain: Pub/Sub → Function → Billing API.

---

### Option A — ₹1 Test Budget (use when you have some spend this month)

This creates a real budget at ₹1. Since your project has already spent more than ₹1,
the alert fires automatically within minutes — no manual action needed.

> ⚠️ **Warning:** Your GCP services will briefly stop during this test.
> ⚠️ Do this when you are not actively running anything on the project.
> ⚠️ You must re-enable billing after the test (takes 2 minutes).

### 7a — Create a ₹1 test budget

Repeat Step 3 with these values only:
- Name: `killswitch-TEST`
- Amount: `₹1`
- Threshold: `100%` only
- Connect same Pub/Sub topic: `billing-killswitch`

Since your project has already spent more than ₹1 this month, the alert fires within minutes.

### 7b — Watch the function logs

Run this in Cloud Shell and keep it open:
```bash
watch -n 30 "gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=billing-killswitch' \
  --limit=10 --format='table(timestamp,textPayload)'"
```

### 7c — Expected log output

Within a few minutes you should see:
```
Budget check → Spent: ₹X | Limit: ₹1
OVER BUDGET! ₹X > ₹1. Disabling billing now...
✅ Billing DISABLED for project: gcp-labs
```

### 7d — Confirm billing is disabled

```bash
gcloud beta billing projects describe YOUR_PROJECT_ID | grep billingEnabled
# Expected: billingEnabled: false
```

### 7e — Re-enable billing immediately after test

1. GCP Console → **Billing → Account management**
2. Your project will show "Billing disabled"
3. Click **"Link a billing account"** → select `gcp-labs-billing` → Save

```bash
# Confirm billing is back on
gcloud beta billing projects describe YOUR_PROJECT_ID | grep billingEnabled
# Expected: billingEnabled: true
```

### 7f — Delete the test budget

GCP Console → **Billing → Budgets & alerts** → click `killswitch-TEST` → **Delete**

> If you skip this, the ₹1 budget will keep firing the kill switch every time GCP reports costs.

✅ **Done when:** only `killswitch-budget` remains in your budgets list, `killswitch-TEST` is gone

---

### Option B — Publish Fake Message via Cloud Shell (use when current spend is ₹0)

If your project has ₹0 spend this month, the ₹1 budget won't fire automatically.
Instead, publish a fake budget message directly to Pub/Sub — the function receives it
exactly as if a real budget alert fired. Same end-to-end chain, crafted message.

> ⚠️ **Warning:** This will actually disable your billing — it is a real test, not a dry run.
> ⚠️ You must re-enable billing immediately after (takes 2 minutes).

**7g — Publish a fake over-budget message:**
```bash
gcloud pubsub topics publish billing-killswitch   --message='{"costAmount": 1500, "budgetAmount": 1000, "budgetDisplayName": "killswitch-budget"}'
```

This tells the function: "you have spent ₹1500 against a ₹1000 budget" — triggering the kill switch.

**7h — Watch the logs immediately after:**
```bash
gcloud logging read   "resource.type=cloud_run_revision AND resource.labels.service_name=billing-killswitch"   --limit=10   --format="table(timestamp, textPayload)"   --freshness=5m
```

Expected output:
```
Budget check → Spent: ₹1500.0 | Limit: ₹1000.0
OVER BUDGET! ₹1500.0 > ₹1000.0. Disabling billing now...
✅ Billing DISABLED for project: gcp-labs
```

**7i — Confirm billing is disabled:**
```bash
gcloud beta billing projects describe project-207daf80-c763-429b-8cb | grep billingEnabled
# Expected: billingEnabled: false
```

**7j — Re-enable billing immediately:**

1. GCP Console → **Billing → Account management**
2. Your project will show "Billing disabled"
3. Click **"Link a billing account"** → select `gcp-labs-billing` → Save

```bash
# Confirm billing is back on
gcloud beta billing projects describe project-207daf80-c763-429b-8cb | grep billingEnabled
# Expected: billingEnabled: true
```

✅ **Done when:** billing is re-enabled and logs show the expected kill switch output

---

## You're Done ✅

The kill switch is live and protecting your project.
You never need to touch this again unless you want to change the limit.

---

## Quick Reference

| Task | How |
|------|-----|
| Change the budget limit | Billing → Budgets & alerts → `killswitch-budget` → Edit → change amount |
| Re-enable billing after a kill | Billing → Account management → Link billing account |
| Check if kill switch fired | Cloud Run → `billing-killswitch` → Logs tab |
| Check current spend | Billing → Reports → Group by SKU → This month |
