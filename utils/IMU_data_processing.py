import os, time, struct
import matplotlib.pyplot as plt
import numpy as np
import csv
from pathlib import Path
from datetime import datetime

SCALE_LSB_PER_G = 16384.0 # from the internet
G_TO_MS2 = 9.80665 
t_list, ax_list, ay_list, az_list = [], [], [], []
t0 = time.perf_counter()
duration_s = 30.0  # one duration for both
base_dir = Path("results")
base_dir.mkdir(exist_ok=True)
date = datetime.now()
formatted_date = date.strftime("%Y-%m-%d_%H_%M_%S")
trial_dir = base_dir / f"{formatted_date}"
trial_dir.mkdir()
print("Saving to", trial_dir)

# ---------- read accel for ~60 seconds ----------
t_list, ax_list, ay_list, az_list = [], [], [], []
t0 = time.perf_counter()
target_duration = 30.0

# Data collection loop 
    # while True:
    #     i = 0


    #     raw6 = reult.csv
    #     ax_counts, ay_counts, az_counts = struct.unpack(">hhh", raw6)
    #     ax_g = ax_counts / SCALE_LSB_PER_G
    #     ay_g = ay_counts / SCALE_LSB_PER_G
    #     az_g = az_counts / SCALE_LSB_PER_G
    #     ax = ax_g * G_TO_MS2
    #     ay = ay_g * G_TO_MS2
    #     az = az_g * G_TO_MS2

    #     now = time.perf_counter() - t0
    #     t_list.append(now)
    #     ax_list.append(ax)
    #     ay_list.append(ay)
    #     az_list.append(az)

    #     #print(f"{now:6.3f}s  ax={ax_g:+.3f}g  ay={ay_g:+.3f}g  az={az_g:+.3f}g")

    #     if now >= target_duration:
    #         break

# Data pre-processing and saving
# Convert to numpy arrays
t = np.asarray(t_list, dtype=float)
ax_arr = np.asarray(ax_list, dtype=float)
ay_arr = np.asarray(ay_list, dtype=float)
az_arr = np.asarray(az_list, dtype=float)
with open(trial_dir / "scaled_data.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["time_s", "ax_m_s2", "ay_m_s2", "az_m_s2"])
    for ti, x, y, z in zip(t, ax_arr, ay_arr, az_arr):
        w.writerow([ti, x, y, z])

print(f"Collected {len(t)} samples in {duration_s:.3f}s "
      f"→ ~{len(t)/duration_s:.1f} Hz")

# Data processing and plotting 
# ---- Plot motion in x, y, z ----
accel_fig = plt.figure()
plt.plot(t, ax_arr, label="ax (m/s²)")
plt.plot(t, ay_arr, label="ay (m/s²)")
plt.plot(t, az_arr, label="az (m/s²)")
plt.xlabel("Time (s)")
plt.ylabel("Acceleration (m/s²)")
plt.legend()
plt.grid(True)
plt.tight_layout()
accel_fig.savefig(trial_dir / "time_domain.png", dpi=150)


t = np.asarray(t_list, dtype=float)
ax_arr = np.asarray(ax_list, dtype=float)
print(f"average acceleration in the x-direction {np.mean(np.asarray(ax_list, dtype=float))}")
ay_arr = np.asarray(ay_list, dtype=float)
print(f"average acceleration in the y-direction {np.mean(np.asarray(ay_list, dtype=float))}")

az_arr = np.asarray(az_list, dtype=float)
print(f"average acceleration in the z-direction {np.mean(np.asarray(az_list, dtype=float))}")

duration_s = t[-1] - t[0]
print(f"Collected {len(t)} samples in {duration_s:.3f}s "
      f"→ ~{len(t)/duration_s:.1f} Hz")
# --- Frequency-domain (FFT) of IMU motion ---
if len(t) > 1:
    dt = np.mean(np.diff(t))          # sampling period
    freqs = np.fft.rfftfreq(len(t), d=dt)

    Ax_fft = np.fft.rfft(ax_arr - ax_arr.mean())
    Ay_fft = np.fft.rfft(ay_arr - ay_arr.mean())
    Az_fft = np.fft.rfft(az_arr - az_arr.mean())
    
    # Optional: dominant frequency of the vibrator (pick one axis)
    dom_idx = np.argmax(np.abs(Ax_fft))
    dom_freq_x = freqs[dom_idx]
    print(f"Dominant X-axis frequency ≈ {dom_freq_x:.2f} Hz")
    dom_idy = np.argmax(np.abs(Ay_fft))
    dom_freq_y = freqs[dom_idy]
    print(f"Dominant Y-axis frequency ≈ {dom_freq_y:.2f} Hz")
    dom_idz = np.argmax(np.abs(Az_fft))
    dom_freq_z= freqs[dom_idz]
    print(f"Dominant Z-axis frequency: {dom_freq_z:.2f} Hz")
    Ax_mag = np.abs(Ax_fft)
    Ay_mag = np.abs(Ay_fft)
    Az_mag = np.abs(Az_fft)
    # with open(trial_dir / "accel_freq.csv", "w", newline="") as f:
    #     w = csv.writer(f)
    #     w.writerow(["freq_Hz", "Ax_mag", "Ay_mag", "Az_mag"])
    #     for fhz, X, Y, Z in zip(freqs, Ax_mag, Ay_mag, Az_mag):
    #         w.writerow([fhz, X, Y, Z])

    freq_fig = plt.figure()
    plt.plot(freqs, np.abs(Ax_fft), label="X")
    plt.plot(freqs, np.abs(Ay_fft), label="Y")
    plt.plot(freqs, np.abs(Az_fft), label="Z")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.title("IMU vibration spectrum")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    freq_fig.savefig(trial_dir / "freqency_domain.png", dpi=150)

#plt.show()
print(f"Got {len(t_list)} samples")
with open(trial_dir / "result_summary.txt", "w") as f:
    f.write(f"Samples: {len(t)}\n")
    f.write(f"Duration: {duration_s:.3f} s\n")
    f.write(f"Sample rate:{len(t)/duration_s:.1f} Hz\n")
    f.write(f"Dominant X-axis frequency: {dom_freq_x:.2f} Hz\n")
    f.write(f"Dominant Y-axis frequency: {dom_freq_y:.2f} Hz\n")
    f.write(f"Dominant Z-axis frequency: {dom_freq_z:.2f} Hz\n")
    f.write(f"average acceleration in the x-direction {np.mean(np.asarray(ax_list, dtype=float))}\n")
    f.write(f"average acceleration in the y-direction {np.mean(np.asarray(ay_list, dtype=float))}\n")
    f.write(f"average acceleration in the z-direction {np.mean(np.asarray(az_list, dtype=float))}\n")

