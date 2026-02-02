import serial
import csv
import time 
import signal 
import sys 

COM_PORT = 'COM11'
BAUD_RATE = 115200
CSV_FILE = "reading.csv"

def write_serial_to_csv():
    # must alwasya have a finally or except to use try
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=10)
        ser.flushInput() # clearing inputing buffer in case of prior data
        print(f"Connected to {COM_PORT}. Logging data to {CSV_FILE}...")
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if ser.in_waiting > 0:
                ser_byte = ser.readline().decode('utf-8').rstrip()
                line = ser.readline().decode('utf-8').rstrip()
                data = line.split(',')
                writer.writerow(data)
                print(f"Logged data: {data}")
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                row = [timestamp, ser_byte]
                writer.writerow(row)
                f.flush() # Ensure data is written to disk immediately

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    finally:
        if ser and ser.open:
            ser.close()
            print("Serial port closed.")
if __name__ == "__main__":
    write_serial_to_csv()
