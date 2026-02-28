#!/usr/bin/env python3
"""
analyze_force_fft.py

Usage:
  python analyze_force_fft.py "D:/No_fracture/2026-02-27_14_53_20/LoadCell-5min-setup2.CSV"

Notes:
- Expects two columns: time (seconds) and load/force (N), but names can vary.
- Handles whitespace in headers like "Elapsed Time  " and "Load 2 ".
- Removes DC offset, applies Hann window, then computes one-sided amplitude spectrum.
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def find_time_and_signal_columns(df: pd.DataFrame):
    """
    Heuristics to find time and signal columns.
    Prefers columns containing 'time' and force/load-like columns.
    Falls back to first two numeric columns.
    """
    # Normalize column names
    cols = list(df.columns)
    norm = {c: str(c).strip().lower().replace(" ", "") for c in cols}

    # Candidate time columns
    time_cands = [c for c in cols if "time" in norm[c] or norm[c] in ("t", "sec", "seconds")]
    # Candidate signal columns (force/load)
    sig_cands = [
        c for c in cols
        if any(k in norm[c] for k in ("load", "force", "n", "newton", "sensor", "value"))
        and c not in time_cands
    ]

    # Keep only numeric columns for fallback
    numeric_cols = []
    for c in cols:
        try:
            pd.to_numeric(df[c], errors="raise")
            numeric_cols.append(c)
        except Exception:
            pass

    time_col = None
    sig_col = None

    if time_cands:
        time_col = time_cands[0]
    if sig_cands:
        sig_col = sig_cands[0]

    if time_col is None or sig_col is None:
        # Fallback: pick first two numeric columns
        if len(numeric_cols) < 2:
            raise ValueError("Couldn't find at least two numeric columns (time + signal).")
        time_col = time_col or numeric_cols[0]
        sig_col = sig_col or numeric_cols[1]

    return time_col, sig_col


def one_sided_amplitude_spectrum(x: np.ndarray, fs: float):
    """
    Returns (freqs, amps) for one-sided amplitude spectrum of x.
    Uses rFFT and amplitude correction for Hann window + one-sided scaling.
    """
    n = len(x)
    if n < 4:
        raise ValueError("Not enough samples for FFT.")

    # Hann window
    w = np.hanning(n)
    xw = x * w

    # rFFT
    X = np.fft.rfft(xw)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)

    # Amplitude correction:
    # For a pure tone, amplitude in time domain ~ (2*|X|)/sum(window)
    # (DC and Nyquist bins should NOT be doubled)
    scale = np.sum(w)
    amps = np.abs(X) / scale
    amps[1:-1] *= 2.0  # one-sided correction except DC & Nyquist (if present)

    return freqs, amps


def pick_top_peaks(freqs, amps, k=5, fmin=0.0):
    """
    Picks top k peaks by amplitude above fmin, excluding DC.
    Simple approach: take largest amplitudes after masking, without peak-shape detection.
    """
    mask = freqs >= fmin
    f = freqs[mask]
    a = amps[mask]

    if len(a) < 3:
        return []

    # Exclude DC exactly
    if f[0] == 0:
        f = f[1:]
        a = a[1:]

    idx = np.argsort(a)[::-1][:k]
    peaks = [(float(f[i]), float(a[i])) for i in idx]
    # Sort by frequency for nicer printing
    peaks.sort(key=lambda t: t[0])
    return peaks


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_force_fft.py Test2-10min-setup1.CSV")
        sys.exit(1)

    path = sys.argv[1]

    # Read CSV. Try common separators, be forgiving.
    # If your file is tab-separated, this still usually works.
    try:
        df = pd.read_csv(path, engine="python")
    except Exception:
        df = pd.read_csv(path, sep=r"[,\t;]", engine="python")

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # Try to coerce everything to numeric (non-numeric become NaN)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows missing time or signal later
    time_col, sig_col = find_time_and_signal_columns(df)
    df = df[[time_col, sig_col]].dropna()

    t = df[time_col].to_numpy(dtype=float)
    x = df[sig_col].to_numpy(dtype=float)

    # Sort by time (in case file isn't ordered)
    order = np.argsort(t)
    t = t[order]
    x = x[order]

    # Estimate sampling rate
    dt = np.diff(t)
    dt_med = np.median(dt)
    if dt_med <= 0:
        raise ValueError("Time column is not increasing properly.")

    # Check uniformity
    rel_jitter = np.std(dt) / dt_med if len(dt) > 5 else 0.0
    fs = 1.0 / dt_med

    # Detrend (remove mean)
    x0 = x - np.mean(x)

    # FFT
    freqs, amps = one_sided_amplitude_spectrum(x0, fs=fs)

    # Dominant (exclude DC)
    if len(freqs) > 1:
        dom_i = 1 + np.argmax(amps[1:])
        dom_f = float(freqs[dom_i])
        dom_a = float(amps[dom_i])
    else:
        dom_f, dom_a = 0.0, 0.0

    # Print summary
    print("\n=== Sampling info ===")
    print(f"Samples: {len(t)}")
    print(f"Median dt: {dt_med:.6g} s  =>  Fs ≈ {fs:.3f} Hz")
    if rel_jitter > 0.01:
        print(f"WARNING: time-step jitter seems non-trivial (std(dt)/median(dt) ≈ {rel_jitter:.3%}).")
        print("If this is high, consider resampling to uniform time before FFT.")

    print("\n=== Dominant FFT component ===")
    print(f"Frequency: {dom_f:.6g} Hz")
    print(f"Amplitude: {dom_a:.6g} (same units as signal)")

    peaks = pick_top_peaks(freqs, amps, k=8, fmin=0.5)  # ignore ultra-low drift
    print("\n=== Top peaks (freq Hz, amplitude) ===")
    for f, a in peaks:
        print(f"{f:.6g} Hz\t{a:.6g}")

    # --- Plots ---
    plt.figure()
    plt.plot(t, x)
    plt.xlabel("Time (s)")
    plt.ylabel(sig_col)
    plt.title("Signal (time domain)")
    plt.grid(True)

    plt.figure()
    plt.plot(freqs, amps)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.title("FFT amplitude spectrum (one-sided, Hann window)")
    plt.grid(True)

    # Zoomed view (optional) up to, say, 200 Hz for vibrator-like signals
    plt.figure()
    fmax = min(200.0, freqs[-1])
    zoom_mask = freqs <= fmax
    plt.plot(freqs[zoom_mask], amps[zoom_mask])
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.title(f"FFT amplitude spectrum (0–{fmax:g} Hz)")
    plt.grid(True)

    plt.show()


if __name__ == "__main__":
    main()