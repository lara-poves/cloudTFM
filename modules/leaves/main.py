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

SLEEP_TIME = 5 * 60 # Each 5 minutes
SLEEP_TIME_ERROR = 5

stop_event = threading.Event()

def create_client():
    return IoTHubModuleClient.create_from_edge_environment()

def segment_leaf(img_rgb):
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    lower_leaf = np.array([20, 30, 30])     
    upper_leaf = np.array([90, 255, 255])    

    mask = cv2.inRange(hsv, lower_leaf, upper_leaf)
    return mask

def get_domain_color(masked_img):
    pixels = masked_img.reshape(-1, 3)
    pixels = pixels[np.any(pixels > 0, axis=1)]

    if pixels.size == 0:
        return np.array([0, 0, 0]) # All img black

    avg_color = np.mean(pixels, axis=0)
    return np.round(avg_color).astype(int)

def calcular_porcentaje_infeccion(masked_img, domain_color, threshold=75):
    pixels = masked_img.reshape(-1, 3)
    leaf  = np.any(pixels > 0, axis=1) 
    diff   = np.linalg.norm(pixels - domain_color, axis=1)
    infected = (diff > threshold) & leaf

    return infected.sum() / leaf.sum() * 100

async def send_sensor_data(client):
    # Read images
    dir_imgs = "img"
    imgs = [f for f in os.listdir(dir_imgs) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    while not stop_event.is_set():
        sleep_time = SLEEP_TIME
        
        # Choose a random image
        img_name = random.choice(imgs)
        img_path = os.path.join(dir_imgs, img_name)
        leaf_rgb = cv2.imread(img_path)
        leaf_rgb = cv2.cvtColor(leaf_rgb, cv2.COLOR_BGR2RGB)

        # Segmented and edored the image
        mask = segment_leaf(leaf_rgb)
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=7)
        leaf_only = cv2.bitwise_and(leaf_rgb, leaf_rgb, mask=mask)

        # Get parameters
        domain_color = get_domain_color(leaf_only)
        inf_pct = calcular_porcentaje_infeccion(leaf_only, domain_color)

        # Create message
        data = {
            "domain_color": domain_color.tolist(),
            "infected_percentage": inf_pct
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