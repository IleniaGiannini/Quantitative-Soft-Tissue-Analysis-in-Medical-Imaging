REFERENCE_DATA = {
    "female": {
        "smi": {
            # Nowak et al. 2025, single-slice L3 MRI, prospective cohort.
            # Values are descriptive cohort values, not diagnostic cut-offs.
            "median": 41.1,
            "q1": 38.0,
            "q3": 50.8,
            "unit": "cm²/m²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
            "note": (
                "Descriptive L3 MRI values from a small technical validation cohort; "
                "not sex-specific and not intended as diagnostic reference cut-offs."
            ),
        },

        "skeletal_muscle_area": {
            "median": 125.5,
            "q1": 106.0,
            "q3": 174.5,
            "unit": "cm²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "sat_area": {
            "median": 124.0,
            "q1": 101.0,
            "q3": 178.5,
            "unit": "cm²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "sat_index": {
            "median": 44.1,
            "q1": 30.7,
            "q3": 61.0,
            "unit": "cm²/m²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "vat_area": {
            "median": 65.9,
            "q1": 47.4,
            "q3": 93.6,
            "unit": "cm²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "vat_index": {
            "median": 25.4,
            "q1": 14.6,
            "q3": 38.3,
            "unit": "cm²/m²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "vat_sat_ratio": {
            "median": 0.49,
            "q1": 0.29,
            "q3": 0.80,
            "unit": "ratio",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
            "note": (
                "Descriptive cohort distribution. A fixed clinical threshold is not provided "
                "by Nowak et al.; previous threshold=1.0 should be treated as heuristic."
            ),
        },

    },

    "male": {
        # Same Nowak values are used for male and female because Table 1 is not sex-specific.
        # This avoids pretending that sex-specific MRI L3 reference cut-offs exist in this paper.
        "smi": {
            "median": 41.1,
            "q1": 38.0,
            "q3": 50.8,
            "unit": "cm²/m²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
            "note": (
                "Descriptive L3 MRI values from a small technical validation cohort; "
                "not sex-specific and not intended as diagnostic reference cut-offs."
            ),
        },

        "skeletal_muscle_area": {
            "median": 125.5,
            "q1": 106.0,
            "q3": 174.5,
            "unit": "cm²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "sat_area": {
            "median": 124.0,
            "q1": 101.0,
            "q3": 178.5,
            "unit": "cm²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "sat_index": {
            "median": 44.1,
            "q1": 30.7,
            "q3": 61.0,
            "unit": "cm²/m²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "vat_area": {
            "median": 65.9,
            "q1": 47.4,
            "q3": 93.6,
            "unit": "cm²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "vat_index": {
            "median": 25.4,
            "q1": 14.6,
            "q3": 38.3,
            "unit": "cm²/m²",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
        },

        "vat_sat_ratio": {
            "median": 0.49,
            "q1": 0.29,
            "q3": 0.80,
            "unit": "ratio",
            "source": "Nowak et al. 2025, single-slice L3 MRI",
            "note": (
                "Descriptive cohort distribution. A fixed clinical threshold is not provided "
                "by Nowak et al.; previous threshold=1.0 should be treated as heuristic."
            ),
        },

    },

    "technical_performance": {
        "source": "Nowak et al. 2025, single-slice L3 MRI",

        "scan_rescan_repeatability": {
            "note": "Reference scanner Philips 1.5 T. RC = repeatability coefficient.",
            "skeletal_muscle_area": {"rc": 5.1, "cov_percent": 1.5, "unit": "cm²"},
            "smi": {"rc": 1.9, "cov_percent": 1.7, "unit": "cm²/m²"},
            "sat_area": {"rc": 12.0, "cov_percent": 1.9, "unit": "cm²"},
            "sat_index": {"rc": 3.5, "cov_percent": 1.9, "unit": "cm²/m²"},
            "vat_area": {"rc": 15.0, "cov_percent": 5.0, "unit": "cm²"},
            "vat_index": {"rc": 4.5, "cov_percent": 5.0, "unit": "cm²/m²"},
            "vat_sat_ratio": {"rc": 0.099, "cov_percent": 5.9, "unit": "ratio"},
        },

        "cross_scanner_reproducibility": {
            "note": "Philips 3 T compared with Philips 1.5 T reference scanner. RDC = reproducibility coefficient.",
            "skeletal_muscle_csa": {"rdc": 7.5, "cov_percent": 2.3, "unit": "cm²"},
            "smi": {"rdc": 2.8, "cov_percent": 2.4, "unit": "cm²/m²"},
            "sat_area": {"rdc": 26.0, "cov_percent": 7.3, "unit": "cm²"},
            "sat_index": {"rdc": 8.4, "cov_percent": 7.5, "unit": "cm²/m²"},
            "vat_area": {"rdc": 42.0, "cov_percent": 10.0, "unit": "cm²"},
            "vat_index": {"rdc": 12.0, "cov_percent": 10.0, "unit": "cm²/m²"},
            "vat_sat_ratio": {"rdc": 0.27, "cov_percent": 15.0, "unit": "ratio"},
        },
    },
}