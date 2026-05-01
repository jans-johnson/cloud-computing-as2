#!/bin/bash
# EC2 user-data: bootstraps an Amazon Linux 2023 instance to run the
# Flask backend behind nginx on port 80.
#
# Prereqs: launch with the LabRole instance profile attached and a
# security group that allows inbound TCP 80 from anywhere (0.0.0.0/0).
# Replace REPO_URL with the URL of your shared git repo.
set -euxo pipefail

REPO_URL="${REPO_URL:-https://github.com/REPLACE-ME/cc-as2.git}"
APP_DIR=/opt/music-app

dnf install -y python3.11 python3.11-pip git nginx
systemctl enable --now nginx

# App user already exists on AL2023 as ec2-user
mkdir -p "$APP_DIR"
chown ec2-user:ec2-user "$APP_DIR"

sudo -u ec2-user git clone "$REPO_URL" "$APP_DIR"
sudo -u ec2-user python3.11 -m venv "$APP_DIR/.venv"
sudo -u ec2-user "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u ec2-user "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/backend-ec2/requirements.txt"

# nginx -> gunicorn
cp "$APP_DIR/backend-ec2/nginx.conf" /etc/nginx/conf.d/music-app.conf
rm -f /etc/nginx/conf.d/default.conf || true
nginx -t && systemctl reload nginx

# Systemd unit
cp "$APP_DIR/backend-ec2/music-app.service" /etc/systemd/system/music-app.service
systemctl daemon-reload
systemctl enable --now music-app
