# Quantitative Soft-Tissue Analysis in Medical Imaging

**Bachelor's Thesis — ZHAW School of Life Sciences, 2026**  
In collaboration with Kantonsspital Winterthur (KSW)

> **⚠️ Research Prototype**  
> This software is a research prototype developed as part of a Bachelor's thesis. It must **not** be used for clinical decision-making without further validation.

---

## What does this project do?

This project provides two complementary workflows for extracting **body composition metrics** from **Dixon MRI scans** at the **L3 vertebral level**:

| Metric | Description |
|--------|-------------|
| SAT Area (cm²) | Subcutaneous adipose tissue |
| VAT Area (cm²) | Visceral adipose tissue |
| SMA / SMI (cm², cm²/m²) | Skeletal muscle area and index |
| IMAT Area / % | Intramuscular adipose tissue |
| SAT Index / VAT Index | Height-normalised fat indices |
| VAT/SAT Ratio | Cardiometabolic risk indicator |

Results are displayed in an **interactive Panel dashboard** with segmentation overlays, percentile comparisons, bilingual interface (DE/EN), and PDF export.

---

## Repository Structure

```
Quantitative-Soft-Tissue-Analysis-in-Medical-Imaging/
│
├── automated_pipeline/              ← Luca Meier
│   ├── KSWBodyComposition.py        3D Slicer module (main entry point)
│   ├── run_pipeline.py              DICOM → NIfTI → VIBESegmentator
│   ├── compute_metrics.py           Metric extraction from segmentation
│   └── dashboard.py                 Interactive Panel dashboard
│
├── semi_automatic_pipeline/         ← Ilenia Giannini
│   ├── KSW_SemiAutomatic_BCW_module.py   3D Slicer module
│   └── dashboard.py                      Interactive Panel dashboard
│
├── NiceGUI/                        Experimental GUI prototype for comparison with panel
│   ├── io_utils.py                 Helper functions for loading and handling result files
│   ├── main.py                     Main entry point of the experimental NiceGUI interface
│   ├── metrics.py                  Prototype functions for calculating body composition metrics
│   ├── reference.py                Experimental reference value and interpretation logic
│   ├── report.py                   Prototype for PDF report generation
│   └── requirements.txt            Python dependencies for the NiceGUI prototype
|
└── README.md
```

---

## Prerequisites

Before you start, make sure the following software is installed on your Windows computer.

### 1. Required Software

| Software | Version | Download |
|----------|---------|----------|
| 3D Slicer | 5.10.0 or newer | https://www.slicer.org |
| Anaconda (Python) | Latest | https://www.anaconda.com |
| dcmdjpeg | Any | Part of DCMTK: https://dcmtk.org |
| dcm2niix | Latest | https://github.com/rordenlab/dcm2niix/releases |

> **dcmdjpeg and dcm2niix** must be accessible from the command line (i.e. added to your system PATH). To check, open a Command Prompt and type `dcmdjpeg` — if you see a help message, it is installed correctly.

> **Note for the semi-automatic workflow:** VIBESegmentator, `dcmdjpeg`, and `dcm2niix` are only required for the automated workflow. The semi-automatic module runs directly inside 3D Slicer and works with loaded Dixon fat and water images.

### 2. VIBESegmentator (Deep Learning Segmentation Model)

The automated pipeline uses VIBESegmentator for tissue segmentation. Follow these steps to install it:

```bash
# Step 1: Create a new conda environment with Python 3.11
conda create -n VIBESegmentator python=3.11

# Step 2: Activate the environment
conda activate VIBESegmentator

# Step 3: Install PyTorch (with CUDA support for GPU — recommended)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Step 4: Clone and install VIBESegmentator
git clone https://github.com/robert-graf/VIBESegmentator.git
cd VIBESegmentator
pip install -r requirements.txt

# Step 5: Install additional required packages
pip install panel nibabel nrrd scipy matplotlib pymupdf pandas
```

> **GPU strongly recommended.** On a modern GPU, segmentation takes ~30–50 seconds per patient. On CPU only, it may take several minutes.

After installation, **note down the full path** to the folder where VIBESegmentator was installed (i.e. where `run_VIBESegmentator.py` is located). You will need this path in the setup step below.

---

## Setup (One-time configuration)

### Step 1: Create the correct folder structure

Copy the files from `automated_pipeline/` into a folder on your computer, using this exact structure:

```
C:\KSW_Pipeline\
    KSWBodyComposition.py        ← this file goes directly in the folder
    scripts\
        run_pipeline.py
        compute_metrics.py
        dashboard.py
```

> **Important:** `run_pipeline.py`, `compute_metrics.py` and `dashboard.py` must be placed in a `scripts` subfolder — **not** next to `KSWBodyComposition.py`. If they are in the same folder, 3D Slicer will try to load them as modules and fail on startup.

### Step 2: Set the two required paths

Open `run_pipeline.py` **and** `compute_metrics.py` in a text editor (e.g. Notepad or Notepad++).

In `KSWBodyComposition.py`, find this line near the top and replace `<username>` with your actual Windows username:

```python
# BEFORE:
PYTHON_VIBE = r"C:\Users\<username>\anaconda3\envs\VIBESegmentator\python.exe"

# AFTER (example):
PYTHON_VIBE = r"C:\Users\roman.guggenberger\anaconda3\envs\VIBESegmentator\python.exe"
```

> **How to find your exact path:** Open Anaconda Prompt and run these two commands:
> ```
> conda activate VIBESegmentator
> where python
> ```
> Copy the output path exactly into `PYTHON_VIBE`.

> **Note:** `run_pipeline.py` and `compute_metrics.py` do **not** need `PYTHON_VIBE` — they are launched by `KSWBodyComposition.py` using the correct Python automatically.

Additionally, in `run_pipeline.py` only, set the path to `run_VIBESegmentator.py`:

```python
# BEFORE:
VIBE_SCRIPT = r"C:\Users\<username>\VIBESegmentator\run_VIBESegmentator.py"

# AFTER (example — use the folder where you cloned VIBESegmentator):
VIBE_SCRIPT = r"C:\Users\roman.guggenberger\VIBESegmentator\run_VIBESegmentator.py"
```

### Step 3: Add the module to 3D Slicer

1. Open **3D Slicer**
2. Go to **Edit → Application Settings → Modules**
3. Under **Additional module paths**, click the ➕ button
4. Navigate to the folder containing `KSWBodyComposition.py` and select it
5. Click **OK** and **restart 3D Slicer**
6. After restart, find the module under: **Modules → KSW → KSW Body Composition**

---

## Patient Folder Structure

The pipeline expects one folder per patient. The folder must contain a scan session subfolder with the DICOM series inside.

**Standard format (new KSW datasets, recommended):**
```
Anonym_Patient/
└── 20260506_1/                        ← scan session folder (date-based name)
    ├── MR_Seq._1203_mDIXON_all_W/    ← water channel DICOM series (ends with _W)
    └── MR_Seq._1206_mDIXON_all_F/    ← fat channel DICOM series (ends with _F)
```

The pipeline automatically detects the water and fat series. It looks for folder names:
- Ending in `_W` → water channel
- Ending in `_F` → fat channel
- Containing the keyword `water` → water channel (fallback)

**Alternative format (older datasets with many sequences):**
```
Anonym_Patient_0/
└── 20260318_MRI_ABDOMEN_K/            ← scan session folder
    ├── MR_Seq._603_AI_T1_Nativ_mDIXON_TSE_tra_water only/   ← water
    ├── MR_Seq._606_AI_T1_nativ_mDIXON_tra_F/                ← fat
    └── ... (many other series — the pipeline ignores them)
```

> **Important:** Always select the **top-level patient folder** (e.g. `Anonym_Patient_0`) in the module — not the scan session folder inside it.

---

## How to Use — Automated Workflow (Step by Step)

### Step 1 — Select Patient Folder

In the **KSW Body Composition** module in 3D Slicer:

1. Click **Browse...** next to "Patient folder"
2. Select the **top-level patient folder** (e.g. `Anonym_Patient_0`)
3. Enter the **patient height in metres** (e.g. `1.75`) — needed for SMI calculation

---

### Step 2 — Run Automated Pipeline

Click **Run Pipeline**.

This automatically runs:
- DICOM decompression (`dcmdjpeg`)
- NIfTI conversion (`dcm2niix`)
- VIBESegmentator segmentation

> Watch the **Python Console** in 3D Slicer for progress messages. When you see `PIPELINE COMPLETE`, the pipeline has finished. This typically takes **2–5 minutes** depending on your hardware.

---

### Step 3 — Load Images into 3D Slicer

Click **Load Images into Slicer**.

This loads the following files into 3D Slicer:
- `water.nii` — water channel MRI
- `fat.nii` — fat channel MRI
- `seg.nii.gz` — initial VIBESegmentator segmentation

---

### Step 4 — Cleanup and IMAT Segmentation

1. Click **Cleanup Segments** — removes anatomically irrelevant labels, keeps: `Autochthon L/R`, `Iliopsoas L/R`, `Muscle`, `SAT`, `VAT`
2. Set the **IMAT Fat Threshold** (default: `100`, typical range: `80–130`)
3. Click **Create IMAT Segment** — detects intramuscular fat within the muscle region

---

### Step 5 — Correct VAT and IMAT (Manual Step)

Use the embedded **Segment Editor** to manually correct the VAT and IMAT segmentations:

- Click **Fat** to switch to the fat image — use this for correcting VAT and IMAT
- Click **Water** to switch to the water image — use this for correcting muscle
- Use the **Paint**, **Erase**, and **Logical Operators** tools

> **Why is this needed?** VIBESegmentator sometimes includes intra-abdominal organ tissue in the VAT segmentation. A brief manual correction (typically 2–5 minutes) ensures accurate results.

---

### Step 6 — Select the L3 Slice

Scroll through the axial slices in 3D Slicer to find the **L3 vertebral level** (identified by the characteristic butterfly shape of the vertebra).

Then click **Auto-detect from cursor** — this reads the current slice position and fills in the Z-index automatically.

> You can also type the Z-index manually if you know it.

---

### Step 7 — Compute Metrics and Open Dashboard

Click **Compute Metrics & Open Dashboard**.

This:
1. Saves the corrected segmentation as `seg_corrected.seg.nrrd`
2. Runs `compute_metrics.py` to calculate all body composition metrics
3. Exports results to `body_composition_results.csv`
4. Opens the **Panel dashboard** automatically in your browser

---

## Dashboard Overview

The dashboard has two views, switchable via the toggle at the top:

### Radiology View
- L3 axial slice with colour-coded segmentation overlays (SAT, VAT, Muscle, IMAT)
- Toggle individual tissue compartments on/off
- Z-slice navigation slider for visual quality control
- Metric cards with all body composition values
- Percentile comparison against Nowak et al. (2025) reference values — switchable between normal distribution curve and percentile bar

### Clinical View
- Metabolic profile: waist circumference, BMI (auto-calculated), VAT/SAT ratio
- Cardiovascular profile: blood pressure, SCORE2 risk category (ESC 2021)
  > The SCORE2 value must be calculated externally using the official ESC calculator and entered manually
- Patient data input fields
- Laboratory report integration (upload a KSW lab PDF — values are parsed automatically, abnormal findings highlighted in red)
- PDF export (role-specific report)

---

## Output Files

After running the pipeline, the following files are created inside the patient folder:

```
Anonym_Patient_0/
└── output/
    ├── nifti/
    │   ├── water.nii                    Water channel NIfTI
    │   ├── fat.nii                      Fat channel NIfTI
    │   ├── seg.nii.gz                   Initial segmentation
    │   └── seg_corrected.seg.nrrd       Corrected segmentation (after Step 5)
    ├── body_composition_results.csv     All computed metrics
    └── pipeline_log.txt                 Processing log with timing
```

---

## Troubleshooting

**Pipeline does not start / "python not found"**  
→ Check that `PYTHON_VIBE` in `run_pipeline.py` and `compute_metrics.py` points to the correct `python.exe`. Open Anaconda Prompt, activate the environment (`conda activate VIBESegmentator`), and type `where python` to find the correct path.

**"No Water folder found"**  
→ The pipeline could not automatically detect the water DICOM series. Check that your DICOM folder names contain the keyword `water` or end with `_W`.

**"No Fat folder found"**  
→ Check that your fat DICOM folder name ends with `_F` or contains `mDIXON` without `water`, `ip`, `op`, or `ff`.

**Dashboard does not open**  
→ Make sure the `panel` package is installed: open Anaconda Prompt, activate the environment, and run `pip install panel`.

**Segment Editor not visible in module**  
→ This can happen on some systems. Use **Modules → Segment Editor** directly in 3D Slicer as a workaround.

**IMAT shows 0 pixels**  
→ Try lowering the IMAT fat threshold (e.g. from `100` to `80`).

**VIBESegmentator fails with a CUDA error**  
→ If no GPU is available, open `run_pipeline.py` and change `--ddevice cuda` to `--ddevice cpu`. Processing will be slower but will still work.

---

## Semi-Automatic Workflow (Ilenia Giannini)

The semi-automatic workflow is located in `semi_automatic_pipeline/` and uses a separate 3D Slicer module:

```
semi_automatic_pipeline/
├── KSW_SemiAutomatic_BCW_module.py   3D Slicer module
└── dashboard.py                      Interactive Panel dashboard
```

This workflow is designed for Dixon MRI-based body composition analysis at the L3 vertebral level. It combines threshold-based segmentation, manual refinement, metric extraction, and dashboard export in one guided 3D Slicer interface.

In contrast to the automated workflow, the semi-automatic workflow does **not** use VIBESegmentator. The user manually selects the L3 slice and can directly refine the segmentation inside the embedded Segment Editor.

It supports:

* 2D isolated L3 slice datasets
* Radiologist-selected single-slice or reduced three-slice 3D datasets
* Full volumetric 3D Dixon MRI datasets processed in single-slice mode

---

## Setup — Semi-Automatic Workflow

### Step 1: Create the correct folder structure

Copy the files from `semi_automatic_pipeline/` into a folder on your computer, for example:

```
C:\KSW_SemiAutomatic\
    KSW_SemiAutomatic_BCW_module.py
    Dashboard\
        dashboard.py
        current_patient\
            output\
```

> The exact dashboard folder structure may already be included in the repository. The module automatically exports the metric CSV, image files, segmentation, and slice index files to the dashboard input folder.

### Step 2: Add the module to 3D Slicer

1. Open **3D Slicer**
2. Go to **Edit → Application Settings → Modules**
3. Under **Additional module paths**, click the ➕ button
4. Select the folder containing `KSW_SemiAutomatic_BCW_module.py`
5. Click **OK** and restart 3D Slicer
6. After restart, open the module under:

```
Modules → Segmentation → KSW Semi-automatic MRI Body Composition Workflow
```

> **Important:** The filename must remain `KSW_SemiAutomatic_BCW_module.py`, because 3D Slicer requires the filename and the main module class name to match.

---

## How to Use — Semi-Automatic Workflow (Step by Step)

### Step 1 — Load Dixon Fat and Water Images

In the **KSW Semi-automatic MRI Body Composition Workflow** module, load the required Dixon images:

* Click **Load Fat Image**
* Click **Load Water Image**

The module supports image files and DICOM folders, including:

* `.dcm`
* `.nrrd`
* `.nii`
* `.nii.gz`

The images are used as follows:

| Image       | Purpose                                              |
| ----------- | ---------------------------------------------------- |
| Fat image   | SAT, VAT, and IMAT segmentation                      |
| Water image | Muscle segmentation and manual anatomical correction |

The segmentation field can be left empty initially. The module creates the segmentation node automatically when needed.

---

### Step 2 — Enter Patient Information

Optionally enter:

* Patient name or patient ID
* Year of birth

Enter the patient height in metres.
The height is required for height-normalised metrics such as SMI, SAT Index, and VAT Index.

---

### Step 3 — Select Processing Mode

The module provides two processing modes:

#### 2D image mode

Use this mode for isolated single-slice L3 images.

In this mode, the first and only slice is used for segmentation and metric extraction.

Click:

```
Run automatic SAT/VAT segmentation
```

The module performs threshold-based SAT and VAT segmentation on the fat image. Muscle segmentation is then performed or refined manually using the embedded Segment Editor.

#### 3D single-slice mode

Use this mode for full volumetric Dixon MRI datasets.

1. Scroll to the desired L3 slice in the **Red slice viewer**
2. Click **Auto-detect**

The module reads the currently visible Red viewer slice and stores it as the shared workflow slice. This slice index is used for the fat image, water image, segmentation, metric calculation, and dashboard export.

> No automatic fat-water slice offset is applied.

The 3D workflow is performed step by step:

1. Click **Run SAT threshold**
2. Click **Edit SAT Segment** and correct SAT if needed
3. Click **Run VAT threshold + subtract SAT**
4. Correct VAT if needed using the Segment Editor
5. Click **Run Muscle threshold + clean fat overlap**
6. Click **Edit Muscle Segment** and refine Muscle manually
7. Adjust the IMAT threshold if needed
8. Click **Run automatic IMAT segmentation**
9. Click **Compute Metrics + Export to Dashboard**

---

### Step 4 — Manual Segmentation Refinement

The module contains an embedded **Segment Editor**, so manual corrections can be performed directly inside the workflow.

Recommended source images:

| Segment | Source image                                      |
| ------- | ------------------------------------------------- |
| SAT     | Fat image                                         |
| VAT     | Fat image                                         |
| Muscle  | Water image                                       |
| IMAT    | Fat image, with water image for anatomical review |

The Segment Editor can be used with standard tools such as **Paint**, **Erase**, and **Logical Operators**.

---

### Step 5 — IMAT Segmentation

IMAT is derived from fat-image intensities inside the corrected Muscle segment.

The recommended starting threshold is:

```
53–233
```

The threshold can be adjusted directly in the module before running IMAT segmentation.

Click:

```
Run automatic IMAT segmentation
```

The module thresholds the fat image on the selected L3 slice and keeps only pixels that overlap with the Muscle segment.

---

### Step 6 — Compute Metrics and Export

Click:

```
Compute Metrics + Export to Dashboard
```

The module computes the body composition metrics on the selected shared L3 slice.

Computed metrics include:

| Metric          | Description                                        |
| --------------- | -------------------------------------------------- |
| SAT area        | Subcutaneous adipose tissue area in cm²            |
| VAT area        | Visceral adipose tissue area in cm²                |
| SMA             | Skeletal muscle area in cm²                        |
| IMAT area       | Intramuscular adipose tissue area in cm²           |
| IMAT percentage | IMAT area relative to skeletal muscle area         |
| VAT/SAT ratio   | Ratio of visceral to subcutaneous adipose tissue   |
| SMI             | Skeletal Muscle Index, calculated as SMA / height² |
| SAT Index       | SAT area normalised by height²                     |
| VAT Index       | VAT area normalised by height²                     |

> The workflow is slice-based. For 3D datasets, only the selected L3 slice is quantified, not the full 3D volume.

---

### Step 7 — Open Dashboard

After the export is complete, click:

```
Open Dashboard
```

The Panel dashboard opens in the browser and displays:

* L3 image overlays
* SAT, VAT, Muscle, and IMAT segmentations
* Metric cards
* Percentile visualisations
* Clinical input fields
* PDF report export

---

## Output Files — Semi-Automatic Workflow

After metric export, the semi-automatic workflow creates dashboard-compatible output files:

```
Dashboard/
└── current_patient/
    └── output/
        ├── nifti/
        │   ├── fat.nii
        │   ├── water.nii
        │   └── seg_corrected.seg.nrrd
        ├── body_composition_results.csv
        ├── slice_index.txt
        └── dashboard_start_slice.txt
```

The main metric file is:

```
body_composition_results.csv
```

Typical columns include:

```
sat_cm2
vat_cm2
sma_cm2
imat_cm2
imat_pct
vat_sat_ratio
smi
sat_index
vat_index
height_m
patient_id
patient_name
birth_year
slice_index
water_slice_index
fat_slice_index
```

For datasets with only a small number of slices, the module may copy the selected image slice and the corresponding segmentation to a dashboard-compatible display position. This is only an export adjustment for correct dashboard visualisation and does not change the segmentation workflow.

---

## Troubleshooting — Semi-Automatic Workflow

**Module does not appear in 3D Slicer**
→ Check that the folder containing `KSW_SemiAutomatic_BCW_module.py` was added under **Edit → Application Settings → Modules** and that 3D Slicer was restarted.

**Module fails to load**
→ Make sure the filename is exactly `KSW_SemiAutomatic_BCW_module.py`. The filename and the main module class name must match.

**Fat or water image is not loaded correctly**
→ Try loading the image as an image file instead of a DICOM folder, or check that the selected DICOM folder contains only the intended fat or water series.

**Muscle segment is empty**
→ Check that the correct water image is selected and that the L3 slice index corresponds to the visible Red slice.

**IMAT shows 0 pixels**
→ Check that the Muscle segment exists on the selected L3 slice and adjust the IMAT threshold values. The recommended starting range is `53–233`.

**Dashboard does not open**
→ First run **Compute Metrics + Export to Dashboard**. The dashboard requires the exported CSV, image files, segmentation, and slice index files.

---

## Notes and Limitations — Semi-Automatic Workflow

* The workflow is slice-based.
* In 3D mode, only the selected L3 slice is segmented and quantified.
* The workflow does not perform full-volume body composition analysis.
* Threshold values are dataset-specific and may require adaptation for different scanners, Dixon sequences, or intensity scalings.
* Manual correction is still required, especially for heterogeneous MRI datasets or reduced anatomical coverage.
* The module is a research prototype and must not be used for clinical decision-making without further validation.
* The workflow does not replace radiological review.

---

## Authors

| Name | Role | Institution |
|------|------|-------------|
| Luca Meier | Automated pipeline, dashboard, metrics | ZHAW Wädenswil |
| Ilenia Giannini | Semi-automatic pipeline, experimental NiceGUI comparison prototype | ZHAW Wädenswil |

**Supervisors:**  
Dr. Norman Juchler (ZHAW) · Dr. Dr. Georg Spinner (ZHAW) · Prof. Dr. med. Roman Guggenberger (KSW) · PD Dr. med. Tim Fischer (KSW) · Dr. med. Oliver Boss (KSW)

---

## License

This project was developed as part of a Bachelor's thesis at ZHAW. The code is provided for research and educational purposes only.

Note: **VIBESegmentator** is a third-party tool with its own license. Check [github.com/robert-graf/VIBESegmentator](https://github.com/robert-graf/VIBESegmentator) before any commercial use.
