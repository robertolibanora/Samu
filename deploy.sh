#!/bin/bash

# ============================================
# SAMU – SAFE DEPLOY SCRIPT
# ============================================

set -e  # interrompe lo script al primo errore

PROJECT_DIR="/var/www/samu"
SERVICE_NAME="samu"

echo "🚀 Deploy SAMU started..."

cd $PROJECT_DIR

echo "📦 Pulling latest code from GitHub..."
git pull

echo "🔄 Restarting systemd service ($SERVICE_NAME)..."
sudo systemctl restart $SERVICE_NAME

echo "⏱️ Waiting for service to stabilize..."
sleep 2

echo "🔍 Service status:"
systemctl status $SERVICE_NAME --no-pager

echo "✅ Deploy completed successfully."