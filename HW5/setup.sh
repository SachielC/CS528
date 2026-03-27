#!/bin/bash
set -e

# ////// CONFIG //////

PROJECT_ID="coral-mission-485618-m4"
ZONE="us-central1-a"
REGION="us-central1"

SERVER_VM_NAME="web-server-vm-auto"
SUBSCRIBER_VM_NAME="subscriber-vm-auto"

SERVER_IMAGE="projects/coral-mission-485618-m4/global/machineImages/tosqlhw5"
SUBSCRIBER_IMAGE="projects/coral-mission-485618-m4/global/machineImages/subscriberimg"

INSTANCE_NAME="requestsdb"
DB_NAME="requestsdb"
DB_USER="sachvm"
DB_PASS="sachpass"

# ===== AUTHENTICATE WITH SERVICE ACCOUNT =====
export GOOGLE_APPLICATION_CREDENTIALS="coral-mission-485618-m4-a165e80ee5db.json"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project $PROJECT_ID

echo "Authenticated with service account and project set."

# ////// CLOUD SQL //////


echo "Checking Cloud SQL..."

if gcloud sql instances describe $INSTANCE_NAME >/dev/null 2>&1; then
    echo "Starting existing Cloud SQL..."
    gcloud sql instances patch $INSTANCE_NAME --activation-policy=ALWAYS
else
    echo "Creating Cloud SQL instance..."
    gcloud sql instances create $INSTANCE_NAME \
        --database-version=MYSQL_8_0 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password=$DB_PASS \
        --quiet

    gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME --quiet

    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password=$DB_PASS \
        --quiet
fi

# Get DB IP dynamically
DB_HOST=$(gcloud sql instances describe $INSTANCE_NAME \
    --format="value(ipAddresses[0].ipAddress)")

echo "DB HOST: $DB_HOST"

# ////// STARTUP SCRIPTS //////

cat << 'EOF' > server-startup.sh
#!/bin/bash
if [ -f /var/log/startup_already_done ]; then
    echo "Already ran"
    exit 0
fi
cd /home/sach || exit 1

DB_HOST=$(curl -H "Metadata-Flavor: Google" \
http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_HOST)
DB_USER=$(curl -H "Metadata-Flavor: Google" \
http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_USER)
DB_PASS=$(curl -H "Metadata-Flavor: Google" \
http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_PASS)
DB_NAME=$(curl -H "Metadata-Flavor: Google" \
http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_NAME)

export DB_HOST DB_USER DB_PASS DB_NAME
export GOOGLE_APPLICATION_CREDENTIALS=/home/sach/hw-service-account.json
export BUCKET_NAME=hw2bucketmanyrank
export TOPIC_NAME=forbidden-topic
export GCP_PROJECT=coral-mission-485618-m4

nohup python3 server.py > server.log 2>&1 &
touch /var/log/startup_already_done
EOF

cat << 'EOF' > subscriber-startup.sh
#!/bin/bash
if [ -f /var/log/startup_already_done ]; then
    exit 0
fi
cd /home/sach || exit 1

export GOOGLE_APPLICATION_CREDENTIALS=/home/sach/hw-service-account.json
export BUCKET_NAME=hw2bucketmanyrank
export TOPIC_NAME=forbidden-topic
export GCP_PROJECT=coral-mission-485618-m4

nohup python3 subscriber.py > subscriber.log 2>&1 &
touch /var/log/startup_already_done
EOF

# ////// CREATE VMs //////

echo "Creating server VM..."
gcloud compute instances create $SERVER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --boot-disk-size=10GB \
  --source-machine-image=$SERVER_IMAGE \
  --tags=http-server \
  --metadata-from-file startup-script=server-startup.sh \
  --metadata=DB_HOST=$DB_HOST,DB_USER=$DB_USER,DB_PASS=$DB_PASS,DB_NAME=$DB_NAME \
  --quiet

echo "Creating subscriber VM..."
gcloud compute instances create $SUBSCRIBER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --boot-disk-size=10GB \
  --source-machine-image=$SUBSCRIBER_IMAGE \
  --metadata-from-file startup-script=subscriber-startup.sh \
  --quiet

echo "Opening port 8080..."
gcloud compute firewall-rules create allow-http-8080 \
  --allow tcp:8080 \
  --target-tags=http-server || true

echo "Setup complete! ヽ(◕ヮ◕)ﾉ"