#!/bin/bash

PROJECT_ID="coral-mission-485618-m4"
ZONE="us-central1-a"

-
SERVER_VM_NAME="web-server-vm"
SUBSCRIBER_VM_NAME="subscriber-vm"

echo "Starting VM teardown..."


echo "Deleting $SERVER_VM_NAME..."
gcloud compute instances delete $SERVER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --quiet

# 

echo "Deleting $SUBSCRIBER_VM_NAME..."
gcloud compute instances delete $SUBSCRIBER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --quiet

echo "VM teardown complete. All instances deleted."