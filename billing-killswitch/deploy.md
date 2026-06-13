# Deploy Guide — GCP Billing Kill Switch

Follow these steps in order. Takes about 10 minutes total.
All steps are done in GCP Console. No CLI needed for setup.
gcloud commands are only used for verification and testing at the end.

---

## Before You Start — Note These Down

You'll need these two values during setup:

| What | Where to find it | Your value |
|------|-----------------|------------|
| Project ID | GCP Console → top bar dropdown | e.g. `housing-society-bot` |
| Billing Account ID | Billing → Account management → "ID" column | e.g. `ABCD12-EFGH34-IJKL56` |

---

## Step 1 — Enable Required APIs

Go to: **GCP Console → APIs & Services → Enable APIs and Services**

Search and enable each of these:
- `Cloud Functions API`
- `Cloud Billing API`
- `Cloud Pub/Sub API`

> Each one has an "Enable" button. Click it and wait for the green tick.

---

## Step 2 — Create Pub/Sub Topic

This is the "pipe" that budget alerts flow through to reach your function.

1. GCP Console → search **"Pub/Sub"** in the top search bar
2. Click **"Create Topic"**
3. Topic ID: `billing-killswitch`
4. Uncheck "Add a default subscription" (not needed)
5. Click **Create**

✅ You should see `billing-killswitch` listed in your topics.

---

## Step 3 — Create Budget Alert

This watches your spend and fires a message when you hit ₹2,000.

1. GCP Console → **Billing → Budgets & alerts → Create Budget**
2. Fill in:
   - Name: `killswitch-budget`
   - Time range: `Monthly`
   - Projects: select your project
   - Amount: `₹2000`
3. Set alert thresholds (click "Add threshold rule" for each):
   - `50%` of budget → email alert
   - `90%` of budget → email alert
   - `100%` of budget → this triggers the kill switch
4. Scroll to **"Manage notifications"**
   - Toggle ON: **"Connect a Pub/Sub topic"**
   - Select: `billing-killswitch` (the topic you just created)
5. Click **Save**

✅ Budget should appear in your Budgets & alerts list.

---

## Step 4 — Deploy the Cloud Function

This is the function that actually disables billing.

1. GCP Console → search **"Cloud Functions" → Create Function**
2. **Basics tab:**
   - Environment: `2nd gen`
   - Function name: `billing-killswitch`
   - Region: `asia-south1` (Mumbai — lowest latency for you)
3. **Trigger tab:**
   - Trigger type: `Cloud Pub/Sub`
   - Topic: select `billing-killswitch`
   - Click **Save**
4. Click **Next**
5. **Code tab:**
   - Runtime: `Python 3.11`
   - Entry point: `stop_billing`
   - In the `main.py` file in the editor: **delete everything** and paste the contents of `main.py` from this folder
   - Click on `requirements.txt` tab in the editor: **delete everything** and paste the contents of `requirements.txt` from this folder
6. **Environment variables** (still on Code tab, scroll down):
   - Click "Add variable"
   - Name: `PROJECT_ID`
   - Value: your project ID (e.g. `housing-society-bot`)
7. Click **Deploy**

> Deployment takes 2–3 minutes. Wait for the green tick next to the function name.

✅ Function should show status: **Active**

---

## Step 5 — Grant Billing Permission to the Function

This is the most important step. Without this, the function can't disable billing.

1. GCP Console → **Cloud Functions** → click `billing-killswitch`
2. Go to **Details tab**
3. Find **"Service account"** — copy that email address
   (looks like: `billing-killswitch@your-project.iam.gserviceaccount.com`)
4. Go to **Billing → Account management → IAM** (top right area of billing page)
5. Click **"Add"** (or Grant Access)
6. Paste the service account email
7. Role: **Billing Account Administrator**
8. Click **Save**

✅ The function now has permission to disable billing.

---

## Step 6 — Verify Everything is Set Up

Run these commands in **Cloud Shell** (GCP Console → top right terminal icon).
No local installation needed — Cloud Shell has gcloud pre-installed.

```bash
# Check function is deployed and active
gcloud functions list --region=asia-south1

# Expected output: billing-killswitch ... ACTIVE
```

```bash
# Check Pub/Sub topic exists
gcloud pubsub topics list

# Expected output: name: projects/YOUR_PROJECT/topics/billing-killswitch
```

```bash
# Check function logs (should be empty at this point — no triggers yet)
gcloud functions logs read billing-killswitch \
  --region=asia-south1 \
  --limit=20
```

✅ If all three commands return expected output, setup is complete.

---

## Step 7 — Test the Kill Switch (Real End-to-End Test)

This is a real test using a ₹1 budget — the kill switch will actually fire.

> ⚠️ Your project services will stop briefly. Re-enable billing after the test (see below).
> ⚠️ Do this when you're not actively using the project.

### 7a — Create a Test Budget (₹1 limit)

Repeat Step 3 but with:
- Name: `killswitch-TEST`
- Amount: `₹1`
- Same Pub/Sub topic: `billing-killswitch`
- Threshold: `100%` only

Since your project has already spent more than ₹1 this month, the alert will fire within minutes.

### 7b — Watch the Logs

```bash
# Run this in Cloud Shell and keep watching (updates every 30 seconds)
watch -n 30 "gcloud functions logs read billing-killswitch --region=asia-south1 --limit=10"
```

### 7c — What You Should See in Logs

```
Budget check → Spent: ₹X | Limit: ₹1
OVER BUDGET! ₹X > ₹1. Disabling billing now...
✅ Billing DISABLED for project: your-project-id
```

### 7d — Confirm Billing is Disabled

```bash
gcloud beta billing projects describe YOUR_PROJECT_ID | grep billingEnabled
# Expected: billingEnabled: false
```

### 7e — Re-enable Billing Immediately After Test

1. GCP Console → **Billing**
2. Your project will show "Billing disabled"
3. Click **"Link a billing account"** → select your account → Save

```bash
# Confirm billing is back on
gcloud beta billing projects describe YOUR_PROJECT_ID | grep billingEnabled
# Expected: billingEnabled: true
```

### 7f — Delete the Test Budget

GCP Console → **Billing → Budgets & alerts** → click `killswitch-TEST` → Delete

> This prevents it from firing again next time you use the project.

---

## You're Done

The real `killswitch-budget` (₹2,000) is now protecting your project.
You never need to touch this again unless you want to change the limit.

### To Change the Budget Limit Later
Billing → Budgets & alerts → click `killswitch-budget` → Edit → change amount → Save
