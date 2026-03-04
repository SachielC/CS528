#!/bin/bash

LOCK_FILE="/var/log/webserver_setup.lock"

if [ ! -f "$LOCK_FILE" ]; then
    echo "First boot setup: installing dependencies and configuring server..."

    apt update
    apt install -y python3-pip curl

    pip3 install google-cloud-storage google-cloud-pubsub

    export BUCKET_NAME=hw2bucketmanyrank
    export TOPIC_NAME=forbidden-topic
    export GCP_PROJECT=coral-mission-485618-m4

    # Download server.py directly from GitHub
    curl -o /home/server.py https://raw.githubusercontent.com/SachielC/CS528/main/HW4/server.py
    chmod +x /home/server.py

    # Start server in background
    nohup python3 /home/server.py > /home/server.log 2>&1 &

    touch "$LOCK_FILE"
fi
