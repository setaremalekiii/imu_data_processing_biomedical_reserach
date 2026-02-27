import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

INPUT_CSV = "collected_data/reading_2026-02-26_16-43-21.csv"   # from the collector please change this path to analyze a different file if needed
SCALE_LSB_PER_G = 16384.0     # adjust if your IMU full-scale is not ±2g
G_TO_MS2 = 9.80665

# indicate the output path
base_dir = Path("results")
base_dir.mkdir(exist_ok=True)
trial_dir = base_dir / datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
trial_dir.mkdir()
print("Saving to", trial_dir)

# raw csv
t_list, x_list, y_list, z_list = [], [], [], []

with open(INPUT_CSV, "r", newline="") as f:
    r = csv.reader(f)
    header = next(r, None)  # ["t_s","x_counts","y_counts","z_counts"]

    for row in r:
        if len(row) < 5:
            continue
        try:
            t_s = float(row[1])
            x = int(row[2])
            y = int(row[3])
            z = int(row[4])
        except ValueError:
            continue

        t_list.append(t_s)
        x_list.append(x)
        y_list.append(y)
        z_list.append(z)

t = np.asarray(t_list, dtype=float)
x_counts = np.asarray(x_list, dtype=float)
y_counts = np.asarray(y_list, dtype=float)
z_counts = np.asarray(z_list, dtype=float)

if len(t) < 2:
    raise RuntimeError("Not enough samples in raw_accel.csv to process.")

# get sampling rate estimate
dt = np.diff(t)
dt = dt[dt > 0]  # remove any zeros / weirdness
fs = 1.0 / np.mean(dt)
duration_s = t[-1] - t[0]
print(f"Samples: {len(t)}")
print(f"Duration: {duration_s:.3f} s")
print(f"Estimated sample rate: {fs:.2f} Hz")

# g -> m/s^2
ax = (x_counts / SCALE_LSB_PER_G) * G_TO_MS2
ay = (y_counts / SCALE_LSB_PER_G) * G_TO_MS2
az = (z_counts / SCALE_LSB_PER_G) * G_TO_MS2

print(f"Mean ax (m/s²): {ax.mean():.4f}")
print(f"Mean ay (m/s²): {ay.mean():.4f}")
print(f"Mean az (m/s²): {az.mean():.4f}")

# save scaled data
scaled_path = trial_dir / "scaled_data.csv"
with open(scaled_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t_s", "ax_m_s2", "ay_m_s2", "az_m_s2"])
    for ti, x, y, z in zip(t, ax, ay, az):
        w.writerow([ti, x, y, z])
print("Wrote", scaled_path)

# time-domain plot
plt.figure()
plt.plot(t, ax, label="ax (m/s²)")
plt.plot(t, ay, label="ay (m/s²)")
plt.plot(t, az, label="az (m/s²)")
plt.xlabel("Time (s)")
plt.ylabel("Acceleration (m/s²)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(trial_dir / "time_domain.png", dpi=150)

# FFT (per axis)
# Detrend by removing mean (DC)
ax0 = ax - ax.mean()
ay0 = ay - ay.mean()
az0 = az - az.mean()

freqs = np.fft.rfftfreq(len(t), d=1.0/fs)
Ax_fft = np.fft.rfft(ax0)
Ay_fft = np.fft.rfft(ay0)
Az_fft = np.fft.rfft(az0)

Ax_mag = np.abs(Ax_fft)
Ay_mag = np.abs(Ay_fft)
Az_mag = np.abs(Az_fft)

# ignore DC bin for "dominant freq"
dom_x = freqs[1 + np.argmax(Ax_mag[1:])]
dom_y = freqs[1 + np.argmax(Ay_mag[1:])]
dom_z = freqs[1 + np.argmax(Az_mag[1:])]

print(f"Dominant freq X: {dom_x:.2f} Hz")
print(f"Dominant freq Y: {dom_y:.2f} Hz")
print(f"Dominant freq Z: {dom_z:.2f} Hz")

plt.figure()
plt.plot(freqs, Ax_mag, label="X")
plt.plot(freqs, Ay_mag, label="Y")
plt.plot(freqs, Az_mag, label="Z")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.title("IMU vibration spectrum")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(trial_dir / "frequency_domain.png", dpi=150)

# summary txt file
summary_path = trial_dir / "result_summary.txt"
with open(summary_path, "w") as f:
    f.write(f"Input: {INPUT_CSV}\n")
    f.write(f"Samples: {len(t)}\n")
    f.write(f"Duration: {duration_s:.6f} s\n")
    f.write(f"Estimated sample rate: {fs:.3f} Hz\n")
    f.write(f"Mean ax (m/s^2): {ax.mean():.6f}\n")
    f.write(f"Mean ay (m/s^2): {ay.mean():.6f}\n")
    f.write(f"Mean az (m/s^2): {az.mean():.6f}\n")
    f.write(f"Dominant freq X (Hz): {dom_x:.3f}\n")
    f.write(f"Dominant freq Y (Hz): {dom_y:.3f}\n")
    f.write(f"Dominant freq Z (Hz): {dom_z:.3f}\n")

print("Wrote", summary_path)
print("Done.")