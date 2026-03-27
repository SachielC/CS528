#!/bin/bash
set -e

# ////// CONFIG //////

PROJECT_ID="coral-mission-485618-m4"
ZONE="us-central1-a"
INSTANCE_NAME="requestsdb"

SERVER_VM_NAME="web-server-vm-auto"
SUBSCRIBER_VM_NAME="subscriber-vm-auto"

# ===== AUTHENTICATE WITH SERVICE ACCOUNT =====
export GOOGLE_APPLICATION_CREDENTIALS="C:/Users/chuck/Downloads/coral-mission-485618-m4-a165e80ee5db.json"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project $PROJECT_ID

echo "Authenticated with service account and project set."

# ////// DELETE VMs //////

echo "Starting VM teardown..."

if gcloud compute instances describe $SERVER_VM_NAME --zone=$ZONE >/dev/null 2>&1; then
    echo "Deleting $SERVER_VM_NAME..."
    gcloud compute instances delete $SERVER_VM_NAME \
      --project=$PROJECT_ID \
      --zone=$ZONE \
      --quiet
else
    echo "$SERVER_VM_NAME does not exist, skipping."
fi

if gcloud compute instances describe $SUBSCRIBER_VM_NAME --zone=$ZONE >/dev/null 2>&1; then
    echo "Deleting $SUBSCRIBER_VM_NAME..."
    gcloud compute instances delete $SUBSCRIBER_VM_NAME \
      --project=$PROJECT_ID \
      --zone=$ZONE \
      --quiet
else
    echo "$SUBSCRIBER_VM_NAME does not exist, skipping."
fi

# ////// DISABLE / DELETE CLOUD SQL //////

if gcloud sql instances describe $INSTANCE_NAME >/dev/null 2>&1; then
    echo "Disabling Cloud SQL instance $INSTANCE_NAME..."
    gcloud sql instances patch $INSTANCE_NAME --activation-policy=NEVER --quiet

else
    echo "Cloud SQL instance $INSTANCE_NAME does not exist, skipping."
fi

echo "Teardown complete! All resources stopped or deleted. (︶｡︶✽)"