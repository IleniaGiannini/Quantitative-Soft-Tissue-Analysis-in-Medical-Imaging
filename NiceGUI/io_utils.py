from __future__ import annotations

from pathlib import Path
from typing import Any

import nrrd
import numpy as np


def load_nrrd(file_path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Load a NRRD file and remove singleton dimensions."""
    data, header = nrrd.read(str(file_path))
    data = np.asarray(np.squeeze(data))
    return data, header


def get_segment_info(seg_header: dict[str, Any]) -> dict[str, dict[str, int]]:
    """
    Read segment names from a .seg.nrrd header.

    Returns a dict like:
    {
        "Muscle": {"index": 0, "layer": 0, "label_value": 1},
        "SAT": {"index": 1, "layer": 0, "label_value": 1},
        ...
    }
    """
    segment_info: dict[str, dict[str, int]] = {}
    i = 0

    while f"Segment{i}_Name" in seg_header:
        name = str(seg_header[f"Segment{i}_Name"])
        layer = int(seg_header.get(f"Segment{i}_Layer", 0))
        label_value = int(seg_header.get(f"Segment{i}_LabelValue", 1))

        segment_info[name] = {
            "index": i,
            "layer": layer,
            "label_value": label_value,
        }
        i += 1

    return segment_info


def extract_2d_slice(image: np.ndarray, slice_index: int | None = None) -> np.ndarray:
    """
    Convert an image array to one 2D slice for display/calculation.

    - 2D input: returned unchanged
    - 3D input: selected slice along the last axis
    - if no slice index is provided, the middle slice is used
    """
    if image.ndim == 2:
        return image

    if image.ndim == 3:
        if slice_index is None:
            slice_index = image.shape[2] // 2
        return image[:, :, slice_index]

    raise ValueError(f"Unsupported image shape for slice extraction: {image.shape}")



def get_mask_from_segmentation(seg_data, segment_info, segment_name, slice_index=0):
    """
    Extract a boolean mask for one segment from a Slicer .seg.nrrd array.

    Supported cases:
    - 2D labelmap: (H, W)
    - layered 2D: (layers, H, W)
    - layered 3D/4D: (layers, H, W, slices)

    For your current 3D Slicer export:
    seg_data.shape = (3, 528, 528, 252)
    and the segmentation is on slice 0.
    """
    if segment_name not in segment_info:
        raise KeyError(f"Segment '{segment_name}' not found. Available: {list(segment_info.keys())}")

    layer = segment_info[segment_name]["layer"]
    label_value = segment_info[segment_name]["label_value"]

    # 2D labelmap
    if seg_data.ndim == 2:
        return seg_data == label_value

    # layered 2D
    if seg_data.ndim == 3:
        layer_img = seg_data[layer]
        return layer_img == label_value

    # layered 3D/4D from Slicer
    if seg_data.ndim == 4:
        seg_slice = seg_data[:, :, :, slice_index]   # shape: (layers, H, W)
        layer_img = seg_slice[layer]
        return layer_img == label_value

    raise ValueError(f"Unsupported segmentation shape: {seg_data.shape}")


def get_pixel_area_cm2(header: dict[str, Any]) -> float:
    """
    Compute in-plane pixel area in cm² from NRRD 'space directions'.

    Expects space directions like:
    [[sx, 0, 0],
     [0, sy, 0],
     [0, 0, sz]]

    sx and sy are usually in mm.
    """
    if "space directions" not in header:
        raise KeyError("Header does not contain 'space directions'.")

    space_dirs = header["space directions"]

    # robust extraction of x/y spacing magnitude
    sx = float(np.linalg.norm(space_dirs[0]))
    sy = float(np.linalg.norm(space_dirs[1]))

    pixel_area_mm2 = sx * sy
    pixel_area_cm2 = pixel_area_mm2 / 100.0
    return pixel_area_cm2