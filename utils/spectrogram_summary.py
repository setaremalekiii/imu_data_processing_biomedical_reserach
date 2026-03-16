#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import signal


def _exec_ipynb_code(nb_path: Path, g: dict) -> None:
    nb = json.loads(nb_path.read_text())
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            exec("".join(cell.get("source", [])), g, g)


def _approx_quantiles(arrays: list[np.ndarray], q=(0.05, 0.95), max_samples: int = 1_000_000) -> tuple[float, float]:
    if not arrays:
        return float("nan"), float("nan")
    rng = np.random.default_rng(0)
    per = max(10_000, int(max_samples // max(1, len(arrays))))
    samples: list[np.ndarray] = []
    for a in arrays:
        flat = np.asarray(a).ravel()
        flat = flat[np.isfinite(flat)]
        if flat.size == 0:
            continue
        if flat.size <= per:
            samples.append(flat)
        else:
            idx = rng.choice(flat.size, size=per, replace=False)
            samples.append(flat[idx])
    if not samples:
        return float("nan"), float("nan")
    s = np.concatenate(samples)
    zmin, zmax = np.quantile(s, q)
    return float(zmin), float(zmax)


def _load_imu_channels(imu_csv: Path, detrend: str) -> list[dict]:
    df = pd.read_csv(imu_csv).dropna()
    if "t_s" not in df.columns:
        raise ValueError(f"IMU file missing t_s column: {imu_csv}")
    t = df["t_s"].to_numpy(float)
    dur = float(t[-1] - t[0])
    if not (np.isfinite(dur) and dur > 0 and len(t) >= 2):
        raise ValueError(f"Bad IMU time axis in {imu_csv}")
    fs = float((len(t) - 1) / dur)

    out = []
    for col, name in [("ax_m_s2", "IMU ax"), ("ay_m_s2", "IMU ay"), ("az_m_s2", "IMU az")]:
        if col not in df.columns:
            raise ValueError(f"IMU file missing {col} column: {imu_csv}")
        x = signal.detrend(df[col].to_numpy(float), type=detrend)
        out.append(dict(name=name, t=t, x=x, fs=fs, units="m/s²"))
    return out


def _compute_spectra(ch: dict, fmin: float, fmax: float, welch_window: str, welch_overlap: float, welch_nperseg_cap: int) -> dict:
    f, psd = welch_psd(  # noqa: F821 (loaded from function.ipynb)
        ch["x"],
        ch["fs"],
        window=welch_window,
        nperseg_cap=welch_nperseg_cap,
        overlap=welch_overlap,
    )
    fmax_eff = min(float(fmax), 0.499 * float(ch["fs"]))
    peak = peak_freq_hz(f, psd, fmin, fmax_eff)  # noqa: F821
    mean = mean_freq_hz(f, psd, fmin, fmax_eff)  # noqa: F821
    return dict(
        f=f,
        psd=psd,
        psd_db=10 * np.log10(psd + 1e-30),
        fmax_eff=float(fmax_eff),
        peak_hz=float(peak),
        mean_hz=float(mean),
    )


def _compute_spectrogram(ch: dict, fmin: float, fmax: float, spec_win_s: float, spec_overlap: float, spec_nfft_min: int) -> dict:
    f, tt, Z = spectrogram_psd_db(  # noqa: F821 (loaded from function.ipynb)
        ch["x"],
        ch["fs"],
        win_s=spec_win_s,
        overlap=spec_overlap,
        nfft_min=spec_nfft_min,
    )
    fmax_eff = min(float(fmax), 0.499 * float(ch["fs"]))
    m = (f >= float(fmin)) & (f <= float(fmax_eff))
    return dict(t=tt, f=f[m], Z=Z[m, :], fmax_eff=float(fmax_eff))


def _plot_periodograms(channels: list[dict], out_png: Path, title: str, fmin: float, fmax: float) -> None:
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(15.0, 5.0), constrained_layout=True)
    for ax, ch in zip(axs.ravel(), channels):
        f = ch["spec"]["f"]
        y = ch["spec"]["psd_db"]
        m = (f >= float(fmin)) & (f <= float(ch["spec"]["fmax_eff"]))
        ax.plot(f[m], y[m], lw=1.0, color="black")
        ax.axvline(ch["spec"]["peak_hz"], color="tab:red", lw=1.0, ls="--")
        ax.set_title(f"{ch['name']} — peak {ch['spec']['peak_hz']:.2f} Hz", fontsize=11)
        ax.set_xlim(float(fmin), float(fmax))
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("PSD (dB/Hz)")
        ax.grid(True, alpha=0.25)

    fig.suptitle(title, fontsize=14)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def _plot_spectrograms(channels: list[dict], out_png: Path, title: str, fmin: float, fmax: float) -> None:
    import matplotlib.pyplot as plt

    zmin, zmax = _approx_quantiles([ch["specgram"]["Z"] for ch in channels], q=(0.05, 0.95))

    fig, axs = plt.subplots(1, 3, figsize=(15.0, 5.0), constrained_layout=True)
    pcm = None
    for ax, ch in zip(axs.ravel(), channels):
        tt = ch["specgram"]["t"]
        f = ch["specgram"]["f"]
        Z = ch["specgram"]["Z"]
        pcm = ax.pcolormesh(tt, f, Z, shading="auto", cmap="turbo", vmin=zmin, vmax=zmax)
        ax.set_title(ch["name"], fontsize=11)
        ax.set_ylim(float(fmin), float(fmax))
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")

    fig.suptitle(title, fontsize=14)
    if pcm is not None:
        fig.colorbar(pcm, ax=axs, shrink=0.85, label="PSD (dB/Hz)")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate 3x (periodogram + spectrogram) for IMU datasets.")
    ap.add_argument(
        "--root",
        type=Path,
        default=Path("new_fracture"),
        help="Parent folder of datasets OR a single dataset folder (containing IMU/).",
    )
    ap.add_argument("--fmin", type=float, default=5.0, help="Min frequency (Hz).")
    ap.add_argument("--fmax", type=float, default=500.0, help="Max frequency (Hz).")
    ap.add_argument("--detrend", type=str, default="constant", choices=["constant", "linear"], help="Detrend type.")
    ap.add_argument("--welch-window", type=str, default="hann")
    ap.add_argument("--welch-overlap", type=float, default=0.5)
    ap.add_argument("--welch-nperseg-cap", type=int, default=32768)
    ap.add_argument("--spec-win-s", type=float, default=2.0)
    ap.add_argument("--spec-overlap", type=float, default=0.9)
    ap.add_argument("--spec-nfft-min", type=int, default=4096)
    args = ap.parse_args()

    helpers_nb = Path(__file__).resolve().parent / "function.ipynb"
    if not helpers_nb.exists():
        raise FileNotFoundError(f"Missing helper notebook: {helpers_nb}")
    _exec_ipynb_code(helpers_nb, globals())

    root = args.root
    if not root.exists():
        raise FileNotFoundError(root)

    # Allow passing either:
    # - a parent folder containing multiple datasets, or
    # - a single dataset folder containing IMU/
    if (root / "IMU" / "reading_2026-03-16_12-14-21_frac_1.csv").exists():
        datasets = [root]
    else:
        datasets = sorted([p for p in root.iterdir() if p.is_dir()])
    tag = f"{args.fmin:g}-{args.fmax:g}Hz".replace(".", "p")

    all_rows = []
    for ds in datasets:
        imu_csv = ds / "IMU" / "reading_2026-03-16_12-14-21_frac_1.csv"
        if not imu_csv.exists():
            continue

        out_dir = ds / f"spectra_{tag}"
        channels = _load_imu_channels(imu_csv, args.detrend)

        for ch in channels:
            ch["spec"] = _compute_spectra(
                ch,
                fmin=args.fmin,
                fmax=args.fmax,
                welch_window=args.welch_window,
                welch_overlap=args.welch_overlap,
                welch_nperseg_cap=args.welch_nperseg_cap,
            )
            ch["specgram"] = _compute_spectrogram(
                ch,
                fmin=args.fmin,
                fmax=args.fmax,
                spec_win_s=args.spec_win_s,
                spec_overlap=args.spec_overlap,
                spec_nfft_min=args.spec_nfft_min,
            )
            all_rows.append(
                dict(
                    dataset=ds.name,
                    channel=ch["name"],
                    fs_hz=float(ch["fs"]),
                    peak_hz=float(ch["spec"]["peak_hz"]),
                    mean_hz=float(ch["spec"]["mean_hz"]),
                    fmax_eff_hz=float(ch["spec"]["fmax_eff"]),
                    n_samples=int(len(ch["x"])),
                )
            )

        title = f"{ds.name} — band {args.fmin:g}–{args.fmax:g} Hz"
        _plot_periodograms(channels, out_dir / f"periodograms_{tag}.png", title, args.fmin, args.fmax)
        _plot_spectrograms(channels, out_dir / f"spectrograms_{tag}.png", title, args.fmin, args.fmax)

        pd.DataFrame(all_rows).query("dataset == @ds.name").to_csv(out_dir / "metrics.csv", index=False)

    if all_rows:
        pd.DataFrame(all_rows).to_csv(root / f"spectra_summary_{tag}.csv", index=False)
        print(pd.DataFrame(all_rows).sort_values(["dataset", "channel"]).to_string(index=False))
        return 0

    print("No datasets found (expected: <root>/<dataset>/IMU/yourfile).")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())