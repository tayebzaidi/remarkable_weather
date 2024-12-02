#!/bin/bash

# Configuration
USB_HUB_PORT=2           # Replace with your USB hub port number
USB_DEVICE='1-1'         # Replace with your USB device ID from 'lsusb'
RM1_CONFIG_NAME='remarkable'
RM1_IP='10.11.99.1'   # Replace with the IP address of your RM1 device
RM1_USER='root'          # Replace with the username for RM1 (default is 'root')
IMAGE_PATH='weather_forecast.png'
REMOTE_IMAGE_PATH='/usr/share/remarkable/poweroff.png'

# Enable power to USB hub port
uhubctl -l $USB_DEVICE -a 0
sleep 20


uhubctl -l $USB_DEVICE -a 1
sleep 20  # Wait for the device to boot up

# Generate image before transfer
python3 gen_image_detailed_2.py
sleep 10

# Transfer the image to RM1 device
scp $IMAGE_PATH $RM1_CONFIG_NAME:$REMOTE_IMAGE_PATH

# Power off the RM1 device
#ssh $RM1_USER@$RM1_IP 'reboot -p'

# Wait for the device to shut down
sleep 330
