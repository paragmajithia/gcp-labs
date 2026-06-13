"""
GCP Billing Kill Switch
=======================
Triggered by: Pub/Sub message from GCP Budget Alert
What it does: Disables billing on your project when spend exceeds budget
Effect:       All GCP services stop immediately. No further charges.

Author note:  Keep this function deployed and forget about it.
              It only acts when budget is exceeded.
"""

import base64
import json
import os
import logging
from googleapiclient import discovery

# ─── CONFIG ──────────────────────────────────────────────────────────────────
PROJECT_ID = os.environ.get("PROJECT_ID")   # set in deploy.sh, don't hardcode
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def stop_billing(event, context):
    """
    Entry point. Called automatically by GCP when budget alert fires.

    'event' contains the Pub/Sub message with cost vs budget info.
    """

    # Step 1: Decode the Pub/Sub message
    pubsub_data = base64.b64decode(event["data"]).decode("utf-8")
    budget_msg  = json.loads(pubsub_data)

    cost_so_far  = budget_msg.get("costAmount", 0)
    budget_limit = budget_msg.get("budgetAmount", 0)

    log.info(f"Budget check → Spent: ₹{cost_so_far} | Limit: ₹{budget_limit}")

    # Step 2: Only kill billing if we've hit or exceeded the limit
    if cost_so_far <= budget_limit:
        log.info("Within budget. No action taken.")
        return

    # Step 3: We're over budget — disable billing
    log.warning(f"OVER BUDGET! ₹{cost_so_far} > ₹{budget_limit}. Disabling billing now...")
    _disable_billing(PROJECT_ID)


def _disable_billing(project_id):
    """Disconnects the billing account from the project. This stops all services."""

    if not project_id:
        raise ValueError("PROJECT_ID environment variable is not set.")

    billing   = discovery.build("cloudbilling", "v1")
    project   = f"projects/{project_id}"

    # Check if billing is already disabled (avoid unnecessary API calls)
    current   = billing.projects().getBillingInfo(name=project).execute()
    if not current.get("billingEnabled"):
        log.info("Billing already disabled. Nothing to do.")
        return

    # Unlink billing account → empty string means "no billing account"
    billing.projects().updateBillingInfo(
        name=project,
        body={"billingAccountName": ""}
    ).execute()

    log.warning(f"✅ Billing DISABLED for project: {project_id}")
    log.warning("To resume: go to GCP Console → Billing → Re-link your billing account.")
