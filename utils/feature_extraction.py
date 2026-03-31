import csv
import numpy as np
from pathlib import Path
from datetime import datetime
from scipy.signal import welch
from scipy.stats import kurtosis, skew

# ─────────────────────────────────────────────
# CONFIG — edit these before running
# ─────────────────────────────────────────────
INPUT_CSV   = "E:/IMU_only/readings/frac/reading_2026-03-20_13-58-01_nofrac_3.csv"
STAGE_LABEL = 2          # <-- set to 1–5 depending on which stage this recording belongs to
SCALE_LSB_PER_G = 16384.0
G_TO_MS2    = 9.80665

# Output — all recordings append to one master CSV
OUTPUT_CSV  = Path("E:/IMU_only/results/standardized/frac/2026-03-23_14_46_14_frac_3/features_all_recordings.csv")

# Frequency bands (Hz) — adjust to your domain knowledge
BAND_LOW    = (0,   10)
BAND_MID    = (10,  50)
BAND_HIGH   = (50, 200)
# ─────────────────────────────────────────────


def compute_features(sig, fs, axis_name):
    """
    Compute time-domain and frequency-domain features for one axis signal.
    sig  : 1-D numpy array, already in physical units (m/s²), DC removed
    fs   : sampling rate (Hz)
    Returns a dict of {feature_name: value}
    """
    feats = {}
    n = len(sig)

    # ── Time domain ──────────────────────────────────────────────────────
    feats[f"{axis_name}_rms"]         = float(np.sqrt(np.mean(sig**2)))
    feats[f"{axis_name}_peak"]        = float(np.max(np.abs(sig)))
    feats[f"{axis_name}_peak_to_peak"]= float(np.ptp(sig))
    feats[f"{axis_name}_std"]         = float(np.std(sig))
    feats[f"{axis_name}_variance"]    = float(np.var(sig))
    feats[f"{axis_name}_kurtosis"]    = float(kurtosis(sig))          # excess kurtosis (normal=0)
    feats[f"{axis_name}_skewness"]    = float(skew(sig))
    rms_val = feats[f"{axis_name}_rms"]
    feats[f"{axis_name}_crest_factor"]= float(feats[f"{axis_name}_peak"] / rms_val) if rms_val > 0 else 0.0
    feats[f"{axis_name}_shape_factor"]= float(rms_val / (np.mean(np.abs(sig)) + 1e-12))

    # ── Frequency domain (Welch PSD) ─────────────────────────────────────
    nperseg = min(1024, n)
    freqs, psd = welch(sig, fs=fs, nperseg=nperseg)

    # ignore DC bin
    freqs_no_dc = freqs[1:]
    psd_no_dc   = psd[1:]

    total_power = float(np.trapz(psd_no_dc, freqs_no_dc))
    feats[f"{axis_name}_total_power"] = total_power

    # dominant frequency
    dom_idx = np.argmax(psd_no_dc)
    feats[f"{axis_name}_dominant_freq_hz"] = float(freqs_no_dc[dom_idx])
    feats[f"{axis_name}_dominant_freq_power"] = float(psd_no_dc[dom_idx])

    # spectral centroid — "centre of mass" of the spectrum
    feats[f"{axis_name}_spectral_centroid_hz"] = float(
        np.sum(freqs_no_dc * psd_no_dc) / (np.sum(psd_no_dc) + 1e-12)
    )

    # spectral spread — how wide the energy distribution is
    centroid = feats[f"{axis_name}_spectral_centroid_hz"]
    feats[f"{axis_name}_spectral_spread"] = float(
        np.sqrt(np.sum(((freqs_no_dc - centroid)**2) * psd_no_dc) / (np.sum(psd_no_dc) + 1e-12))
    )

    # band power — energy in each frequency band
    def band_power(f_low, f_high):
        mask = (freqs >= f_low) & (freqs < f_high)
        if mask.sum() < 2:
            return 0.0
        return float(np.trapz(psd[mask], freqs[mask]))

    feats[f"{axis_name}_band_power_low_{BAND_LOW[0]}_{BAND_LOW[1]}hz"]   = band_power(*BAND_LOW)
    feats[f"{axis_name}_band_power_mid_{BAND_MID[0]}_{BAND_MID[1]}hz"]   = band_power(*BAND_MID)
    feats[f"{axis_name}_band_power_high_{BAND_HIGH[0]}_{BAND_HIGH[1]}hz"]= band_power(*BAND_HIGH)

    # spectral entropy — how spread out / chaotic the spectrum is
    psd_norm = psd_no_dc / (np.sum(psd_no_dc) + 1e-12)
    feats[f"{axis_name}_spectral_entropy"] = float(
        -np.sum(psd_norm * np.log2(psd_norm + 1e-12))
    )

    return feats


def main():
    # ── Load raw CSV ────────────────────────────────────────────────────
    t_list, x_list, y_list, z_list = [], [], [], []
    with open(INPUT_CSV, "r", newline="") as f:
        r = csv.reader(f)
        next(r, None)  # skip header
        for row in r:
            if len(row) < 5:
                continue
            try:
                t_s = float(row[1])
                x   = int(row[2])
                y   = int(row[3])
                z   = int(row[4])
            except ValueError:
                continue
            t_list.append(t_s)
            x_list.append(x)
            y_list.append(y)
            z_list.append(z)

    t        = np.asarray(t_list, dtype=float)
    x_counts = np.asarray(x_list, dtype=float)
    y_counts = np.asarray(y_list, dtype=float)
    z_counts = np.asarray(z_list, dtype=float)

    if len(t) < 2:
        raise RuntimeError("Not enough samples in the CSV.")

    # ── Sampling rate ───────────────────────────────────────────────────
    dt = np.diff(t)
    dt = dt[dt > 0]
    fs = 1.0 / np.mean(dt)
    duration_s = t[-1] - t[0]
    print(f"Samples: {len(t)}  |  Duration: {duration_s:.2f}s  |  Fs: {fs:.2f} Hz")

    # ── Convert counts → m/s², remove DC ───────────────────────────────
    ax = (x_counts / SCALE_LSB_PER_G) * G_TO_MS2;  ax -= ax.mean()
    ay = (y_counts / SCALE_LSB_PER_G) * G_TO_MS2;  ay -= ay.mean()
    az = (z_counts / SCALE_LSB_PER_G) * G_TO_MS2;  az -= az.mean()

    # ── Compute magnitude signal (resultant) ────────────────────────────
    mag = np.sqrt(ax**2 + ay**2 + az**2)

    # ── Extract features ────────────────────────────────────────────────
    record = {
        "recording_file": Path(INPUT_CSV).name,
        "stage":          STAGE_LABEL,
        "duration_s":     round(duration_s, 4),
        "fs_hz":          round(fs, 4),
        "n_samples":      len(t),
    }
    record.update(compute_features(ax,  fs, "x"))
    record.update(compute_features(ay,  fs, "y"))
    record.update(compute_features(az,  fs, "z"))
    record.update(compute_features(mag, fs, "mag"))  # resultant — often most useful for classification

    # ── Append to master CSV ─────────────────────────────────────────────
    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(record.keys()))
        if not file_exists:
            writer.writeheader()
            print(f"Created new feature file: {OUTPUT_CSV}")
        writer.writerow(record)
        print(f"Appended row for stage={STAGE_LABEL} → {OUTPUT_CSV}")

    # ── Print summary to console ─────────────────────────────────────────
    print("\n── Feature Summary ─────────────────────────────────")
    for k, v in record.items():
        if isinstance(v, float):
            print(f"  {k:50s} {v:.6f}")
        else:
            print(f"  {k:50s} {v}")
    print("────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()