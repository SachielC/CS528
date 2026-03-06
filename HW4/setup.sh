#!/bin/bash


PROJECT_ID="coral-mission-485618-m4"
ZONE="us-central1-a"


SERVER_VM_NAME="web-server-vm"
SUBSCRIBER_VM_NAME="subscriber-vm"


SERVER_IMAGE="projects/coral-mission-485618-m4/global/machineImages/serverimg"
SUBSCRIBER_IMAGE="projects/coral-mission-485618-m4/global/machineImages/subscriberimg"



# Server startup script
cat << 'EOF' > server-startup.sh
#!/bin/bash

cd /home/sach || exit 1

export GOOGLE_APPLICATION_CREDENTIALS=/home/sach/hw-service-account.json
export BUCKET_NAME=hw2bucketmanyrank
export TOPIC_NAME=forbidden-topic
export GCP_PROJECT=coral-mission-485618-m4

nohup python3 server.py > server.log 2>&1 &
EOF

# Subscriber startup script
cat << 'EOF' > subscriber-startup.sh
#!/bin/bash

cd /home/sach || exit 1

export GOOGLE_APPLICATION_CREDENTIALS=/home/sach/hw-service-account.json
export BUCKET_NAME=hw2bucketmanyrank
export TOPIC_NAME=forbidden-topic
export GCP_PROJECT=coral-mission-485618-m4

nohup python3 subscriber.py > subscriber.log 2>&1 &
EOF

gcloud compute instances create $SERVER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --boot-disk-size=10GB \
  --source-machine-image=$SERVER_IMAGE \
  --tags=http-server \
  --metadata-from-file startup-script=server-startup.sh

gcloud compute instances create $SUBSCRIBER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --boot-disk-size=10GB \
  --source-machine-image=$SUBSCRIBER_IMAGE \
  --metadata-from-file startup-script=subscriber-startup.sh


echo "All VMs created! Server and Subscriber programs should start automatically."

echo "Check startup logs with:"
echo "gcloud compute ssh $SERVER_VM_NAME --zone=$ZONE --command 'cat /var/log/startup-script.log'"
echo "gcloud compute ssh $SUBSCRIBER_VM_NAME --zone=$ZONE --command 'cat /var/log/startup-script.log'"

echo "Check running Python processes with:"
echo "gcloud compute ssh $SERVER_VM_NAME --zone=$ZONE --command 'ps aux | grep python'"
echo "gcloud compute ssh $SUBSCRIBER_VM_NAME --zone=$ZONE --command 'ps aux | grep python'"