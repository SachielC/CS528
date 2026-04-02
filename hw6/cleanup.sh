#!/bin/bash
set -e

# ////// CONFIG //////
PROJECT_ID="coral-mission-485618-m4"
ZONE="us-central1-a"
REGION="us-central1"

DB_INSTANCE_NAME="requestsdb"
SERVER_VM_NAME="hw6tosql"
STATIC_IP_NAME="hw6tosql"  # the reserved external IP

# ===== AUTHENTICATE =====
export GOOGLE_APPLICATION_CREDENTIALS="coral-mission-485618-m4-a165e80ee5db.json"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project $PROJECT_ID
echo "Authenticated with service account and project set."

# ////// DELETE VM //////

echo "Starting VM teardown..."
if gcloud compute instances describe $SERVER_VM_NAME --zone=$ZONE >/dev/null 2>&1; then
    echo "Deleting VM: $SERVER_VM_NAME..."
    gcloud compute instances delete $SERVER_VM_NAME \
      --project=$PROJECT_ID \
      --zone=$ZONE \
      --quiet
else
    echo "VM $SERVER_VM_NAME does not exist, skipping."
fi

# ////// RELEASE STATIC EXTERNAL IP //////

if gcloud compute addresses describe $STATIC_IP_NAME --region=$REGION >/dev/null 2>&1; then
    echo "Releasing static external IP: $STATIC_IP_NAME..."
    gcloud compute addresses delete $STATIC_IP_NAME \
      --project=$PROJECT_ID \
      --region=$REGION \
      --quiet
else
    echo "Static IP $STATIC_IP_NAME does not exist, skipping."
fi

# ////// DISABLE CLOUD SQL INSTANCE //////

if gcloud sql instances describe $DB_INSTANCE_NAME >/dev/null 2>&1; then
    echo "Disabling Cloud SQL instance $DB_INSTANCE_NAME..."
    gcloud sql instances patch $DB_INSTANCE_NAME --activation-policy=NEVER --quiet
else
    echo "Cloud SQL instance $DB_INSTANCE_NAME does not exist, skipping."
fi

echo "Teardown complete! All resources stopped or deleted. (︶｡︶✽)"