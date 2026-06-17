#!/usr/bin/env bash
set -euo pipefail

CAMERA_IP="10.100.10.100"
CAMERA_USER="root"

scp Camera_scripts/capture_remote.py ${CAMERA_USER}@${CAMERA_IP}:/root/scripts/
scp Camera_scripts/camera_control.py ${CAMERA_USER}@${CAMERA_IP}:/root/scripts/
scp Camera_scripts/camera_config.py ${CAMERA_USER}@${CAMERA_IP}:/root/scripts/

ssh ${CAMERA_USER}@${CAMERA_IP} "mkdir -p /root/scripts/data /root/scripts/logs"

echo "Camera scripts deployed."