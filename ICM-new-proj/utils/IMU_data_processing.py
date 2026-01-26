import os, time, struct
import matplotlib.pyplot as plt
import numpy as np
import csv
from pathlib import Path
from datetime import datetime
import board, busio, digitalio
import adafruit_blinka.microcontroller.ftdi_mpsse.mpsse as mpsse
import adafruit_icm20948


# Setting up the file and board environments
os.environ["BLINKA_FT232H"] = "1"   # IMPORTANT: must be set before importing board
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

# Setting up SPI + CS communication
pins = [("SCLK", board.SCLK), ("MOSI", board.MOSI), ("MISO", board.MISO)]
spi = busio.SPI(board.SCLK, MOSI=board.MOSI, MISO=board.MISO)
#CS_PIN_NAME = os.getenv("IMU_CS_PIN", "C3")
cs = digitalio.DigitalInOut(board.C3)

#cs = digitalio.DigitalInOut(getattr(board, CS_PIN_NAME))
cs.direction = digitalio.Direction.OUTPUT
cs.value = True
# Lock and configure SPI
while not spi.try_lock():
    pass
spi.configure(
    baudrate=int(os.getenv("SPI_BAUD", "7_000_000 ")),  # highest setting 7MHz
    polarity=0,
    phase=0,
)

# The library does not support SPI communication it only has I2C support in python which is why there is 
# low level SPI read/write helper functions here
def write_reg(bank: int, addr: int, val: int):
    """Write single byte to (bank, addr)."""
    # select register bank
    cs.value = False
    spi.write(bytes([0x7F & 0x7F, (bank & 0x3) << 4]))  # 0x7F write, USER_BANK[1:0] in bits[5:4]
    cs.value = True
    time.sleep(0.0003)

    # write register (MSB=0)
    cs.value = False
    spi.write(bytes([addr & 0x7F, val & 0xFF]))
    cs.value = True
    time.sleep(0.0003)


def read_regs(bank: int, addr: int, n: int) -> bytes:
    """Read n bytes starting at (bank, addr)."""
    # select register bank
    cs.value = False
    spi.write(bytes([0x7F & 0x7F, (bank & 0x3) << 4]))
    cs.value = True
    time.sleep(0.0003)

    # read: MSB=1
    cs.value = False
    tx = bytearray([addr | 0x80]) + bytearray(n)
    rx = bytearray(len(tx))
    spi.write_readinto(tx, rx)
    cs.value = True
    return bytes(rx[1:])  # drop command byte


def wait_drdy(timeout_s: float = 0.2) -> bool:
    """Wait for accel/gyro data ready (INT_STATUS_1 bit0)."""
    t0 = time.perf_counter()
    while True:
        status = read_regs(0, 0x1A, 1)[0]  # INT_STATUS_1, bank 0
        if status & 0x01:
            return True
        if time.perf_counter() - t0 >= timeout_s:
            return False
        time.sleep(0.0005)

# Initialize the IMU 
# ---------- basic init ----------
# Wake up, auto clock
write_reg(0, 0x06, 0x01)   # PWR_MGMT_1: CLKSEL=1, SLEEP=0
time.sleep(0.01)

# Disable I2C (I2C_IF_DIS bit) so SPI is solid
# write_reg(0, 0x03, 0x10)   # USER_CTRL
# time.sleep(0.005)

# WHO_AM_I check (0xEA)
# ---- Wake, WHO_AM_I ----
# Wake device: PWR_MGMT_1 (0x06) => CLKSEL=1, SLEEP=0
write_reg(0, 0x06, 0x01)      # clock = best, sleep = 0
time.sleep(0.05)

# Put serial interface in SPI-only mode (recommended)
# USER_CTRL (0x03), bit4 = I2C_IF_DIS
write_reg(0, 0x03, 0x10)

# Explicitly enable accel + gyro just in case
# PWR_MGMT_2 (0x07), DISABLE_ACCEL[2:0] = 000, DISABLE_GYRO[2:0] = 000
write_reg(0, 0x07, 0x00)

who = read_regs(0, 0x00, 1)[0]
print(f"WHO_AM_I = 0x{who:02X}")
if who != 0xEA:
    print("WARNING: unexpected WHO_AM_I (wiring / power / CS / SPI?)")

pm1 = read_regs(0, 0x06, 1)[0]
pm2 = read_regs(0, 0x07, 1)[0]
# print(f"PWR_MGMT_1=0x{pm1:02X}, PWR_MGMT_2=0x{pm2:02X}")

# Bank 2: accel config
# ACCEL_CONFIG_1 (0x14, bank 2) – DLPF etc.; here: enable DLPF, ±2g (default, 16384 LSB/g)
write_reg(2, 0x14, 0x11)

# Set accel ODR via divisor in ACCEL_SMPLRT_DIV (0x10 high, 0x11 low, bank2)
ACCEL_DIV = int(os.getenv("ACCEL_DIV", "0"))
ACCEL_DIV = max(0, min(0x0FFF, ACCEL_DIV))
write_reg(2, 0x10, (ACCEL_DIV >> 8) & 0x0F)
write_reg(2, 0x11, ACCEL_DIV & 0xFF)
configured_odr = 1125.0 / (1.0 + ACCEL_DIV)
print(f"Accel ODR ≈ {configured_odr:.1f} Hz (div={ACCEL_DIV})")

# Back to bank 0: enable accel/gyro, enable data ready interrupt
write_reg(0, 0x05, 0x00)  # LP_CONFIG: disable cycle modes
write_reg(0, 0x07, 0x00)  # PWR_MGMT_2: enable accel + gyro
write_reg(0, 0x10, 0x00)  # INT_ENABLE_0: none
write_reg(0, 0x11, 0x01)  # INT_ENABLE_1: RAW_DATA_0_RDY_EN
_ = read_regs(0, 0x1A, 1) # clear latched status

ACCEL_XOUT_H = 0x2D  # bank 0
SCALE_LSB_PER_G = 16384.0

# ---------- read accel for ~60 seconds ----------
t_list, ax_list, ay_list, az_list = [], [], [], []
t0 = time.perf_counter()
target_duration = 30.0

# Data collection loop
try:
    while True:
        i = 0

        wait_drdy(0.2)  # if it times out we just read anyway

        raw6 = read_regs(0, ACCEL_XOUT_H, 6)
        ax_counts, ay_counts, az_counts = struct.unpack(">hhh", raw6)
        ax_g = ax_counts / SCALE_LSB_PER_G
        ay_g = ay_counts / SCALE_LSB_PER_G
        az_g = az_counts / SCALE_LSB_PER_G
        ax = ax_g * G_TO_MS2
        ay = ay_g * G_TO_MS2
        az = az_g * G_TO_MS2

        now = time.perf_counter() - t0
        t_list.append(now)
        ax_list.append(ax)
        ay_list.append(ay)
        az_list.append(az)

        #print(f"{now:6.3f}s  ax={ax_g:+.3f}g  ay={ay_g:+.3f}g  az={az_g:+.3f}g")

        if now >= target_duration:
            break

finally:
    spi.unlock()

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

