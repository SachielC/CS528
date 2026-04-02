#!/bin/bash
set -e

# ////// CONFIG //////

PROJECT_ID="coral-mission-485618-m4"
ZONE="us-central1-a"
REGION="us-central1"

DB_INSTANCE_NAME="requestsdb"
DB_NAME="hw6"
DB_USER="sachvm"
DB_PASS="sachpass"

SERVER_VM_NAME="hw6automated"
VM_IMAGE_NAME="projects/coral-mission-485618-m4/global/machineImages/hw6vmfixed"
VM_MACHINE_TYPE="e2-micro"

BUCKET_NAME="hw2bucketmanyrank"

# ===== AUTHENTICATE =====
export GOOGLE_APPLICATION_CREDENTIALS="coral-mission-485618-m4-a165e80ee5db.json"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project $PROJECT_ID
echo "Authenticated with service account."

# ////// CLOUD SQL //////

echo "Setting up Cloud SQL instance..."
if gcloud sql instances describe $DB_INSTANCE_NAME >/dev/null 2>&1; then
    echo "Starting existing Cloud SQL..."
    gcloud sql instances patch $DB_INSTANCE_NAME --activation-policy=ALWAYS --quiet
else
    echo "Creating Cloud SQL instance..."
    gcloud sql instances create $DB_INSTANCE_NAME \
        --database-version=MYSQL_8_0 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password=$DB_PASS --quiet

    gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME --quiet
    gcloud sql users create $DB_USER --instance=$DB_INSTANCE_NAME --password=$DB_PASS --quiet
fi

# Get DB IP dynamically
DB_HOST=$(gcloud sql instances describe $DB_INSTANCE_NAME \
    --format="value(ipAddresses[0].ipAddress)")
echo "DB HOST: $DB_HOST"

# ////// STARTUP SCRIPT //////

cat << 'EOF' > hw6-startup.sh
#!/bin/bash
if [ -f /var/log/startup_done ]; then exit 0; fi
cd /home/sach || exit 1

# Load DB credentials from instance metadata
export DB_HOST=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_HOST)
export DB_USER=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_USER)
export DB_PASS=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_PASS)
export DB_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_NAME)

export GOOGLE_APPLICATION_CREDENTIALS=/home/sach/hw-service-account.json
export BUCKET_NAME=hw2bucketmanyrank

# Activate virtual environment
source venv/bin/activate

echo "Running hw6.py with KNN and LightGBM..."
python3 hw6.py

echo "Fetching output files from bucket..."
gsutil cat gs://$BUCKET_NAME/supervised_income_predictions.csv

touch /var/log/startup_done
EOF

# ////// CREATE VM //////

echo "Creating VM: $SERVER_VM_NAME..."
gcloud compute instances create $SERVER_VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=$VM_MACHINE_TYPE \
  --boot-disk-size=10GB \
  --source-machine-image=$VM_IMAGE_NAME \
  --metadata-from-file startup-script=hw6-startup.sh \
  --metadata=DB_HOST=$DB_HOST,DB_USER=$DB_USER,DB_PASS=$DB_PASS,DB_NAME=$DB_NAME \
  --address=hw6automated  --tags=http-server \
  --quiet


echo "VM created. Startup script will run on boot. "

