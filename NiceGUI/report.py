from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


def fmt(value, decimals=2, suffix=""):
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"



def create_pdf_report(output_path, results):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#1f3b5b"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["BodyText"],
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#444444"),
        )
    )

    elements = []
    
    role = results.get("user_role", "clinical")

    # Title
    elements.append(Paragraph("Quantitative Body Composition Report", styles["Title"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Single-slice L3 MRI analysis", styles["Heading3"]))
    elements.append(Spacer(1, 12))

    # Examination details
    details_data = [
        ["Sex", str(results.get("sex", "N/A")).capitalize()],
        ["Age", fmt(results.get("age"), 0, " years")],
        ["Height", fmt(results.get("height_m"), 2, " m")],
    ]

    if role == "clinical":
        if results.get("weight_kg") is not None:
            details_data.append(["Weight", fmt(results.get("weight_kg"), 1, " kg")])

        if results.get("bmi") is not None:
            details_data.append(["BMI", fmt(results.get("bmi"), 1, " kg/m²")])

        if results.get("waist_cm") is not None:
            details_data.append(["Waist circumference", fmt(results.get("waist_cm"), 1, " cm")])

        if results.get("score2") is not None:
            details_data.append([
                "SCORE2",
                f"{fmt(results.get('score2'), 1, ' %')} ({results.get('score2_category', 'N/A')})"
            ])

    elif role == "radiologist":
        if results.get("liver_fat_fraction") is not None:
            details_data.append([
                "Liver fat fraction",
                fmt(results.get("liver_fat_fraction"), 1, " %")
            ])

        details_data.append(["L3 slice index", str(results.get("slice_index", "N/A"))])
        details_data.append(["Pixel area", fmt(results.get("pixel_area_cm2"), 4, " cm²")])

    details_data += [
        ["Analysis level", "L3"],
        ["Method", "2D slice-based segmentation of muscle, SAT and VAT"],
    ]

    details_table = Table(details_data, colWidths=[4.2 * cm, 10.5 * cm])
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eef5")),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#9aa7b3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(Paragraph("Examination Details", styles["SectionTitle"]))
    elements.append(details_table)
    elements.append(Spacer(1, 14))

    # Quantitative metrics
    metrics_data = [["Metric", "Value"]]

    if role == "clinical":
        metric_items = [
            ("SMA / Muscle area", results.get("muscle_area_cm2"), 2, " cm²"),
            ("SAT area", results.get("sat_area_cm2"), 2, " cm²"),
            ("VAT area", results.get("vat_area_cm2"), 2, " cm²"),
            ("VAT/SAT ratio", results.get("vat_sat_ratio"), 2, ""),
            ("SMI", results.get("smi"), 2, " cm²/m²"),
            ("SAT index", results.get("sat_index"), 2, " cm²/m²"),
            ("VAT index", results.get("vat_index"), 2, " cm²/m²"),
            ("Muscle-to-fat ratio", results.get("muscle_to_fat_ratio"), 2, ""),
            ("IMAT area", results.get("imat_area_cm2"), 2, " cm²"),
            ("IMAT", results.get("imat_percent"), 2, " %"),
        ]

    elif role == "radiologist":
        metric_items = [
            ("SMA / Muscle area", results.get("muscle_area_cm2"), 2, " cm²"),
            ("SAT area", results.get("sat_area_cm2"), 2, " cm²"),
            ("VAT area", results.get("vat_area_cm2"), 2, " cm²"),
            ("VAT/SAT ratio", results.get("vat_sat_ratio"), 2, ""),
            ("SMI", results.get("smi"), 2, " cm²/m²"),
            ("SAT index", results.get("sat_index"), 2, " cm²/m²"),
            ("VAT index", results.get("vat_index"), 2, " cm²/m²"),
            ("Muscle-to-fat ratio", results.get("muscle_to_fat_ratio"), 2, ""),
            ("IMAT area", results.get("imat_area_cm2"), 2, " cm²"),
            ("IMAT", results.get("imat_percent"), 2, " %"),
            ("Liver fat fraction", results.get("liver_fat_fraction"), 1, " %"),
        ]

    else:
        metric_items = []

    for label, value, decimals, suffix in metric_items:
        if value is not None:
            metrics_data.append([label, fmt(value, decimals, suffix)])

    metrics_table = Table(metrics_data, colWidths=[7.5 * cm, 7.2 * cm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b5b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#9aa7b3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#eef2f7")]),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(Paragraph("Quantitative Results", styles["SectionTitle"]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 14))


    # Images side by side
    elements.append(Paragraph("Image Review", styles["SectionTitle"]))

    raw_img = Image(results["raw_path"], width=7.2 * cm, height=7.2 * cm)
    overlay_img = Image(results["overlay_path"], width=7.2 * cm, height=7.2 * cm)

    image_table = Table(
        [
            [
                Paragraph("<b>Fat Image</b>", styles["BodyText"]),
                Paragraph("<b>Segmentation Overlay</b>", styles["BodyText"]),
            ],
            [raw_img, overlay_img],
        ],
        colWidths=[7.8 * cm, 7.8 * cm],
    )

    image_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(image_table)
    elements.append(Spacer(1, 14))
