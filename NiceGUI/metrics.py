from __future__ import annotations

import math
import numpy as np


def compute_area_cm2(mask: np.ndarray, pixel_area_cm2: float) -> float:
    """Compute area in cm² from a binary mask."""
    return float(np.sum(mask) * pixel_area_cm2)


def compute_vat_sat_ratio(vat_area_cm2: float, sat_area_cm2: float) -> float | None:
    """Return VAT/SAT ratio, or None if SAT is zero."""
    if sat_area_cm2 <= 0:
        return None
    return float(vat_area_cm2 / sat_area_cm2)


def compute_smi(muscle_area_cm2: float, height_m: float) -> float | None:
    """Compute skeletal muscle index (SMI) = muscle area / height²."""
    if height_m <= 0:
        return None
    return float(muscle_area_cm2 / (height_m ** 2))


def compute_index(area_cm2: float, height_m: float) -> float | None:
    """Generic area index = area / height²."""
    if height_m <= 0:
        return None
    return float(area_cm2 / (height_m ** 2))


def compute_mean_in_mask(image_2d: np.ndarray, mask: np.ndarray) -> float | None:
    """Mean image value inside a binary mask."""
    if image_2d.shape != mask.shape:
        return None
    if np.sum(mask) == 0:
        return None
    values = image_2d[mask]
    if values.size == 0:
        return None
    return float(np.mean(values))


def compute_smff(ff_image_2d: np.ndarray, muscle_mask: np.ndarray) -> float | None:
    """SMFF = mean fat fraction inside the muscle mask."""
    return compute_mean_in_mask(ff_image_2d, muscle_mask)


def compute_imat_mask(
    muscle_mask: np.ndarray,
    total_fat_mask: np.ndarray,
) -> np.ndarray | None:
    """IMAT mask = fat pixels inside muscle region."""
    if muscle_mask.shape != total_fat_mask.shape:
        return None
    return muscle_mask & total_fat_mask


def compute_imat_area_cm2(
    muscle_mask: np.ndarray,
    total_fat_mask: np.ndarray,
    pixel_area_cm2: float,
) -> float | None:
    """IMAT area in cm² from muscle-fat overlap."""
    imat_mask = compute_imat_mask(muscle_mask, total_fat_mask)
    if imat_mask is None:
        return None
    return compute_area_cm2(imat_mask, pixel_area_cm2)


def compute_muscle_to_fat_ratio(
    muscle_area_cm2: float,
    sat_area_cm2: float,
    vat_area_cm2: float,
) -> float | None:
    """Muscle-to-fat ratio = SMA / (SAT + VAT)."""
    total_fat = sat_area_cm2 + vat_area_cm2
    if total_fat <= 0:
        return None
    return float(muscle_area_cm2 / total_fat)


def estimate_percentile(value: float | None, reference: dict[int, float]) -> float | None:
    if value is None or not reference:
        return None

    points = sorted(reference.items())
    percentiles = [p for p, _ in points]
    values = [v for _, v in points]

    if value <= values[0]:
        return float(percentiles[0])
    if value >= values[-1]:
        return float(percentiles[-1])

    for i in range(len(values) - 1):
        v0, v1 = values[i], values[i + 1]
        p0, p1 = percentiles[i], percentiles[i + 1]

        if v0 <= value <= v1:
            if v1 == v0:
                return float(p0)
            fraction = (value - v0) / (v1 - v0)
            return float(p0 + fraction * (p1 - p0))

    return None


def percentile_band(percentile: float | None) -> str:
    if percentile is None:
        return "N/A"
    if percentile < 10:
        return "low"
    if percentile <= 90:
        return "reference range"
    return "high"


def reference_range_from_mean_sd(mean: float, sd: float, n_sd: float = 2.0) -> tuple[float, float]:
    """
    Create an approximate reference range from mean ± n*SD.
    Default: mean ± 2 SD.
    """
    low = mean - n_sd * sd
    high = mean + n_sd * sd
    return float(low), float(high)


def estimate_percentile_from_mean_sd(value: float | None, mean: float, sd: float) -> float | None:
    """
    Estimate percentile assuming an approximately normal distribution.
    Returns percentile in range 0..100.
    """
    if value is None or sd <= 0:
        return None

    z = (value - mean) / sd
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    percentile = cdf * 100.0
    return float(max(0.0, min(100.0, percentile)))