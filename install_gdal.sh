#!/bin/bash
# GDAL Installation Script
# Run this script with sudo: sudo bash install_gdal.sh

echo "Installing GDAL and dependencies..."
apt-get update
apt-get install -y gdal-bin libgdal-dev python3-gdal

echo "GDAL installation complete!"
echo "You can now run migrations and start the server."

