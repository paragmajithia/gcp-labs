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
import flask
from googleapiclient import discovery

# ─── CONFIG ──────────────────────────────────────────────────────────────────
PROJECT_ID = os.environ.get("PROJECT_ID")   # set as environment variable in Cloud Run
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def stop_billing(request: flask.Request):
    """
    Entry point. Called automatically by GCP when budget alert fires via Pub/Sub.

    Cloud Run functions framework passes a Flask 'request' object.
    The Pub/Sub message is inside request.get_json() → 'message' → 'data'.
    """

    # Step 1: Extract the Pub/Sub message from the HTTP request body
    envelope = request.get_json(silent=True)
    if not envelope or "message" not in envelope:
        log.error("Invalid Pub/Sub message format received.")
        return "Bad Request: missing message", 400

    pubsub_message = envelope["message"]

    # Step 2: Decode the base64-encoded message data
    if "data" not in pubsub_message:
        log.error("No data field in Pub/Sub message.")
        return "Bad Request: missing data", 400

    pubsub_data = base64.b64decode(pubsub_message["data"]).decode("utf-8")
    budget_msg  = json.loads(pubsub_data)

    cost_so_far  = budget_msg.get("costAmount", 0)
    budget_limit = budget_msg.get("budgetAmount", 0)

    log.info(f"Budget check → Spent: ₹{cost_so_far} | Limit: ₹{budget_limit}")

    # Step 3: Only kill billing if we've hit or exceeded the limit
    if cost_so_far <= budget_limit:
        log.info("Within budget. No action taken.")
        return "OK: within budget", 200

    # Step 4: Over budget — disable billing
    log.warning(f"OVER BUDGET! ₹{cost_so_far} > ₹{budget_limit}. Disabling billing now...")
    _disable_billing(PROJECT_ID)
    return "OK: billing disabled", 200


def _disable_billing(project_id):
    """Disconnects the billing account from the project. This stops all services."""

    if not project_id:
        raise ValueError("PROJECT_ID environment variable is not set.")

    billing = discovery.build("cloudbilling", "v1")
    project = f"projects/{project_id}"

    # Check if billing is already disabled (avoid unnecessary API calls)
    current = billing.projects().getBillingInfo(name=project).execute()
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
