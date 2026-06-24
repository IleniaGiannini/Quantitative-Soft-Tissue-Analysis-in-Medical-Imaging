from __future__ import annotations

"""
NiceGUI dashboard prototype for the Bachelor thesis body-composition workflow.

The dashboard loads images and segmentation masks exported by the 3D Slicer
module, computes single-slice L3 body-composition metrics, visualizes the
results, and generates a simple PDF report. The implementation is intentionally
kept as a prototype and is not intended for clinical diagnosis.
"""

from pathlib import Path
from typing import Any
from time import time

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import numpy as np
from nicegui import ui
from report import create_pdf_report

from io_utils import (
    extract_2d_slice,
    get_pixel_area_cm2,
    load_nrrd,
)
from metrics import (
    compute_area_cm2,
    compute_index,
    compute_muscle_to_fat_ratio,
    compute_smi,
    compute_vat_sat_ratio,
)

# Folder for generated plots, uploaded lab PDFs, and PDF reports.
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Folder expected to contain the export files written by the 3D Slicer module.
AUTO_INPUT_DIR = Path(__file__).parent / "input"
AUTO_INPUT_DIR.mkdir(exist_ok=True)

state: dict[str, Any] = {
    "image_path": None,
    "seg_path": None,
    "image_data": None,
    "image_header": None,
    "seg_data": None,
    "seg_header": None,
    "segment_info": None,
    "results": None,
    "sat_mask_data": None,
    "vat_mask_data": None,
    "muscle_mask_data": None,
    "slice_index": 0,
    "imat_mask_data": None,
    "visible_segments": {"SAT": True, "VAT": True, "Muscle": True, "IMAT": True},
    "user_role": "clinical",
    "lab_table": None,
    "lab_pdf_path": None,
    "water_image_data": None,
    "water_image_header": None,
    "display_image_type": "fat",
}


def normalize_for_display(image_2d: np.ndarray) -> np.ndarray:
    image_2d = image_2d.astype(float)
    min_val = np.min(image_2d)
    max_val = np.max(image_2d)
    if max_val == min_val:
        return np.zeros_like(image_2d, dtype=float)
    return (image_2d - min_val) / (max_val - min_val)


def create_overlay_plot(image_2d: np.ndarray, masks: dict[str, np.ndarray], output_path: Path, image_title: str = "Image",) -> None:
    sat_mask = masks.get("SAT")
    vat_mask = masks.get("VAT")
    muscle_mask = masks.get("Muscle")
    imat_mask = masks.get("IMAT")

    overlay = np.zeros(image_2d.shape, dtype=np.uint8)

    if sat_mask is not None:
        overlay[sat_mask] = 1
    if vat_mask is not None:
        overlay[vat_mask] = 2
    if muscle_mask is not None:
        overlay[muscle_mask] = 3
    if imat_mask is not None:
        overlay[imat_mask] = 4

    colors = [
        (0, 0, 0, 0.0),
        (1, 0, 0, 0.35),      # SAT
        (0, 1, 0, 0.35),      # VAT
        (0, 0, 1, 0.35),      # Muscle
        (1, 0, 1, 0.55),      # IMAT
    ]
    cmap = ListedColormap(colors)

    plt.figure(figsize=(8, 8))
    plt.imshow(image_2d, cmap="gray")
    plt.imshow(overlay, cmap=cmap, interpolation="none")

    if sat_mask is not None and np.any(sat_mask):
        plt.contour(sat_mask, levels=[0.5], colors="red", linewidths=1)
    if vat_mask is not None and np.any(vat_mask):
        plt.contour(vat_mask, levels=[0.5], colors="lime", linewidths=1)
    if muscle_mask is not None and np.any(muscle_mask):
        plt.contour(muscle_mask, levels=[0.5], colors="cyan", linewidths=1)
    if imat_mask is not None and np.any(imat_mask):
        plt.contour(imat_mask, levels=[0.5], colors="magenta", linewidths=1)

    legend_handles = []
    if sat_mask is not None and np.any(sat_mask):
        legend_handles.append(mpatches.Patch(color="red", label="SAT"))
    if vat_mask is not None and np.any(vat_mask):
        legend_handles.append(mpatches.Patch(color="lime", label="VAT"))
    if muscle_mask is not None and np.any(muscle_mask):
        legend_handles.append(mpatches.Patch(color="blue", label="Muscle"))
    if imat_mask is not None and np.any(imat_mask):
        legend_handles.append(mpatches.Patch(color="magenta", label="IMAT"))

    if legend_handles:
        plt.legend(handles=legend_handles, loc="lower right")

    plt.title(f"{image_title} with segmentation overlay")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", pad_inches=0.05)
    plt.close()


def format_metric(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"

def classify_score2(score2_value: float | None, age: int) -> tuple[str, str]:
    """
    Returns SCORE2 risk category and color.
    """

    if score2_value is None or age is None:
        return "N/A", "#d9d9d9"

    # <50 years
    if age < 50:
        if score2_value < 2.5:
            return "Low risk", "#4CAF50"
        elif score2_value < 7.5:
            return "Increased risk", "#FF9800"
        else:
            return "High risk", "#D32F2F"

    # 50-69 years
    elif age < 70:
        if score2_value < 5:
            return "Low risk", "#4CAF50"
        elif score2_value < 10:
            return "Increased risk", "#FF9800"
        else:
            return "High risk", "#D32F2F"

    # >=70 years
    else:
        if score2_value < 7.5:
            return "Low risk", "#4CAF50"
        elif score2_value < 15:
            return "Increased risk", "#FF9800"
        else:
            return "High risk", "#D32F2F"

def load_auto_inputs() -> None:
    fat_path = AUTO_INPUT_DIR / "fat_image.nrrd"
    water_path = AUTO_INPUT_DIR / "water_image.nrrd"
    sat_path = AUTO_INPUT_DIR / "SAT_mask.nrrd"
    vat_path = AUTO_INPUT_DIR / "VAT_mask.nrrd"
    muscle_path = AUTO_INPUT_DIR / "Muscle_mask.nrrd"
    imat_path = AUTO_INPUT_DIR / "IMAT_mask.nrrd"
    slice_index_path = AUTO_INPUT_DIR / "slice_index.txt"

    if slice_index_path.exists():
        with open(slice_index_path, "r") as f:
            state["slice_index"] = int(f.read().strip())
    else:
        state["slice_index"] = 0

    print("L3 slice index:", state["slice_index"])

    for path in [fat_path, sat_path, vat_path, muscle_path, imat_path]:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

    image_data, image_header = load_nrrd(fat_path)
    water_data, water_header = load_nrrd(water_path) if water_path.exists() else (None, None)
    sat_data, _ = load_nrrd(sat_path)
    vat_data, _ = load_nrrd(vat_path)
    muscle_data, _ = load_nrrd(muscle_path)
    imat_data, _ = load_nrrd(imat_path)


    state["image_path"] = str(fat_path)
    state["image_data"] = image_data
    state["image_header"] = image_header

    state["water_image_data"] = water_data
    state["water_image_header"] = water_header
    state["sat_mask_data"] = sat_data > 0
    state["vat_mask_data"] = vat_data > 0
    state["muscle_mask_data"] = muscle_data > 0
    state["imat_mask_data"] = imat_data > 0

    print("AUTO INPUTS LOADED")
    print("Fat image:", fat_path, image_data.shape)
    print("SAT mask:", sat_path, sat_data.shape)
    print("VAT mask:", vat_path, vat_data.shape)
    print("Muscle mask:", muscle_path, muscle_data.shape)
    print("IMAT mask:", imat_path, imat_data.shape)

def create_distribution_plot(
    value: float | None,
    mean: float,
    std: float,
    label: str,
    unit: str,
    output_path: Path,
) -> None:
    x = np.linspace(mean - 4 * std, mean + 4 * std, 1000)

    y = (
        1 / (std * np.sqrt(2 * np.pi))
        * np.exp(-0.5 * ((x - mean) / std) ** 2)
    )

    fig, ax = plt.subplots(figsize=(6, 3))

    ax.plot(x, y, linewidth=2)

    ax.fill_between(
        x,
        y,
        where=((x >= mean - std) & (x <= mean + std)),
        alpha=0.3,
    )

    if value is not None:
        patient_y = (
            1 / (std * np.sqrt(2 * np.pi))
            * np.exp(-0.5 * ((value - mean) / std) ** 2)
        )

        ax.axvline(value, linestyle="--")
        ax.plot(value, patient_y, marker="o", markersize=9)
        ax.text(value, patient_y, f" {value:.2f}", fontsize=9)

    ax.set_title(f"{label} reference distribution")
    ax.set_xlabel(unit)
    ax.set_ylabel("Density")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

def run_analysis(
    height_m: float,
    weight_kg: float | None,
    waist_cm: float | None,
    sex: str | None,
    age: int | None,
    score2_value: float | None,
    liver_fat_fraction: float | None,
    slice_index: int = 0,
) -> dict[str, Any]:

    pixel_area_cm2 = get_pixel_area_cm2(state["image_header"])

    if state.get("display_image_type") == "water" and state.get("water_image_data") is not None:
        image = state["water_image_data"]
        results_image_type = "Water image"
    else:
        image = state["image_data"]
        results_image_type = "Fat image"

    sat_mask = state["sat_mask_data"]
    vat_mask = state["vat_mask_data"]
    muscle_mask = state["muscle_mask_data"]
    imat_mask = state["imat_mask_data"]

    if image is not None and image.ndim == 3:
        image_2d = image[:, :, slice_index]
    else:
        image_2d = extract_2d_slice(image)

    if sat_mask is not None and sat_mask.ndim == 3:
        sat_mask = sat_mask[:, :, slice_index]

    if vat_mask is not None and vat_mask.ndim == 3:
        vat_mask = vat_mask[:, :, slice_index]

    if muscle_mask is not None and muscle_mask.ndim == 3:
        muscle_mask = muscle_mask[:, :, slice_index]

    if imat_mask is not None and imat_mask.ndim == 3:
        imat_mask = imat_mask[:, :, slice_index]

    results: dict[str, Any] = {
        "pixel_area_cm2": pixel_area_cm2,
        "available_segments": ["SAT", "VAT", "Muscle", "IMAT"],
        "height_m": height_m,
        "sex": sex,
        "age": age,
        "slice_index": slice_index,
        "user_role": state.get("user_role", "clinical"),
        "display_image_type": results_image_type,
    }

    results["weight_kg"] = weight_kg
    results["waist_cm"] = waist_cm
    results["bmi"] = (weight_kg / (height_m ** 2) if weight_kg is not None and height_m > 0 else None)

    score2_category, score2_color = classify_score2(score2_value, age)
    results["score2"] = score2_value
    results["score2_category"] = score2_category
    results["score2_color"] = score2_color
    results["liver_fat_fraction"] = liver_fat_fraction

    results["muscle_area_cm2"] = (
        compute_area_cm2(muscle_mask, pixel_area_cm2) if muscle_mask is not None else None
    )
    results["sat_area_cm2"] = (
        compute_area_cm2(sat_mask, pixel_area_cm2) if sat_mask is not None else None
    )
    results["vat_area_cm2"] = (
        compute_area_cm2(vat_mask, pixel_area_cm2) if vat_mask is not None else None
    )
    results["imat_area_cm2"] = (
        compute_area_cm2(imat_mask, pixel_area_cm2) if imat_mask is not None else None
    )

    if results["vat_area_cm2"] is not None and results["sat_area_cm2"] is not None:
        results["vat_sat_ratio"] = compute_vat_sat_ratio(
            results["vat_area_cm2"], results["sat_area_cm2"]
        )
    else:
        results["vat_sat_ratio"] = None

    if results["muscle_area_cm2"] is not None:
        results["smi"] = compute_smi(results["muscle_area_cm2"], height_m)
    else:
        results["smi"] = None

    results["sat_index"] = (
        compute_index(results["sat_area_cm2"], height_m)
        if results["sat_area_cm2"] is not None
        else None
    )

    results["vat_index"] = (
        compute_index(results["vat_area_cm2"], height_m)
        if results["vat_area_cm2"] is not None
        else None
    )

    if (
        results["muscle_area_cm2"] is not None
        and results["sat_area_cm2"] is not None
        and results["vat_area_cm2"] is not None
    ):
        results["muscle_to_fat_ratio"] = compute_muscle_to_fat_ratio(
            results["muscle_area_cm2"],
            results["sat_area_cm2"],
            results["vat_area_cm2"],
        )
    else:
        results["muscle_to_fat_ratio"] = None

    if (
        results["imat_area_cm2"] is not None
        and results["muscle_area_cm2"] is not None
        and results["muscle_area_cm2"] > 0
    ):
        results["imat_percent"] = (
            results["imat_area_cm2"] / results["muscle_area_cm2"] * 100
        )
    else:
        results["imat_percent"] = None

    if sex == "female":
        smi_low = 35.0
        smi_high = 45.0
        smi_mean = 40.0
    else:
        smi_low = 43.0
        smi_high = 55.0
        smi_mean = 50.0

    results["smi_reference_low"] = smi_low
    results["smi_reference_high"] = smi_high

    if results["smi"] is None:
        results["smi_category"] = "N/A"
    elif results["smi"] < smi_low:
        results["smi_category"] = "low"
    elif results["smi"] > smi_high:
        results["smi_category"] = "high"
    else:
        results["smi_category"] = "reference range"


    # ---------- Normal distribution plots ----------
    distribution_specs = {
        "smi": {
            "value": results["smi"],
            "mean": smi_mean,
            "std": 5,
            "label": "SMI",
            "unit": "cm²/m²",
        },
        "sat_index": {
            "value": results["sat_index"],
            "mean": 90,
            "std": 30,
            "label": "SAT index",
            "unit": "cm²/m²",
        },
        "vat_index": {
            "value": results["vat_index"],
            "mean": 50,
            "std": 25,
            "label": "VAT index",
            "unit": "cm²/m²",
        },
        "vat_sat_ratio": {
            "value": results["vat_sat_ratio"],
            "mean": 0.7,
            "std": 0.3,
            "label": "VAT/SAT ratio",
            "unit": "ratio",
        },
        "imat_percent": {
            "value": results["imat_percent"],
            "mean": 10,
            "std": 5,
            "label": "IMAT",
            "unit": "%",
        },
        "muscle_to_fat_ratio": {
            "value": results["muscle_to_fat_ratio"],
            "mean": 0.4,
            "std": 0.15,
            "label": "Muscle-to-fat ratio",
            "unit": "ratio",
        },
    }

    results["distribution_plots"] = {}

    for key, spec in distribution_specs.items():
        plot_path = UPLOAD_DIR / f"{key}_distribution_{int(time() * 1000)}.png"

        create_distribution_plot(
            value=spec["value"],
            mean=spec["mean"],
            std=spec["std"],
            label=spec["label"],
            unit=spec["unit"],
            output_path=plot_path,
        )

        results["distribution_plots"][key] = str(plot_path)


    # ---------- Overlay ----------
    visible = state.get("visible_segments", {})

    overlay_masks = {}

    if visible.get("Muscle", True) and muscle_mask is not None:
        overlay_masks["Muscle"] = muscle_mask

    if visible.get("SAT", True) and sat_mask is not None:
        overlay_masks["SAT"] = sat_mask

    if visible.get("VAT", True) and vat_mask is not None:
        overlay_masks["VAT"] = vat_mask

    if visible.get("IMAT", True) and imat_mask is not None:
        overlay_masks["IMAT"] = imat_mask

    overlay_path = UPLOAD_DIR / f"overlay_{int(time() * 1000)}.png"
    create_overlay_plot(image_2d, overlay_masks, overlay_path, results_image_type)
    results["overlay_path"] = str(overlay_path)

    raw_path = UPLOAD_DIR / f"raw_{int(time() * 1000)}.png"
    plt.figure(figsize=(6, 6))
    plt.imshow(normalize_for_display(image_2d), cmap="gray")
    plt.title(results_image_type)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(raw_path, bbox_inches="tight", pad_inches=0.05)
    plt.close()
    results["raw_path"] = str(raw_path)

    return results

def metric_bar(
    label: str,
    value: float | None,
    max_value: float,
    unit: str = "",
):
    if value is None:
        return

    normalized = min(max(value / max_value, 0), 1)

    with ui.card().classes("w-full"):
        ui.label(label).classes("text-subtitle2")

        ui.linear_progress(
            value=normalized
        ).classes("w-full")

        ui.label(f"{value:.2f} {unit}")

def update_visible_segments() -> None:
    if state["results"] is None:
        return

    state["visible_segments"] = {
        "SAT": result_sat_checkbox.value,
        "VAT": result_vat_checkbox.value,
        "Muscle": result_muscle_checkbox.value,
        "IMAT": result_imat_checkbox.value,
    }

    r = state["results"]

    state["results"] = run_analysis(
        height_m=r["height_m"],
        weight_kg=r["weight_kg"],
        waist_cm=r["waist_cm"],
        sex=r["sex"],
        age=r["age"],
        score2_value=r["score2"],
        liver_fat_fraction=r.get("liver_fat_fraction"),
        slice_index=r["slice_index"],
    )
    
    results_view.refresh()

def update_display_image(e):
    if state["results"] is None:
        return
    
    state["display_image_type"] = e.value

    r = state["results"]
    state["results"] = run_analysis(
        height_m=r["height_m"],
        weight_kg=r["weight_kg"],
        waist_cm=r["waist_cm"],
        sex=r["sex"],
        age=r["age"],
        score2_value=r["score2"],
        liver_fat_fraction=r.get("liver_fat_fraction"),
        slice_index=r["slice_index"],
    )

    results_view.refresh()

@ui.refreshable
def results_view() -> None:
    results = state["results"]
    role = state.get("user_role", "clinical")

    if results is None:
        ui.label("No results yet.")
        return

    with ui.card().classes("w-full mt-4"):
        ui.label("Visible segments").classes("text-subtitle1")

        visible = state.get("visible_segments", {})

        with ui.row().classes("gap-4"):
            global result_sat_checkbox, result_vat_checkbox, result_muscle_checkbox, result_imat_checkbox

            result_sat_checkbox = ui.checkbox(
                "SAT",
                value=visible.get("SAT", True),
                on_change=update_visible_segments,
            )

            result_vat_checkbox = ui.checkbox(
                "VAT",
                value=visible.get("VAT", True),
                on_change=update_visible_segments,
            )

            result_muscle_checkbox = ui.checkbox(
                "Muscle",
                value=visible.get("Muscle", True),
                on_change=update_visible_segments,
            )

            result_imat_checkbox = ui.checkbox(
                "IMAT",
                value=visible.get("IMAT", True),
                on_change=update_visible_segments,
            )

    with ui.card().classes("w-full mt-4"):
        ui.label("Image display").classes("text-subtitle1")

        ui.select(
            options={
                "fat": "Fat image",
                "water": "Water image",
            },
            value=state.get("display_image_type", "fat"),
            label="Displayed image",
            on_change=update_display_image,
        ).classes("w-60")

    with ui.row().classes("w-full items-start gap-8"):
        with ui.column():
            ui.label(results.get("display_image_type", "Image")).classes("text-subtitle1")
            ui.image(results["raw_path"]).classes("w-80 border")

        with ui.column():
            ui.label(f'Segmentation overlay on {results.get("display_image_type", "image")}').classes("text-subtitle1")
            ui.image(results["overlay_path"]).classes("w-80 border")

    if role == "clinical":

        with ui.card().classes("w-full mt-4"):
            ui.label("Clinical summary").classes("text-h6")

            with ui.card().classes("w-80 mt-4 p-4").style(
                f"background-color: {results['score2_color']}; color: white;"
            ):
                ui.label("Cardiovascular risk in the next 10 years").classes("text-subtitle1 font-bold")
                ui.label(f"SCORE2: {format_metric(results['score2'], 1)} %").classes("text-h5")
                ui.label(results["score2_category"]).classes("text-subtitle2")

    elif role == "radiologist":

        with ui.card().classes("w-full mt-4"):
            ui.label("Radiology information").classes("text-h6")

            ui.label(f'L3 slice index: {results.get("slice_index", "N/A")}')
            ui.label(f'Pixel area: {format_metric(results["pixel_area_cm2"], 4)} cm²')
            ui.label(f'Available segments: {", ".join(results["available_segments"])}')
            ui.label(f'Liver fat fraction: {format_metric(results.get("liver_fat_fraction"), 1)} %')

    with ui.row().classes("w-full gap-4 mt-4 wrap"):
        with ui.card():
            ui.label("SAT area")
            ui.label(f'{format_metric(results["sat_area_cm2"])} cm²').classes("text-h6")

        with ui.card():
            ui.label("VAT area")
            ui.label(f'{format_metric(results["vat_area_cm2"])} cm²').classes("text-h6")

        with ui.card():
            ui.label("SAT index")
            ui.label(f'{format_metric(results["sat_index"])} cm²/m²').classes("text-h6")

        with ui.card():
            ui.label("VAT index")
            ui.label(f'{format_metric(results["vat_index"])} cm²/m²').classes("text-h6")
        
        with ui.card():
            ui.label("VAT/SAT ratio")
            ui.label(format_metric(results["vat_sat_ratio"])).classes("text-h6")

        with ui.card():
            ui.label("SMI")
            ui.label(f'{format_metric(results["smi"])} cm²/m²').classes("text-h6")
        
        with ui.card():
            ui.label("SMA")
            ui.label(f'{format_metric(results["muscle_area_cm2"])} cm²').classes("text-h6")

        with ui.card():
            ui.label("Muscle-to-fat ratio")
            ui.label(format_metric(results["muscle_to_fat_ratio"])).classes("text-h6")

        with ui.card():
            ui.label("IMAT area")
            ui.label(f'{format_metric(results["imat_area_cm2"])} cm²').classes("text-h6")

        with ui.card():
            ui.label("IMAT")
            ui.label(f'{format_metric(results["imat_percent"])} %').classes("text-h6")

    metric_rows = [
        {"Metric": "SAT area", "Value": format_metric(results["sat_area_cm2"]), "Unit": "cm²"},
        {"Metric": "VAT area", "Value": format_metric(results["vat_area_cm2"]), "Unit": "cm²"},
        {"Metric": "Muscle area / SMA", "Value": format_metric(results["muscle_area_cm2"]), "Unit": "cm²"},
        {"Metric": "SMI", "Value": format_metric(results["smi"]), "Unit": "cm²/m²"},
        {"Metric": "VAT/SAT ratio", "Value": format_metric(results["vat_sat_ratio"]), "Unit": ""},
        {"Metric": "IMAT area", "Value": format_metric(results["imat_area_cm2"]), "Unit": "cm²"},
        {"Metric": "IMAT", "Value": format_metric(results["imat_percent"]), "Unit": "%"},
    ]

    with ui.card().classes("mt-4 w-full"):
        ui.label("Metrics table").classes("text-subtitle1")

        ui.table(
            columns=[
                {"name": "Metric", "label": "Metric", "field": "Metric"},
                {"name": "Value", "label": "Value", "field": "Value"},
                {"name": "Unit", "label": "Unit", "field": "Unit"},
            ],
            rows=metric_rows,
        ).classes("w-full")

    with ui.card().classes("mt-4 w-full"):
        ui.label("Metric distributions").classes("text-subtitle1")

        metric_bar(
            "SMI",
            results["smi"],
            max_value=70,
            unit="cm²/m²"
        )

        metric_bar(
            "VAT/SAT ratio",
            results["vat_sat_ratio"],
            max_value=3,
        )

        metric_bar(
            "IMAT",
            results["imat_percent"],
            max_value=30,
            unit="%"
        )

    with ui.card().classes("mt-4 w-full"):
        ui.label("Normal distribution plots").classes("text-subtitle1")

        plots = results.get("distribution_plots", {})

        with ui.row().classes("w-full gap-4 wrap"):
            for title, key in [
                ("SMI", "smi"),
                ("SAT index", "sat_index"),
                ("VAT index", "vat_index"),
                ("VAT/SAT ratio", "vat_sat_ratio"),
                ("IMAT", "imat_percent"),
                ("Muscle-to-fat ratio", "muscle_to_fat_ratio"),
            ]:
                if key in plots:
                    with ui.card():
                        ui.label(title).classes("text-subtitle2")
                        ui.image(plots[key]).classes("w-80")


        
def on_load_from_slicer() -> None:
    try:
        load_auto_inputs()
        ui.notify("Files loaded from 3D Slicer export.")
    except Exception as e:
        print("ERROR in on_load_from_slicer:", e)
        ui.notify(f"Error: {e}", type="negative")


def on_calculate() -> None:
    try:
        load_auto_inputs()

        slice_index = int(state.get("slice_index", 0))

        height_m = (
            float(str(height_input.value).replace(",", "."))
            if str(height_input.value).strip() != ""
            else None
        )

        weight_kg = (
            float(str(weight_input.value).replace(",", "."))
            if str(weight_input.value).strip() != ""
            else None
        )

        waist_cm = (
            float(str(waist_input.value).replace(",", "."))
            if str(waist_input.value).strip() != ""
            else None
        )

        score2_value = (
            float(str(score2_input.value).replace(",", "."))
            if str(score2_input.value).strip() != ""
            else None
        )
        liver_fat_fraction = (
            float(str(liver_fat_input.value).replace(",", "."))
            if str(liver_fat_input.value).strip() != ""
            else None
        )
        
        age = (
            int(float(str(age_input.value).replace(",", ".")))
            if str(age_input.value).strip() != ""
            else None
        )

        sex = str(sex_select.value).lower() if sex_select.value else None

        if height_m is None or height_m <= 0:
            raise ValueError("Height is required and must be greater than 0.")

        if weight_kg is not None and weight_kg <= 0:
            raise ValueError("Weight must be greater than 0.")

        if waist_cm is not None and waist_cm <= 0:
            raise ValueError("Waist circumference must be greater than 0.")

        if age is not None and age <= 0:
            raise ValueError("Age must be greater than 0.")

        if sex is not None and sex not in {"female", "male"}:
            raise ValueError("Please select a valid sex.")

        state["user_role"] = role_select.value
        
        state["results"] = run_analysis(
            height_m=height_m,
            weight_kg=weight_kg,
            waist_cm=waist_cm,
            sex=sex,
            age=age,
            score2_value=score2_value,
            liver_fat_fraction=liver_fat_fraction,
            slice_index=slice_index,
        )
        results_view.refresh()
        ui.notify("Analysis completed.")

    except Exception as e:
        print("ERROR in on_calculate:", e)
        ui.notify(f"Error: {e}", type="negative")


def download_pdf() -> None:
    if state["results"] is None:
        ui.notify("No results to export.", type="warning")
        return

    pdf_path = UPLOAD_DIR / "report.pdf"
    create_pdf_report(str(pdf_path), state["results"])
    ui.download(str(pdf_path))


@ui.refreshable
def lab_table_view():
    rows = state.get("lab_table")

    if not rows:
        ui.label("No lab data uploaded yet.")
        return

    columns = [
        {
            "name": key,
            "label": key,
            "field": key,
        }
        for key in rows[0].keys()
    ]

    ui.table(
        columns=columns,
        rows=rows,
        pagination=10,
    ).classes("w-full")


def on_lab_pdf_upload(e):
    """Handle optional laboratory PDF upload and extract tables if possible."""
    try:
        try:
            import pdfplumber
        except ImportError as exc:
            raise ImportError(
                "The optional dependency 'pdfplumber' is required for lab PDF uploads. "
                "Install it with: pip install pdfplumber"
            ) from exc

        lab_dir = UPLOAD_DIR / "lab_data"
        lab_dir.mkdir(exist_ok=True)

        # NiceGUI versions differ slightly: some provide e.name, others e.names.
        uploaded_name = getattr(e, "name", None)
        if uploaded_name is None and getattr(e, "names", None):
            uploaded_name = e.names[0]
        if uploaded_name is None:
            uploaded_name = "lab_report.pdf"

        pdf_path = lab_dir / Path(uploaded_name).name

        with open(pdf_path, "wb") as f:
            f.write(e.content.read() if hasattr(e.content, "read") else e.content)

        rows = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()

                for table in tables:
                    if not table:
                        continue

                    header = table[0]
                    data = table[1:]

                    for row in data:
                        rows.append(dict(zip(header, row)))

        if not rows:
            raise ValueError("No table could be extracted from the PDF.")

        state["lab_pdf_path"] = str(pdf_path)
        state["lab_table"] = rows

        lab_table_view.refresh()
        ui.notify("Lab PDF uploaded and table extracted.")

    except Exception as e:
        print("ERROR in lab PDF upload:", e)
        ui.notify(f"Error: {e}", type="negative")


ui.page_title("Body Composition Dashboard")

with ui.column().classes("w-full max-w-5xl mx-auto p-6"):
    ui.label("Body Composition Analysis").classes("text-h4")
    ui.label("Data are loaded automatically from 3D Slicer export folder.")

    with ui.card().classes("w-full mt-4"):
        ui.label("Dashboard mode").classes("text-h6")

        role_select = ui.select(
            options={
                "clinical": "Clinical user",
                "radiologist": "Radiologist",
            },
            value="clinical",
            label="User role",
        ).classes("w-60")
    
    with ui.card().classes("w-full mt-4"):
        ui.label("Patient information").classes("text-h6")

        with ui.row().classes("items-end gap-4 mt-4"):
            height_input = ui.input("Height (m)", value="") \
                .props("type=number step=0.01") \
                .classes("w-40")

            weight_input = ui.input("Weight (kg)", value="") \
                .props("type=number step=0.1 min=1") \
                .classes("w-40")

            bmi_label = ui.label("BMI: N/A").classes("w-40 text-subtitle2")

            def update_bmi_label():
                try:
                    h = float(str(height_input.value).replace(",", "."))
                    w = float(str(weight_input.value).replace(",", "."))
                    bmi = w / (h ** 2)
                    bmi_label.text = f"BMI: {bmi:.1f} kg/m²"
                except Exception:
                    bmi_label.text = "BMI: N/A kg/m²"

            height_input.on_value_change(lambda e: update_bmi_label())
            weight_input.on_value_change(lambda e: update_bmi_label())
            update_bmi_label()

            waist_input = ui.input("Waist circumference (cm)", value="") \
                .props("type=number step=0.1 min=1") \
                .classes("w-48")

            age_input = ui.input("Age (years)", value="") \
                .props("type=number step=1 min=18") \
                .classes("w-40")

            sex_select = ui.select(
                options=["female", "male"],
                value=None,
                label="Sex",
            ).classes("w-40")

            score2_input = ui.input(
                "SCORE2 (%)",
                value=""
            ).props("type=number step=0.1").classes("w-40")

            liver_fat_input = ui.input("Liver fat fraction (%)", value="") \
                .props("type=number step=0.1 min=0") \
                .classes("w-48")

        with ui.row().classes("gap-4 mt-4"):
            ui.button("Load from 3D Slicer", on_click=on_load_from_slicer)
            ui.button("Calculate Metrics", on_click=on_calculate)

    with ui.card().classes("w-full mt-4"):
        ui.label("Laboratory data").classes("text-h6")
        ui.label("Upload a lab report PDF. Extracted values will be displayed in a table.")

        ui.upload(
            label="Upload laboratory PDF",
            on_upload=on_lab_pdf_upload,
            auto_upload=True,
        ).props("accept=.pdf")

        lab_table_view()

    with ui.card().classes("w-full mt-6"):
        ui.label("Results").classes("text-h6")
        results_view()
        ui.button("Download PDF Report", on_click=download_pdf).classes("mt-4")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host="0.0.0.0",
        port=8080,
        reload=False,
        show=False
    )