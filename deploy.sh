#!/bin/bash
set -e

echo "🚀 Deploy SAMU started..."

cd /var/www/samu

echo "📦 Fetching latest code from GitHub..."
git fetch origin

echo "🔄 Resetting local code to origin/main..."
git reset --hard origin/main

echo "♻️ Restarting SAMU service..."
sudo systemctl restart samu

echo "✅ Deploy completed successfully."