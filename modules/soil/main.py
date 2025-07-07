import asyncio
import sys
import signal
import threading
import random
import json
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message

PLANT_ID = 1
DEVICE_TYPE = "soil"

SLEEP_TIME = 120 # Each 2 minutes
SLEEP_TIME_ERROR = 5

stop_event = threading.Event()

def create_client():
    return IoTHubModuleClient.create_from_edge_environment()

# Controll incremental change
def update_value(value, min_val, max_val, delta=0.1):
    change = random.uniform(-delta, delta)
    new_value = round(value + change, 2)
    return max(min_val, min(max_val, new_value))

async def send_sensor_data(client):
    # Initial values
    ph = 6.5
    soil_moisture = 50.0 # %
    soil_temperature = 25.0 # ºC
    nitrogen = 1800.0 # mg /kg
    phosphorus = 19.0 # mg / kg
    potassium = 300.0 # mg / kg

    while not stop_event.is_set():
        sleep_time = SLEEP_TIME

        # Update values
        ph = update_value(ph, 4.0, 9.0)
        soil_moisture = update_value(soil_moisture, 0.0, 100.0)
        soil_temperature = update_value(soil_temperature, 9.0, 25.0)
        nitrogen = update_value(nitrogen, 1000.0, 15000.5)
        phosphorus = update_value(phosphorus, 10, 121.0)
        potassium = update_value(potassium, 90.0, 1322.0)

        data = {
            "ph": ph,
            "soil_moisture": soil_moisture,
            "soil_temperature": soil_temperature,
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
            "plantId": PLANT_ID,
            "deviceType": DEVICE_TYPE,
            "latitude": 40.4168,
            "longitude": -3.7038
        }

        message = Message(json.dumps(data))
        message.content_encoding = "utf-8"
        message.content_type = "application/json"

        try:
            print(f"Sending data: {data}", flush=True)
            await client.send_message_to_output(message, "output1")
        except Exception as e:
            print(f"Error sending message: {e}", flush=True)
            sleep_time = SLEEP_TIME_ERROR

        await asyncio.sleep(sleep_time) 

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
