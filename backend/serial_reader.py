import serial

arduino = serial.Serial(
    "COM7",
    9600,
    timeout=1
)

print("Connected to Arduino")

while True:
    line = arduino.readline()

    if line:
        print(repr(line))