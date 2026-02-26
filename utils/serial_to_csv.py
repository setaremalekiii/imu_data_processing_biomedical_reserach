import serial, csv, time

COM_PORT="COM11"
BAUD_RATE=115200
OUT_CSV="reading.csv"
DURATION_S=30.0

with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser, open(OUT_CSV, "w", newline="") as f:
    ser.reset_input_buffer()
    w = csv.writer(f)
    w.writerow(["timestamp", "t_s", "x", "y", "z"])

    t0 = time.perf_counter()
    try:
        while (time.perf_counter() - t0) < DURATION_S:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            parts = line.split(",")
            if len(parts) != 3:
                continue

            try:
                x = int(parts[0]); y = int(parts[1]); z = int(parts[2])
            except ValueError:
                continue

            now = time.perf_counter() - t0
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([ts, f"{now:.6f}", x, y, z])
    except KeyboardInterrupt:
        pass