"""
run_pipeline.py
===============
Automated Body Composition Pipeline — Kantonsspital Winterthur / ZHAW
----------------------------------------------------------------------
Usage:
    conda activate VIBESegmentator
    python run_pipeline.py --patient "<path_to_patient_folder>"

    Example:
    python run_pipeline.py --patient "C:\\Data\\Anonym_Patient_0"
"""

import os
import sys
import argparse
import subprocess
import time
import re
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# =============================================================================
# CONFIG — adjust VIBE_SCRIPT to your VIBESegmentator installation.
# All other scripts are resolved relative to this file automatically.
# =============================================================================

# Folder containing this script
_SCRIPT_DIR = Path(__file__).parent.resolve()

# !! Adjust this to the run_VIBESegmentator.py path on your machine !!
# Example: r"C:\Users\<username>\VIBESegmentator\run_VIBESegmentator.py"
VIBE_SCRIPT      = r"C:\Users\<username>\VIBESegmentator\run_VIBESegmentator.py"

# These are resolved automatically — no changes needed
DASHBOARD_SCRIPT = str(_SCRIPT_DIR / "dashboard.py")
METRICS_NOTEBOOK = str(_SCRIPT_DIR / "03_body_composition_metrics.ipynb"

# =============================================================================
# HELPERS
# =============================================================================

def log(msg, level="INFO"):
    icons = {"INFO": "[INFO]", "OK": "[OK]", "WARN": "[WARN]", "ERROR": "[ERROR]", "STEP": "[STEP]"}
    print(f"\n{icons.get(level, '')} {msg}", flush=True)


def find_dicom_folder(scan_dir, keywords_required, keywords_exclude=None):
    keywords_exclude = keywords_exclude or []
    candidates = []
    for folder in scan_dir.iterdir():
        if not folder.is_dir():
            continue
        name_lower = folder.name.lower()
        if all(k.lower() in name_lower for k in keywords_required):
            if not any(k.lower() in name_lower for k in keywords_exclude):
                candidates.append(folder)
    if not candidates:
        return None

    def score(f):
        name = f.name.lower()
        s = 0
        if "km" in name:  s += 100
        if "tfe" in name: s += 10
        m = re.search(r'(\d+)', f.name)
        if m:
            s += int(m.group(1)) * 0.001
        return s

    candidates.sort(key=score)
    return candidates[0]


def decompress_dicom(src_folder, dst_folder):
    dst_folder.mkdir(parents=True, exist_ok=True)
    dcm_files = sorted(src_folder.glob("*.dcm"))
    if not dcm_files:
        dcm_files = sorted([f for f in src_folder.iterdir() if f.is_file()])
    log(f"Decompressing {len(dcm_files)} files from: {src_folder.name}", "INFO")
    for i, f in enumerate(dcm_files):
        out = dst_folder / f.name
        subprocess.run(["dcmdjpeg", str(f), str(out)], capture_output=True)
        if i % 50 == 0:
            print(f"   {i}/{len(dcm_files)} done...", end="\r", flush=True)
    print(f"   {len(dcm_files)}/{len(dcm_files)} done.   ", flush=True)


def convert_to_nifti(src_folder, out_dir, filename):
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["dcm2niix", "-o", str(out_dir), "-f", filename, "-z", "n", str(src_folder)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    nii = out_dir / f"{filename}.nii"
    if nii.exists():
        return nii
    matches = list(out_dir.glob(f"{filename}*.nii"))
    if matches:
        matches[0].rename(nii)
        return nii
    log(f"dcm2niix stdout: {result.stdout}", "WARN")
    log(f"dcm2niix stderr: {result.stderr}", "WARN")
    return None


def wait_for_user(message):
    print(f"\n{'─'*60}", flush=True)
    print(f"  [PAUSE] {message}", flush=True)
    print(f"{'─'*60}", flush=True)
    input("  Press ENTER when ready...")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_pipeline(patient_root):

    print(f"\n{'='*60}", flush=True)
    print(f"  BODY COMPOSITION PIPELINE", flush=True)
    print(f"  Patient: {patient_root.name}", flush=True)
    print(f"{'='*60}", flush=True)

    pipeline_start = time.time()

    # ── Find scan session folder ──────────────────────────────────────────────
    print(f"\nSearching in: {patient_root}", flush=True)
    scan_candidates = []
    for d in patient_root.iterdir():
        print(f"  found: {d.name} | is_dir={d.is_dir()}", flush=True)
        if d.is_dir() and not d.name.lower().startswith("output"):
            scan_candidates.append(d)

    print(f"  scan_candidates: {[d.name for d in scan_candidates]}", flush=True)

    if len(scan_candidates) == 0:
        log("No scan folder found!", "ERROR")
        sys.exit(1)
    elif len(scan_candidates) == 1:
        scan_dir = scan_candidates[0]
    else:
        scan_dir = max(scan_candidates, key=lambda d: sum(1 for _ in d.iterdir()))

    log(f"Scan folder: {scan_dir.name}", "INFO")

    # ── Output folders ────────────────────────────────────────────────────────
    out_root   = patient_root / "output"
    nifti_dir  = out_root / "nifti"
    decomp_dir = out_root / "dicom_decompressed"
    out_root.mkdir(exist_ok=True)

    # =========================================================================
    # STEP 1 - Find DIXON folders
    # =========================================================================
    log("STEP 1 - Finding DIXON Water & Fat folders", "STEP")

    print(f"\nAll folders in {scan_dir.name}:", flush=True)
    for f in scan_dir.iterdir():
        if f.is_dir():
            print(f"  {f.name}", flush=True)

    # ── Water folder ──────────────────────────────────────────────────────────
    # Try 1: contains "water"
    water_folder = find_dicom_folder(
        scan_dir,
        keywords_required=["water"],
        keywords_exclude=[]
    )
    # Try 2: ends with _W (e.g. mDIXON_all_W)
    if water_folder is None:
        for folder in scan_dir.iterdir():
            if folder.is_dir() and folder.name.upper().endswith("_W"):
                water_folder = folder
                log(f"Water found via _W fallback: {folder.name}", "INFO")
                break

    # ── Fat folder ────────────────────────────────────────────────────────────
    # Try 1: mDIXON + _tra_F keyword
    fat_folder = find_dicom_folder(
        scan_dir,
        keywords_required=["mdixon", "_tra_f"],
        keywords_exclude=["water", "survey", "dwi", "dadc", "mobiview", "befund", "w_cor"]
    )
    # Try 2: mDIXON but not water/_w/ip/op/_ff
    if fat_folder is None:
        fat_folder = find_dicom_folder(
            scan_dir,
            keywords_required=["mdixon"],
            keywords_exclude=["water", "_w", "survey", "dwi", "dadc",
                              "mobiview", "befund", "w_cor", "ip", "op", "_ff", "tfe"]
        )
    # Try 3: IP (InPhase as fallback for Fat)
    if fat_folder is None:
        fat_folder = find_dicom_folder(
            scan_dir,
            keywords_required=["mdixon", "ip"],
            keywords_exclude=["water", "survey", "dwi", "dadc", "mobiview", "befund", "w_cor"]
        )
    # Try 4: ends with _F (e.g. mDIXON_all_F)
    if fat_folder is None:
        for folder in scan_dir.iterdir():
            if folder.is_dir() and folder.name.upper().endswith("_F"):
                fat_folder = folder
                log(f"Fat found via _F fallback: {folder.name}", "INFO")
                break

    # ── FF folder (optional) ─────────────────────────────────────────────────
    ff_folder = None
    for folder in scan_dir.iterdir():
        if folder.is_dir() and folder.name.upper().endswith("_FF"):
            ff_folder = folder
            break

    if water_folder is None:
        log("No Water folder found! Please check manually.", "ERROR")
        sys.exit(1)
    if fat_folder is None:
        log("No Fat folder found! Please check manually.", "ERROR")
        sys.exit(1)

    log(f"Water : {water_folder.name}", "OK")
    log(f"Fat   : {fat_folder.name}", "OK")
    if ff_folder:
        log(f"FF    : {ff_folder.name} (optional)", "OK")
    else:
        log("FF folder not found - skipping (optional)", "INFO")

    # =========================================================================
    # STEP 2 - Decompress DICOM
    # =========================================================================
    log("STEP 2 - DICOM decompression (dcmdjpeg)", "STEP")
    t = time.time()

    water_decomp = decomp_dir / "water"
    fat_decomp   = decomp_dir / "fat"

    decompress_dicom(water_folder, water_decomp)
    decompress_dicom(fat_folder,   fat_decomp)

    if ff_folder:
        ff_decomp = decomp_dir / "ff"
        decompress_dicom(ff_folder, ff_decomp)

    log(f"Decompression done ({time.time()-t:.0f}s)", "OK")

    # =========================================================================
    # STEP 3 - Convert to NIfTI
    # =========================================================================
    log("STEP 3 - NIfTI conversion (dcm2niix)", "STEP")
    t = time.time()

    water_nii = convert_to_nifti(water_decomp, nifti_dir, "water")
    fat_nii   = convert_to_nifti(fat_decomp,   nifti_dir, "fat")

    if water_nii is None or fat_nii is None:
        log("NIfTI conversion failed!", "ERROR")
        sys.exit(1)

    ff_nii = None
    if ff_folder:
        ff_nii = convert_to_nifti(ff_decomp, nifti_dir, "ff")
        if ff_nii:
            log(f"ff.nii -> {ff_nii}", "OK")
        else:
            log("FF conversion failed - skipping (optional)", "WARN")

    log(f"water.nii -> {water_nii}", "OK")
    log(f"fat.nii   -> {fat_nii}", "OK")
    log(f"Conversion done ({time.time()-t:.0f}s)", "OK")

    # =========================================================================
    # STEP 4 - VIBESegmentator
    # =========================================================================
    log("STEP 4 - VIBESegmentator (running segmentation...)", "STEP")
    t = time.time()

    seg_out = nifti_dir / "seg.nii.gz"

    vibe_cmd = [
        "python", VIBE_SCRIPT,
        "--img", str(water_nii),
        "--img", str(fat_nii),
        "--out_path", str(seg_out),
        "--ddevice", "cuda",
        "--override"
    ]

    print(f"\n   Command: {' '.join(vibe_cmd)}\n", flush=True)
    result = subprocess.run(vibe_cmd)

    if result.returncode != 0:
        log("VIBESegmentator returned an error!", "ERROR")
        sys.exit(1)

    log(f"Segmentation saved: {seg_out}", "OK")
    log(f"VIBESegmentator done ({time.time()-t:.0f}s)", "OK")

    # =========================================================================
    # STEP 5 - Summary & time logging
    # =========================================================================
    total_time = time.time() - pipeline_start

    print(f"""
{'='*60}
  PIPELINE COMPLETE
{'='*60}
  Time summary:
     Total time:  {total_time/60:.1f} minutes

  Outputs saved to:
     {out_root}
{'='*60}
    """, flush=True)

    log_file = out_root / "pipeline_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Patient:          {patient_root.name}\n")
        f.write(f"Scan folder:      {scan_dir.name}\n")
        f.write(f"Water folder:     {water_folder.name}\n")
        f.write(f"Fat folder:       {fat_folder.name}\n")
        f.write(f"FF folder:        {ff_folder.name if ff_folder else 'N/A'}\n")
        f.write(f"Total time (min): {total_time/60:.1f}\n")
    log(f"Log saved: {log_file}", "INFO")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Body Composition Pipeline - KSW / ZHAW")
    parser.add_argument(
        "--patient",
        required=True,
        help='Path to the patient folder, e.g. "C:\\Data\\Anonym_Patient_0"'
    )
    args = parser.parse_args()

    patient_path = Path(args.patient)
    if not patient_path.exists():
        print(f"[ERROR] Folder not found: {patient_path}", flush=True)
        sys.exit(1)

    run_pipeline(patient_path)