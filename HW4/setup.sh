#!/bin/bash

# Lock file to prevent re-running on reboot
LOCK_FILE="/var/log/webserver_setup.lock"

if [ ! -f "$LOCK_FILE" ]; then
    echo "First boot setup: installing dependencies and configuring server..."

    # Update system & install Python3 and curl
    apt update
    apt install -y python3-pip curl

    # Install Google Cloud client libraries
    pip3 install google-cloud-storage google-cloud-pubsub

    # Set environment variables globally for this session
    echo "export BUCKET_NAME=hw2bucketmanyrank" >> /etc/profile.d/webserver.sh
    echo "export TOPIC_NAME=forbidden-topic" >> /etc/profile.d/webserver.sh
    echo "export GCP_PROJECT=coral-mission-485618-m4" >> /etc/profile.d/webserver.sh
    source /etc/profile.d/webserver.sh

    # Create directory for server script
    mkdir -p /home/sach

    # Download server.py from GitHub (http.server version)
    curl -o /home/sach/server.py https://raw.githubusercontent.com/SachielC/CS528/main/HW4/server.py
    chmod +x /home/sach/server.py

    # Create systemd service so server starts automatically on boot
    cat <<EOF > /etc/systemd/system/web-server.service
[Unit]
Description=Python HTTP Server for GCP Assignment
After=network.target

[Service]
Type=simple
User=sach
WorkingDirectory=/home/sach
ExecStart=/usr/bin/python3 /home/sach/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable the service
    systemctl daemon-reload
    systemctl enable web-server.service
    systemctl start web-server.service

    # Mark setup as done
    touch "$LOCK_FILE"
fi