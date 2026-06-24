# -*- coding: utf-8 -*-
"""
compute_metrics.py
==================
Body Composition Metrics Extraction
KSW / ZHAW Bachelorarbeit

This script calculates body composition metrics on one selected axial slice,
usually the L3 slice. It uses the corrected segmentation file from 3D Slicer
and the water/fat NIfTI images of one patient.

Main outputs:
    - SAT area: subcutaneous adipose tissue
    - VAT area: visceral adipose tissue
    - SMA area: skeletal muscle area
    - IMAT area: intramuscular adipose tissue
    - SMI, SAT index, VAT index, VAT/SAT ratio, IMAT percentage
    - CSV file for later use in the dashboard

Usage:
    conda activate VIBESegmentator
    python compute_metrics.py --patient "<path_to_patient_folder>" --height 1.75 --z 130

    Example:
    python compute_metrics.py --patient "C:\\Data\\Anonym_Patient_0" --height 1.75 --z 130 --dashboard
"""

import os
import sys
import argparse
import subprocess
import nrrd
from pathlib import Path
from datetime import date
from scipy.ndimage import binary_fill_holes

import numpy as np
import nibabel as nib
import warnings
warnings.filterwarnings("ignore")

# Ensures that printed output is displayed correctly in the terminal,
# including special characters, and appears immediately without buffering.
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# =============================================================================
# CONFIG — only PYTHON_VIBE needs to be adjusted per machine.
# DASHBOARD_SCRIPT is resolved automatically relative to this file.
# =============================================================================

# Folder containing this script — dashboard.py must be in the same folder.
_SCRIPT_DIR = Path(__file__).parent.resolve()
DASHBOARD_SCRIPT = str(_SCRIPT_DIR / "dashboard.py")

# !! Adjust this to your VIBESegmentator python.exe path !!
PYTHON_VIBE = r"C:\Users\<username>\anaconda3\envs\VIBESegmentator\python.exe"

# Fallback labels are used if the segmentation header cannot be parsed correctly.
# These values correspond to the expected label values for muscle, SAT and VAT.
MUSCLE_LABELS_DEFAULT = [59, 60, 61, 62, 66]
SAT_LABEL_DEFAULT     = 65
VAT_LABEL_DEFAULT     = 67

# =============================================================================
# HELPERS
# =============================================================================

def log(msg, level="INFO"):
    """
    Print a formatted log message to the terminal.

    The level controls the prefix shown in front of the message, for example
    INFO, OK, WARN, ERROR or STEP. This makes the terminal output easier to read
    when the script processes a patient folder.
    """
    icons = {"INFO": "[INFO]", "OK": "[OK]", "WARN": "[WARN]", "ERROR": "[ERROR]", "STEP": "[STEP]"}
    print(f"\n{icons.get(level, '')} {msg}", flush=True)



def load_nifti(path):
    """
    Load a NIfTI image file and return both image data and header information.

    The image data is needed for pixel/voxel-based calculations. The header is
    needed to read image spacing, for example the voxel size in millimetres.
    """
    img = nib.load(str(path))
    return img.get_fdata(), img.header



def get_voxel_area(header):
    """
    Calculate the area of one pixel/voxel in an axial slice.

    The NIfTI header stores the physical voxel spacing. For area measurements on
    a 2D slice, only the x- and y-spacing are needed. The result is returned in
    mm² and is later multiplied by the number of pixels in each tissue mask.
    """
    zooms = header.get_zooms()
    return float(zooms[0]) * float(zooms[1])



def load_seg_nrrd(seg_path):
    """
    Load the corrected Slicer segmentation and extract the relevant label values.

    The file seg_corrected.seg.nrrd can contain several segmentation layers.
    This function reads the Slicer header, extracts the segment names and their
    label values, and combines all layers into one 3D label image.

    Returned values:
        combined:      3D array containing the final label image
        muscle_labels: label values belonging to skeletal muscle
        sat_label:     label value for subcutaneous adipose tissue
        vat_label:     label value for visceral adipose tissue
        imat_label:    label value for intramuscular fat, if available
    """
    data, header = nrrd.read(str(seg_path))
    log(f"Seg raw shape: {data.shape}", "INFO")

    # Parse segment information from the NRRD header.
    # Slicer stores information such as segment name, layer and label value
    # in header keys like "Segment0_Name" or "Segment0_LabelValue".
    segments = {}
    for k, v in header.items():
        if k.startswith("Segment") and "_" in k:
            parts = k.split("_", 1)
            seg_id = parts[0]
            attr   = parts[1]
            if seg_id not in segments:
                segments[seg_id] = {}
            segments[seg_id][attr] = v

    # Build a dictionary that maps each segment name to its layer and label value.
    # Example: "SAT" -> (layer_number, label_value).
    label_map = {}
    for seg_id, attrs in segments.items():
        name  = attrs.get("Name")
        layer = attrs.get("Layer")
        lv    = attrs.get("LabelValue")
        if name and layer is not None and lv is not None:
            label_map[name] = (int(layer), int(lv))

    log(f"Label map from header: {label_map}", "INFO")

    # Combine multiple Slicer segmentation layers into one 3D label image.
    # If the NRRD file is 4D, the first dimension represents separate layers.
    # For every non-zero voxel, the label value is copied into the combined image.
    if data.ndim == 4:
        combined = np.zeros(data.shape[1:], dtype=np.uint8)
        for layer_idx in range(data.shape[0]):
            layer_data = data[layer_idx]
            mask = layer_data > 0
            combined[mask] = layer_data[mask]
    else:
        # If the file is already 3D, it can be used directly.
        combined = data

    log(f"Combined seg shape: {combined.shape}", "INFO")
    log(f"Unique labels: {np.unique(combined).tolist()}", "INFO")

    # Identify all labels that should count as skeletal muscle.
    # Depending on the segmentation, muscle may be split into several named parts.
    muscle_names = ["Autochthon_R", "Autochthon_L", "Iliopsoas_R", "Iliopsoas_L", "Muscle"]
    muscle_labels = [label_map[n][1] for n in muscle_names if n in label_map]
    if not muscle_labels:
        # If the header does not contain the expected names, use predefined values.
        log("Muscle labels not found in header, using defaults", "WARN")
        muscle_labels = MUSCLE_LABELS_DEFAULT

    # Read SAT, VAT and optionally IMAT labels from the header.
    # If SAT or VAT are missing, fallback labels are used.
    sat_label  = label_map.get("SAT",  (0, SAT_LABEL_DEFAULT))[1]
    vat_label  = label_map.get("VAT",  (0, VAT_LABEL_DEFAULT))[1]
    imat_label = label_map.get("IMAT", (1, None))[1] if "IMAT" in label_map else None

    log(f"Muscle labels: {muscle_labels}", "INFO")
    log(f"SAT label:     {sat_label}", "INFO")
    log(f"VAT label:     {vat_label}", "INFO")
    log(f"IMAT label:    {imat_label}", "INFO")

    return combined, muscle_labels, sat_label, vat_label, imat_label



def extract_slice(data, z_index):
    """
    Extract one axial slice from a 3D image volume.

    The selected z-index corresponds to the L3 slice provided by the user.
    The slice is transposed so that the orientation matches the expected display
    and processing orientation used later in the script/dashboard.
    """
    return data[:, :, z_index].T



def compute_metrics(seg_slice, fat_slice, voxel_area_mm2, height_m,
                    muscle_labels, sat_label, vat_label, imat_label):
    """
    Calculate body composition metrics from one segmentation slice.

    The function counts pixels belonging to each tissue class, converts these
    pixel counts to physical areas using the voxel area, and then calculates
    height-normalised indices and ratios.
    """
    # Muscle: all pixels whose label belongs to one of the muscle labels.
    muscle_mask = np.isin(seg_slice, muscle_labels)
    muscle_px   = np.sum(muscle_mask)
    muscle_mm2  = float(muscle_px) * voxel_area_mm2

    # SAT: subcutaneous adipose tissue, counted directly from its label.
    sat_px  = np.sum(seg_slice == sat_label)
    sat_mm2 = float(sat_px) * voxel_area_mm2

    # VAT: visceral adipose tissue.
    # The filled muscle mask is used to exclude regions inside/covered by muscle,
    # so that VAT is counted only outside the muscle region.
    muscle_filled = binary_fill_holes(muscle_mask)
    vat_mask = (seg_slice == vat_label) & ~muscle_filled
    vat_px   = np.sum(vat_mask)
    vat_mm2  = float(vat_px) * voxel_area_mm2

    # IMAT: intramuscular adipose tissue.
    # If IMAT exists as a separate Slicer segment, it is counted directly.
    if imat_label is not None:
        imat_mask = seg_slice == imat_label
        imat_px   = np.sum(imat_mask)
        log(f"IMAT from Slicer segment: {imat_px} pixels", "INFO")
    else:
        # Fallback: if no IMAT segment exists, estimate IMAT by thresholding the
        # fat image inside the muscle mask. Pixels already assigned to another
        # segmentation label are excluded.
        IMAT_THRESHOLD = 100
        already_seg    = seg_slice > 0
        imat_mask = muscle_mask & (fat_slice > IMAT_THRESHOLD) & ~already_seg
        imat_px   = np.sum(imat_mask)
        log(f"IMAT from threshold fallback: {imat_px} pixels", "INFO")

    imat_mm2 = float(imat_px) * voxel_area_mm2

    # Convert from mm² to cm².
    # 1 cm² = 100 mm².
    muscle_cm2 = muscle_mm2 / 100
    sat_cm2    = sat_mm2    / 100
    vat_cm2    = vat_mm2    / 100
    imat_cm2   = imat_mm2   / 100

    # Calculate height-normalised indices.
    # These indices make body composition values more comparable between patients
    # with different body heights.
    height2   = height_m ** 2
    smi       = muscle_cm2 / height2
    sat_index = sat_cm2    / height2
    vat_index = vat_cm2    / height2

    # Calculate clinically useful ratios.
    # VAT/SAT describes the relation between visceral and subcutaneous fat.
    # IMAT percentage describes how much of the muscle area consists of IMAT.
    vat_sat_ratio = vat_mm2 / sat_mm2 if sat_mm2 > 0 else float('nan')
    imat_pct      = (imat_mm2 / muscle_mm2 * 100) if muscle_mm2 > 0 else 0.0

    # Return all values rounded to a readable precision.
    return {
        'sat_mm2':       round(sat_mm2,       1),
        'vat_mm2':       round(vat_mm2,       1),
        'sma_mm2':       round(muscle_mm2,    1),
        'imat_mm2':      round(imat_mm2,      1),
        'sat_cm2':       round(sat_cm2,       1),
        'vat_cm2':       round(vat_cm2,       1),
        'sma_cm2':       round(muscle_cm2,    1),
        'imat_cm2':      round(imat_cm2,      1),
        'smi':           round(smi,           2),
        'sat_index':     round(sat_index,     2),
        'vat_index':     round(vat_index,     2),
        'vat_sat_ratio': round(vat_sat_ratio, 4),
        'imat_pct':      round(imat_pct,      1),
    }



def save_csv(metrics, patient_id, height_m, z_index, voxel_area, output_dir):
    """
    Save the calculated metrics into a CSV file.

    The CSV file contains patient information, slice information and all body
    composition values. It is saved inside the patient's output folder and later
    copied to the dashboard folder.
    """
    import csv
    csv_path = output_dir / "body_composition_results.csv"

    # One row is created for the selected patient and selected L3 slice.
    row = {
        'patient_id':     patient_id,
        'date':           str(date.today()),
        'input':          'combined',
        'height_m':       height_m,
        'l3_z_index':     z_index,
        'voxel_area_mm2': round(voxel_area, 4),
        'sat_mm2':        metrics['sat_mm2'],
        'vat_mm2':        metrics['vat_mm2'],
        'sma_mm2':        metrics['sma_mm2'],
        'imat_mm2':       metrics['imat_mm2'],
        'sat_cm2':        metrics['sat_cm2'],
        'vat_cm2':        metrics['vat_cm2'],
        'sma_cm2':        metrics['sma_cm2'],
        'imat_cm2':       metrics['imat_cm2'],
        'smi':            metrics['smi'],
        'sat_index':      metrics['sat_index'],
        'vat_index':      metrics['vat_index'],
        'vat_sat_ratio':  metrics['vat_sat_ratio'],
        'imat_pct':       metrics['imat_pct'],
    }

    # Write the CSV with a header row and one data row.
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)
    return csv_path



def print_metrics(metrics, patient_id, height_m, z_index):
    """
    Print the calculated metrics in a readable table in the terminal.

    This gives immediate feedback after the calculation and helps check whether
    the values look plausible before opening the dashboard.
    """
    print(f"\n{'='*60}", flush=True)
    print(f"  BODY COMPOSITION METRICS @ L3  |  {patient_id}", flush=True)
    print(f"  Height: {height_m} m  |  Z-Index: {z_index}", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"  {'Metric':<25} {'Value':>14}", flush=True)
    print(f"{'-'*60}", flush=True)
    print(f"  {'SAT Area (cm2)':<25} {metrics['sat_cm2']:>14.1f}", flush=True)
    print(f"  {'VAT Area (cm2)':<25} {metrics['vat_cm2']:>14.1f}", flush=True)
    print(f"  {'Muscle Area (cm2)':<25} {metrics['sma_cm2']:>14.1f}", flush=True)
    print(f"  {'IMAT Area (cm2)':<25} {metrics['imat_cm2']:>14.1f}", flush=True)
    print(f"  {'IMAT %':<25} {metrics['imat_pct']:>14.1f}", flush=True)
    print(f"{'-'*60}", flush=True)
    print(f"  {'SMI (cm2/m2)':<25} {metrics['smi']:>14.2f}", flush=True)
    print(f"  {'SAT Index (cm2/m2)':<25} {metrics['sat_index']:>14.2f}", flush=True)
    print(f"  {'VAT Index (cm2/m2)':<25} {metrics['vat_index']:>14.2f}", flush=True)
    print(f"  {'VAT/SAT Ratio':<25} {metrics['vat_sat_ratio']:>14.3f}", flush=True)
    print(f"{'='*60}", flush=True)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """
    Main workflow of the script.

    Steps:
        1. Read command-line arguments.
        2. Build expected input paths for water, fat and segmentation files.
        3. Load image data and segmentation data.
        4. Extract the selected L3 slice.
        5. Calculate body composition metrics.
        6. Save results as CSV.
        7. Optionally start the dashboard.
    """
    # Define the command-line arguments required to run the script.
    parser = argparse.ArgumentParser(description="Body Composition Metrics - KSW / ZHAW")
    parser.add_argument("--patient",   required=True)
    parser.add_argument("--height",    required=True, type=float)
    parser.add_argument("--z",         required=True, type=int)
    parser.add_argument("--dashboard", action="store_true")
    args = parser.parse_args()

    # Build the expected folder structure for the selected patient.
    # The script assumes that water.nii, fat.nii and seg_corrected.seg.nrrd
    # are stored inside output/nifti of the patient folder.
    patient_root = Path(args.patient)
    nifti_dir    = patient_root / "output" / "nifti"

    water_path = nifti_dir / "water.nii"
    fat_path   = nifti_dir / "fat.nii"
    seg_path   = nifti_dir / "seg_corrected.seg.nrrd"

    # Stop the script early if any required input file is missing.
    for p in [water_path, fat_path, seg_path]:
        if not p.exists():
            log(f"File not found: {p}", "ERROR")
            sys.exit(1)

    log(f"Patient:  {patient_root.name}", "STEP")
    log(f"Height:   {args.height} m", "INFO")
    log(f"Z-Index:  {args.z} (L3)", "INFO")

    # Load image volumes and the corrected segmentation.
    log("Loading files...", "STEP")
    water_data, water_header = load_nifti(water_path)
    fat_data, _              = load_nifti(fat_path)
    seg_combined, muscle_labels, sat_label, vat_label, imat_label = load_seg_nrrd(seg_path)

    # Calculate the physical area represented by one pixel in the selected slice.
    voxel_area = get_voxel_area(water_header)
    log(f"Voxel area: {voxel_area:.4f} mm2", "INFO")

    # Check whether the selected z-index is inside the available segmentation volume.
    max_z = seg_combined.shape[2] - 1
    if args.z > max_z:
        log(f"Z-index {args.z} out of bounds (max={max_z})!", "ERROR")
        sys.exit(1)

    # Calculate fat Z-index — water and fat may have different origins.
    # The following values are read from the image headers to correct possible
    # slice offsets between the water image and the fat image.
    water_img_z = float(nib.load(str(water_path)).header.get_sform()[2, 3])
    fat_img_z   = float(nib.load(str(fat_path)).header.get_sform()[2, 3])
    voxel_z     = float(water_data.shape[2])
    voxel_size_z = abs(water_img_z / voxel_z) if voxel_z > 0 else 2.5

    # Re-load headers for accurate spacing.
    # The origin and slice thickness are used to estimate how many slices the fat
    # image is shifted compared with the water image.
    water_hdr   = nib.load(str(water_path)).header
    fat_hdr     = nib.load(str(fat_path)).header
    water_orig_z = float(water_hdr.get_sform()[2, 3])
    fat_orig_z   = float(fat_hdr.get_sform()[2, 3])
    slice_thick  = float(water_hdr.get_zooms()[2])

    # Calculate the slice offset and select the corresponding fat slice.
    # np.clip ensures that the selected fat slice stays within valid image bounds.
    z_offset = round((water_orig_z - fat_orig_z) / slice_thick)
    z_fat    = int(np.clip(args.z + z_offset, 0, fat_data.shape[2] - 1))

    # Inform the user if the fat slice had to be shifted relative to the water slice.
    if z_offset != 0:
        log(f"Z offset Water vs Fat: {z_offset} slice(s) — z_water={args.z}, z_fat={z_fat}", "INFO")
    else:
        z_fat = args.z

    # Extract the actual 2D slices used for the metric calculation.
    seg_slice = extract_slice(seg_combined, args.z)
    fat_slice = extract_slice(fat_data,     z_fat)

    # Print basic label and pixel information for plausibility checking.
    log(f"Labels @ Z={args.z}: {np.unique(seg_slice).tolist()}", "INFO")
    log(f"Muscle pixels: {np.sum(np.isin(seg_slice, muscle_labels))}", "INFO")
    log(f"SAT pixels:    {np.sum(seg_slice == sat_label)}", "INFO")
    log(f"VAT pixels:    {np.sum(seg_slice == vat_label)}", "INFO")

    # Calculate all body composition metrics for the selected slice.
    log("Computing metrics...", "STEP")
    metrics = compute_metrics(
        seg_slice=seg_slice,
        fat_slice=fat_slice,
        voxel_area_mm2=voxel_area,
        height_m=args.height,
        muscle_labels=muscle_labels,
        sat_label=sat_label,
        vat_label=vat_label,
        imat_label=imat_label,
    )

    # Display the results directly in the terminal.
    print_metrics(metrics, patient_root.name, args.height, args.z)

    # Save the metrics as CSV inside the patient output folder.
    log("Saving CSV...", "STEP")
    csv_path = save_csv(
        metrics=metrics,
        patient_id=patient_root.name,
        height_m=args.height,
        z_index=args.z,
        voxel_area=voxel_area,
        output_dir=patient_root / "output"
    )
    log(f"CSV saved: {csv_path}", "OK")

    # Copy the CSV into the dashboard folder so that the dashboard can read it.
    import shutil
    dashboard_csv = Path(DASHBOARD_SCRIPT).parent / "body_composition_results.csv"
    shutil.copy(csv_path, dashboard_csv)
    log(f"CSV copied to dashboard folder: {dashboard_csv}", "OK")

    # If the user provides --dashboard, start the Panel dashboard automatically.
    # The patient path and selected z-index are passed to the dashboard as arguments.
    if args.dashboard:
        log("Starting dashboard...", "STEP")
        subprocess.Popen([
            PYTHON_VIBE, "-m", "panel", "serve", DASHBOARD_SCRIPT,
            "--show",
            "--args", f"--patient={patient_root}", f"--z={args.z}"
        ])


# Standard Python entry point.
# This ensures that main() runs only when this file is executed directly.
if __name__ == "__main__":
    main()