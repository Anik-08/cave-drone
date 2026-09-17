import serial
import json
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

arduino = serial.Serial(
    port="COM7",
    baudrate=9600,
    timeout=1
)

# Give Arduino time to reset after opening COM port
print("Opening Arduino...")
asyncio.sleep(0)

def read_sensor_data():

    while True:

        line = arduino.readline()

        if not line:
            continue

        try:
            text = line.decode("utf-8", errors="ignore").strip()

            print("RAW:", repr(text))

            # Find JSON inside the received line
            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1:
                continue

            json_text = text[start:end + 1]

            data = json.loads(json_text)

            # Make sure required values exist
            if "mq2" not in data:
                continue

            if "mq4" not in data:
                continue

            if "mq7" not in data:
                continue

            return {
                "mq2": data["mq2"],
                "mq4": data["mq4"],
                "mq7": data["mq7"]
            }

        except (json.JSONDecodeError, UnicodeDecodeError):
            print("Ignored corrupted data")
            continue


@app.get("/")
def home():
    return {
        "message": "Drone sensor backend is running"
    }


@app.websocket("/ws/sensors")
async def sensor_websocket(websocket: WebSocket):

    await websocket.accept()

    print("WebSocket client connected")

    try:

        while True:

            data = await asyncio.to_thread(read_sensor_data)

            print("SENDING:", data)

            await websocket.send_json(data)

    except WebSocketDisconnect:

        print("WebSocket client disconnected")

    except Exception as e:

        print("WebSocket error:", e)