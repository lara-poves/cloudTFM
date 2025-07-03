import asyncio
import sys
import signal
import threading
import random
import json
import os  
import cv2  
import numpy as np  

from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message

PLANT_ID = 1
DEVICE_TYPE = "leaves"

SLEEP_TIME = 5 * 60 # Each 5 minutes
SLEEP_TIME_ERROR = 5

stop_event = threading.Event()

def create_client():
    return IoTHubModuleClient.create_from_edge_environment()

def segment_leaf(image_rgb):
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    lower_bound = np.array([20, 30, 30])     
    upper_bound = np.array([90, 255, 255])    
    return cv2.inRange(hsv, lower_bound, upper_bound)

def extract_leaf_pixels(image_rgb, mask):
    return image_rgb[mask > 0]

def get_domain_color(pixels):
    if pixels.size == 0:
        return np.array([0, 0, 0])  # Fully black image
    mean_color = np.mean(pixels, axis=0)
    return np.round(mean_color).astype(int)

def get_infection_percentage(pixels, healthy_color, threshold=75):
    color_diff = np.linalg.norm(pixels - healthy_color, axis=1)
    infected = color_diff > threshold
    return infected.sum() / len(pixels) * 100

async def send_sensor_data(client):
    image_dir = "img"
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    while not stop_event.is_set():
        await asyncio.sleep(SLEEP_TIME)

        # Select a random image
        image_name = random.choice(image_files)
        image_path = os.path.join(image_dir, image_name)
        image_rgb = cv2.imread(image_path)

        # Segment and erode
        mask = segment_leaf(image_rgb)
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=7)
        leaf_pixels = extract_leaf_pixels(image_rgb, mask)

        # Analyze infection
        domain_color = get_domain_color(leaf_pixels)
        infection_percentage = get_infection_percentage(leaf_pixels, domain_color)

        # Create message
        data = {
            "domain_r": int(domain_color[0]),
            "domain_g": int(domain_color[1]),
            "domain_b": int(domain_color[2]),
            "infected_percentage": round(infection_percentage, 2),
            "plantId": PLANT_ID,
            "deviceType": DEVICE_TYPE
        }

        message = Message(json.dumps(data))
        message.content_encoding = "utf-8"
        message.content_type = "application/json"

        try:
            print(f"Sending camera data {data}", flush=True)
            await client.send_message_to_output(message, "output1")
        except Exception as e:
            print(f"Error sending message: {e}", flush=True)
            sleep_time = SLEEP_TIME_ERROR

        await asyncio.sleep(sleep_time)  # Each 5 minutes

async def run_module(client):
    await send_sensor_data(client)

def main():
    if not sys.version >= "3.5.3":
        raise Exception(f"This module requires Python 3.5.3+. Current version: {sys.version}")
    print("Simulated Sensor Module: pH, Soil Moisture, Temperature, NPK")

    client = create_client()

    def termination_handler(signal, frame):
        print("Module terminated by Edge runtime.")
        stop_event.set()

    signal.signal(signal.SIGTERM, termination_handler)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_module(client))
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
    finally:
        print("Shutting down IoT Hub client...")
        loop.run_until_complete(client.shutdown())
        loop.close()

if __name__ == "__main__":
    main()
