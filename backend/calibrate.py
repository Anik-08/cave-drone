import serial
import json
import time
import statistics

PORT = "COM7"
BAUD_RATE = 9600

CALIBRATION_TIME = 300  # 5 minutes

arduino = serial.Serial(PORT, BAUD_RATE, timeout=1)

print("Connected to Arduino")
print("Starting baseline calibration...")
print()
print("Keep the sensors in your NORMAL environment.")
print("Do not expose them to smoke or gas during calibration.")
print()

time.sleep(2)

mq2_values = []
mq4_values = []
mq7_values = []

start_time = time.time()

while time.time() - start_time < CALIBRATION_TIME:

    line = arduino.readline().decode("utf-8").strip()

    if not line:
        continue

    try:
        data = json.loads(line)

        mq2 = data["mq2"]
        mq4 = data["mq4"]
        mq7 = data["mq7"]

        mq2_values.append(mq2)
        mq4_values.append(mq4)
        mq7_values.append(mq7)

        elapsed = int(time.time() - start_time)
        remaining = CALIBRATION_TIME - elapsed

        print(
            f"MQ2: {mq2:4} | "
            f"MQ4: {mq4:4} | "
            f"MQ7: {mq7:4} | "
            f"Remaining: {remaining}s"
        )

    except (json.JSONDecodeError, KeyError):
        continue


arduino.close()


if not mq2_values:
    print("No sensor data received.")
    exit()


mq2_baseline = statistics.mean(mq2_values)
mq4_baseline = statistics.mean(mq4_values)
mq7_baseline = statistics.mean(mq7_values)


baseline = {
    "mq2": round(mq2_baseline, 2),
    "mq4": round(mq4_baseline, 2),
    "mq7": round(mq7_baseline, 2)
}


with open("baseline.json", "w") as file:
    json.dump(baseline, file, indent=4)


print()
print("==============================")
print("CALIBRATION COMPLETE")
print("==============================")

print(f"MQ-2 baseline: {mq2_baseline:.2f}")
print(f"MQ-4 baseline: {mq4_baseline:.2f}")
print(f"MQ-7 baseline: {mq7_baseline:.2f}")

print()
print("Saved to baseline.json")