#!/bin/bash

# Configuration
WORKDIR="$HOME/Development/remarkable_weather"
PYTHON="/usr/bin/python3"
RM1_CONFIG_NAME='remarkable'
RM1_IP='192.168.4.171'   # Replace with the IP address of your RM1 device
RM1_USER='root'        
IMAGE_PATH='weather_forecast.png'
REMOTE_IMAGE_PATH='~/wi/poweroff.png'
LOG="$HOME/Development/remarkable_weather/weather_update.log"

timestamp() { date '+%F %T'; }

# 1) Build the image
cd "$WORKDIR"
"$PYTHON" gen_forecast_image.py

# 2) Copy it to the tablet
if scp -q $IMAGE_PATH $RM1_USER@$RM1_CONFIG_NAME:$REMOTE_IMAGE_PATH; then
	ssh -o BatchMode=yes $RM1_USER@$RM1_CONFIG_NAME 'cd /home/root/wi && ./set_next_wakeup.sh'
	echo "$(timestamp) – power-off image UPDATED successfully" >> "$LOG"
else
	echo "$(timestamp) - ERROR: could not copy image (tablet unreachable)" >> "$LOG"
	exit 1
fi
