import asyncio
import sys
import signal
import threading
import json
import Adafruit_DHT
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message

stop_event = threading.Event()

# Sensor DHT11
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4  

def create_client():
    return IoTHubModuleClient.create_from_edge_environment()

async def send_sensor_data(client):
    while not stop_event.is_set():
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

        if humidity is not None and temperature is not None:
            data = {
                "temperature": round(temperature, 2),
                "humidity": round(humidity, 2)
            }

            message = Message(json.dumps(data))
            message.content_encoding = "utf-8"
            message.content_type = "application/json"

            print(f"Sending real sensor data: {data}")

            try:
                await client.send_message_to_output(message, "output1")
            except Exception as e:
                print(f"Error sending message: {e}")
        else:
            print("Error: could not read from DHT11 sensor.")

        await asyncio.sleep(120)  # Each 2 minutes

async def run_module(client):
    await send_sensor_data(client)

def main():
    if not sys.version >= "3.5.3":
        raise Exception(f"This module requires Python 3.5.3+. Current version: {sys.version}")
    print("DHT11 Sensor Module: Temperature and Humidity")

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
