import asyncio
import sys
import signal
import threading
import json
import RPi.GPIO as GPIO
import dht11
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message

SLEEP_TIME = 60 * 3 # Each 3 minutes
SLEEP_TIME_ERROR = 5

stop_event = threading.Event()

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# DHT11 sensor in GPIO4
sensor = dht11.DHT11(pin=4)

def create_client():
    return IoTHubModuleClient.create_from_edge_environment()

async def send_sensor_data(client):
    while not stop_event.is_set():
        sleep_time = SLEEP_TIME
        result = sensor.read()

        if result.is_valid():
            data = {
                "temperature": result.temperature,
                "humidity": result.humidity
            }

            message = Message(json.dumps(data))
            message.content_encoding = "utf-8"
            message.content_type = "application/json"

            print(f"Sending sensor data: {data}")

            try:
                await client.send_message_to_output(message, "output1")
            except Exception as e:
                print(f"Error sending message: {e}")
                sleep_time = SLEEP_TIME_ERROR
        else:
            print("Error: could not read from DHT11 sensor")
            sleep_time = SLEEP_TIME_ERROR

        await asyncio.sleep(sleep_time) 

async def run_module(client):
    await send_sensor_data(client)

def main():
    if not sys.version >= "3.5.3":
        raise Exception(f"This module requires Python 3.5.3+. Current version: {sys.version}")
    print("DHT11 Sensor Module inside Docker")

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
