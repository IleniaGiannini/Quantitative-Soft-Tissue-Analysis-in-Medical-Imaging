"""
Body Composition Dashboard
ZHAW Bachelor Thesis - Quantitative Soft-Tissue Analysis

Changes:
  - Light KSW/ZHAW corporate theme, no dark/light toggle
  - Logos embedded as PNG base64 (no external files needed)
  - Portable paths (no hardcoded C:\\ZHAW\\ fallbacks)
  - "Blutdruck" / "Blood pressure" label (no syst. suffix, no note)
  - Full EN translation with live widget label updates
  - Role-specific PDF export
"""

import panel as pn
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from pathlib import Path
import scipy.stats as stats
import nibabel as nib
import nrrd
import datetime
import os
import io
import re
import argparse
import warnings
warnings.filterwarnings("ignore")

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

pn.extension(sizing_mode="stretch_width")

# =============================================================================
# LOGOS — PNG base64 embedded directly, no external files needed
# =============================================================================
KSW_IMG_TAG  = '<img src="data:image/png;base64,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" style="height:36px;object-fit:contain;display:block;">'
ZHAW_IMG_TAG = '<img src="data:image/png;base64,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" style="height:36px;object-fit:contain;display:block;">'

# =============================================================================
# CONFIGURATION
# Portable: uses --patient arg when called from Slicer.
# Fallback uses paths relative to this script for standalone use.
# =============================================================================
def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patient", default=None)
    parser.add_argument("--z", default=130, type=int)
    args, _ = parser.parse_known_args()
    print(f"[CONFIG] patient={args.patient}, z={args.z}", flush=True)
    if args.patient:
        nifti_dir = Path(args.patient) / "output" / "nifti"
        out_dir   = Path(args.patient) / "output"
        return {
            "CSV_PATH":       str(out_dir   / "body_composition_results.csv"),
            "WATER_NII_PATH": str(nifti_dir / "water.nii"),
            "FAT_NII_PATH":   str(nifti_dir / "fat.nii"),
            "SEG_NRRD_PATH":  str(nifti_dir / "seg_corrected.seg.nrrd"),
            "PDF_OUTPUT_DIR": str(out_dir),
            "L3_Z_INDEX":     args.z,
        }
    else:
        # Portable fallback: looks for data next to this script
        base = Path(__file__).parent
        return {
            "CSV_PATH":       str(base / "body_composition_results.csv"),
            "WATER_NII_PATH": str(base / "nifti" / "water.nii"),
            "FAT_NII_PATH":   str(base / "nifti" / "fat.nii"),
            "SEG_NRRD_PATH":  str(base / "nifti" / "seg_corrected.seg.nrrd"),
            "PDF_OUTPUT_DIR": str(base),
            "L3_Z_INDEX":     130,
        }

_cfg           = get_config()
CSV_PATH       = _cfg["CSV_PATH"]
WATER_NII_PATH = _cfg["WATER_NII_PATH"]
FAT_NII_PATH   = _cfg["FAT_NII_PATH"]
SEG_NRRD_PATH  = _cfg["SEG_NRRD_PATH"]
PDF_OUTPUT_DIR = _cfg["PDF_OUTPUT_DIR"]
L3_Z_INDEX     = _cfg["L3_Z_INDEX"]

# =============================================================================
# REFERENCE VALUES (Nowak et al. 2025, MRI L3, N=12)
# =============================================================================
REFERENCE = {
    "smi":          {"median":41.1,"q1":38.0,"q3":50.8,"unit":"cm2/m2","label":"SMI",          "color":"#0284C7","low_is_bad":True},
    "sat_index":    {"median":44.1,"q1":30.7,"q3":61.0,"unit":"cm2/m2","label":"SAT Index",    "color":"#D97706","low_is_bad":False},
    "vat_index":    {"median":25.4,"q1":14.6,"q3":38.3,"unit":"cm2/m2","label":"VAT Index",    "color":"#DC2626","low_is_bad":False},
    "vat_sat_ratio":{"median":0.49,"q1":0.29,"q3":0.80,"unit":"",      "label":"VAT/SAT Ratio","color":"#7C3AED","low_is_bad":False},
}
FF_REFERENCE = {
    "median":5.0,"q1":3.0,"q3":8.0,"unit":"%",
    "label":"Fat Fraction (FF)","color":"#059669","low_is_bad":False,"placeholder":True,
}

# =============================================================================
# COLORS — KSW/ZHAW Corporate Design (light theme)
# =============================================================================
KSW_BLUE     = "#00AEEF"
ZHAW_BLUE    = "#1A6FAD"
COLOR_SAT    = "#D97706"
COLOR_VAT    = "#DC2626"
COLOR_MUSCLE = "#1D4ED8"
COLOR_IMAT   = "#059669"
BG_CARD      = "#FFFFFF"
BG_ALT       = "#F0F7FD"
TEXT_DARK    = "#111827"
TEXT_MUTED   = "#6B7280"
BORDER       = "#BFDBFE"
ACCENT       = KSW_BLUE
COLOR_METAB  = "#0284C7"
COLOR_CARDIO = "#7C3AED"

# =============================================================================
# TRANSLATIONS
# =============================================================================
LANG = {
    "DE": {
        "title":"Koerperzusammensetzungs-Analyse",
        "date_lbl":"Datum","height_lbl":"Groesse",
        "metrics":"Klinische Metriken",
        "percentile":"Perzentil-Vergleich - Referenz: Nowak et al. 2025",
        "summary":"Metriken-Zusammenfassung",
        "all_results":"Alle Resultate",
        "export_btn":"PDF exportieren","exporting":"PDF wird generiert...","exported":"PDF gespeichert",
        "ref_note":"Ref: Nowak et al. 2025 - MRI L3 - N=12",
        "smi_note":"SMI: tief = schlechter Wert","vat_note":"VAT, VAT/SAT: hoch = schlechter Wert",
        "seg_title":"L3 Axialschnitt - Segmentierungs-Overlay",
        "viz_normal":"Normalverteilung","viz_bar":"Perzentilbalken",
        "ff_warning":"⚠ Referenzwerte Platzhalter — werden durch KSW-Daten ersetzt",
        "ff_placeholder":"Referenzwerte ausstehend (Platzhalter)",
        "lab_hint":"KSW PDF direkt hochladen (automatisches Parsing) oder CSV.",
        "disclaimer":"Automatisch generiert. Referenzwerte: Nowak et al. 2025 (MRI L3, N=12). Ersetzt keine aerztliche Beurteilung.",
        "metab_profile":"Metabolisches Profil","cardio_profile":"Kardiovaskulaeres Profil",
        "metab_cardio":"Metabolisches & Kardiovaskulaeres Profil",
        "patient_data":"Patientendaten","fat_frac_title":"Fat Fraction (FF)",
        "lab_title":"Laborwerte - KSW Befund",
        "bauchumfang":"Bauchumfang","weight":"Gewicht (kg)","age":"Alter (Jahre)",
        "sex":"Geschlecht","sex_opts":["","Maennlich","Weiblich","Divers"],
        "smoker":"Raucher","bp":"Blutdruck",
        "bp_systolic":"Blutdruck syst. (mmHg)","bp_diastolic":"Blutdruck diast. (mmHg)",
        "chol":"Gesamtcholesterin (mmol/L)","chol_hint":"Benoetigt fuer SCORE2",
        "ff_label":"Fat Fraction (FF) %",
        "score2_label":"SCORE2","score2_note":"Kardiovask. 10-Jahres-Risiko",
        "esc_cat":"ESC Risikokategorie","esc_guidelines":"ESC Guidelines 2021",
        "score2_input_lbl":"SCORE2 Wert (%)","score2_input_hint":"Vom Arzt mit offiziellem ESC-Rechner berechnet",
        "esc_low":"Niedrig","esc_moderate":"Moderat","esc_high":"Hoch",
        "lab_pdf_upload":"KSW Laborbefund (PDF) hochladen","lab_csv_upload":"oder CSV hochladen",
        "lab_parsed":"Laborwerte erkannt","lab_outside":"ausserhalb Referenzbereich",
        "no_ref":"Keine Referenz",
        "role_lbl":"Rolle:","view_lbl":"Ansicht:","lang_lbl":"Sprache:",
        "z_adjust":"Z-Slice anpassen:",
        "waist_ref":"WHO: M <94cm / F <80cm","vat_sat_risk":"Erhoehtes Risiko >0.8","bmi_normal":"Normal: 18.5-24.9",
        "metric_col":"Metrik","value_col":"Wert","median_col":"Median (Ref.)","pct_col":"Perzentil",
        "pz_suffix":". Pz.","role_rad":"Radiologie","role_clin":"Klinisch",
        "status":{"very_low":"Sehr niedrig","low":"Niedrig","normal":"Normal","high":"Hoch","very_high":"Sehr hoch"},
    },
    "EN": {
        "title":"Body Composition Analysis",
        "date_lbl":"Date","height_lbl":"Height",
        "metrics":"Clinical Metrics",
        "percentile":"Percentile Comparison - Reference: Nowak et al. 2025",
        "summary":"Metrics Summary",
        "all_results":"All Results",
        "export_btn":"Export PDF","exporting":"Generating PDF...","exported":"PDF saved",
        "ref_note":"Ref: Nowak et al. 2025 - MRI L3 - N=12",
        "smi_note":"SMI: low = worse","vat_note":"VAT, VAT/SAT: high = worse",
        "seg_title":"L3 Axial Slice - Segmentation Overlay",
        "viz_normal":"Normal Distribution","viz_bar":"Percentile Bars",
        "ff_warning":"⚠ Placeholder reference values — to be replaced with KSW data",
        "ff_placeholder":"Reference values pending (placeholder)",
        "lab_hint":"Upload KSW lab PDF (automatic parsing) or CSV.",
        "disclaimer":"Auto-generated. Reference values: Nowak et al. 2025 (MRI L3, N=12). Does not replace medical judgment.",
        "metab_profile":"Metabolic Profile","cardio_profile":"Cardiovascular Profile",
        "metab_cardio":"Metabolic & Cardiovascular Profile",
        "patient_data":"Patient Data","fat_frac_title":"Fat Fraction (FF)",
        "lab_title":"Lab Values - KSW Report",
        "bauchumfang":"Waist circumference","weight":"Weight (kg)","age":"Age (years)",
        "sex":"Sex","sex_opts":["","Male","Female","Other"],
        "smoker":"Smoker","bp":"Blood pressure",
        "bp_systolic":"Blood pressure syst. (mmHg)","bp_diastolic":"Blood pressure diast. (mmHg)",
        "chol":"Total cholesterol (mmol/L)","chol_hint":"Required for SCORE2",
        "ff_label":"Fat Fraction (FF) %",
        "score2_label":"SCORE2","score2_note":"10-year cardiovascular risk",
        "esc_cat":"ESC Risk Category","esc_guidelines":"ESC Guidelines 2021",
        "score2_input_lbl":"SCORE2 Value (%)","score2_input_hint":"Calculated by physician using official ESC calculator",
        "esc_low":"Low","esc_moderate":"Moderate","esc_high":"High",
        "lab_pdf_upload":"Upload KSW Lab Report (PDF)","lab_csv_upload":"or upload CSV",
        "lab_parsed":"Lab values detected","lab_outside":"outside reference range",
        "no_ref":"No reference",
        "role_lbl":"Role:","view_lbl":"View:","lang_lbl":"Language:",
        "z_adjust":"Adjust Z-Slice:",
        "waist_ref":"WHO: M <94cm / F <80cm","vat_sat_risk":"Elevated risk >0.8","bmi_normal":"Normal: 18.5-24.9",
        "metric_col":"Metric","value_col":"Value","median_col":"Median (Ref.)","pct_col":"Percentile",
        "pz_suffix":"th Pz.","role_rad":"Radiology","role_clin":"Clinical",
        "status":{"very_low":"Very low","low":"Low","normal":"Normal","high":"High","very_high":"Very high"},
    },
}

# =============================================================================
# SEG NRRD LOADER
# =============================================================================
def load_seg_nrrd(seg_path):
    data, header = nrrd.read(str(seg_path))
    segments = {}
    for k, v in header.items():
        if k.startswith("Segment") and "_" in k:
            seg_id, attr = k.split("_", 1)
            if seg_id not in segments: segments[seg_id] = {}
            segments[seg_id][attr] = v
    label_map = {}
    for seg_id, attrs in segments.items():
        name, layer, lv = attrs.get("Name"), attrs.get("Layer"), attrs.get("LabelValue")
        if name and layer is not None and lv is not None:
            label_map[name] = (int(layer), int(lv))
    if data.ndim == 4:
        combined = np.zeros(data.shape[1:], dtype=np.uint8)
        for li in range(data.shape[0]):
            mask = data[li] > 0; combined[mask] = data[li][mask]
    else:
        combined = data
    return combined, label_map

# =============================================================================
# DATA LOADING
# =============================================================================
def load_metrics(csv_path):
    df = pd.read_csv(csv_path)
    if "input" in df.columns and "combined" in df["input"].values:
        row = df[df["input"] == "combined"].iloc[0]
    else:
        row = df.iloc[0]
    return row, df

def load_mri_slice(nii_path, z_index):
    return nib.load(nii_path).get_fdata()[:, :, z_index].T

def get_fat_z_index(water_path, fat_path, z_water):
    try:
        wh = nib.load(water_path).header; fh = nib.load(fat_path).header
        wz = float(wh.get_sform()[2,3]); fz = float(fh.get_sform()[2,3])
        st = float(wh.get_zooms()[2])
        zo = round((wz - fz) / st)
        return int(np.clip(z_water + zo, 0, nib.load(fat_path).shape[2]-1)), zo
    except Exception as e:
        print(f"[WARN] Fat Z offset: {e}"); return z_water, 0

# =============================================================================
# PDF LAB PARSER
# =============================================================================
def parse_ksw_lab_pdf(pdf_bytes):
    if not HAS_PYMUPDF: return None, "PyMuPDF not installed"
    skip = {"Untersuchungen","Flag","Resultat","Einheit","Referenzbereich","Druckdatum",
            "Befundnummer","Auftragsnummer","Entnahmedatum","Laboreingangsdatum","Befunddatum",
            "Letzte","Änderung","Version","Status","abgeschlossen","DGLAB","KSW","Kantonsspital",
            "Hämatologie","Blutbild","Immunologie","Allergie","Chemie","Gerinnung","Hormone",
            "Differenzierung","maschinell","Linksverschiebung","Serologie","Mikrobiologie","Urologie"}
    try:
        results = []
        doc = fitz.open(stream=pdf_bytes if isinstance(pdf_bytes,bytes) else bytes(pdf_bytes), filetype="pdf")
        for page in doc:
            lines = page.get_text().split("\n"); i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line or any(line.startswith(s) or line==s for s in skip): i+=1; continue
                if re.match(r"^[A-Za-zäöüÄÖÜß\s/()+\-]+$", line) and 2 < len(line) < 60:
                    name=line; flag=value=unit=ref=""; j=i+1
                    if j<len(lines) and lines[j].strip() in ["*","H","L","!","HH","LL"]: flag=lines[j].strip(); j+=1
                    if j<len(lines):
                        m=re.match(r"^([\d.,]+)\s+([^\s]+)$", lines[j].strip())
                        if m:
                            value=m.group(1).replace(",","."); unit=m.group(2); j+=1
                            if j<len(lines):
                                rl=lines[j].strip()
                                if re.match(r"^[\d.,<>\-\s]+$", rl) and rl!="-": ref=rl; j+=1
                            results.append({"Untersuchung":name,"Flag":flag,"Resultat":value,"Einheit":unit,"Referenzbereich":ref})
                            i=j; continue
                i+=1
        doc.close()
        return (pd.DataFrame(results), None) if results else (None, "Keine Laborwerte erkannt")
    except Exception as e:
        return None, str(e)

# =============================================================================
# SCORE2 — ESC 2021 classification (3 categories, low CVD risk population)
# The physician calculates SCORE2 externally (official ESC calculator) and
# enters the final percentage value. The dashboard only classifies the result.
#
# Thresholds (Oliver / ESC Guidelines 2021):
#   <50 years:  <2.5% Low | 2.5–<7.5% Moderate | >=7.5% High
#   50–69 years: <5%  Low |    5–<10% Moderate  |  >=10% High
#   >=70 years: <7.5% Low |  7.5–<15% Moderate  |  >=15% High
# =============================================================================
def classify_score2(score2_pct, age):
    """Classify a physician-entered SCORE2 value into ESC risk category."""
    if score2_pct is None or score2_pct <= 0 or age is None or age <= 0:
        return None
    if age < 50:
        return "esc_low" if score2_pct < 2.5 else "esc_moderate" if score2_pct < 7.5 else "esc_high"
    elif age < 70:
        return "esc_low" if score2_pct < 5.0 else "esc_moderate" if score2_pct < 10.0 else "esc_high"
    else:
        return "esc_low" if score2_pct < 7.5 else "esc_moderate" if score2_pct < 15.0 else "esc_high"

# =============================================================================
# PERCENTILE HELPERS
# =============================================================================
def iqr_to_percentile(value, median, q1, q3):
    iqr = q3-q1
    if iqr<=0: return 50.0
    return float(np.clip(stats.norm.cdf((value-median)/(iqr/1.35))*100, 0.5, 99.5))

def percentile_color(pct, low_is_bad):
    if low_is_bad:
        if pct<10: return "#DC2626"
        if pct<25: return "#D97706"
        if pct<75: return "#0284C7"
        return "#16A34A"
    else:
        if pct>90: return "#DC2626"
        if pct>75: return "#D97706"
        if pct>25: return "#0284C7"
        return "#16A34A"

def percentile_status_key(pct, low_is_bad):
    if low_is_bad:
        if pct<10: return "very_low"
        if pct<25: return "low"
        if pct<75: return "normal"
        return "high"
    else:
        if pct>90: return "very_high"
        if pct>75: return "high"
        if pct>25: return "normal"
        return "low"

def pz(pct, lang_key):
    return f"{pct:.0f}{LANG[lang_key]['pz_suffix']}"

# =============================================================================
# FIGURES — light background versions
# =============================================================================
def create_normal_distribution_figure(row, lang_key="DE", ff_value=None):
    T = LANG[lang_key]
    def sf(k):
        try: return float(row[k])
        except: return None
    mets = [("smi","#0284C7"),("sat_index","#D97706"),("vat_index","#DC2626"),("vat_sat_ratio","#7C3AED")]
    if ff_value and ff_value>0: mets.append(("ff","#059669"))
    n=len(mets); cols=3 if n>4 else 2; rows=(n+cols-1)//cols
    fig,axes=plt.subplots(rows,cols,figsize=(cols*6,rows*3.2),facecolor="white")
    af=np.array(axes).flatten()
    for idx in range(len(af)): af[idx].set_visible(idx<n)
    for i,(key,color) in enumerate(mets):
        ax=af[i]; ax.set_facecolor("#F8FAFC")
        for sp in ax.spines.values(): sp.set_color("#D1E8F7"); sp.set_linewidth(0.8)
        ref=FF_REFERENCE if key=="ff" else REFERENCE[key]
        val=ff_value if key=="ff" else sf(key)
        if val is None or val==0:
            ax.text(0.5,0.5,"N/A",color=TEXT_MUTED,ha="center",va="center",transform=ax.transAxes,fontsize=12); ax.axis("off"); continue
        sigma=(ref["q3"]-ref["q1"])/1.35; median=ref["median"]
        x=np.linspace(median-3.8*sigma,median+3.8*sigma,300); y=stats.norm.pdf(x,median,sigma)
        pct=iqr_to_percentile(val,median,ref["q1"],ref["q3"])
        status=T["status"][percentile_status_key(pct,ref["low_is_bad"])]
        ax.plot(x,y,color="#CBD5E1",linewidth=1.5)
        xf=x[x<=val]; rgb=tuple(int(color.lstrip("#")[j:j+2],16)/255 for j in (0,2,4))
        ax.fill_between(xf,stats.norm.pdf(xf,median,sigma),alpha=0.25,color=rgb)
        ymax=y.max()
        ax.axvline(val,color=color,linewidth=2,zorder=5)
        ax.axvline(median,color="#94A3B8",linewidth=1,linestyle="--",alpha=0.7)
        ax.text(val,ymax*0.92,f"{val:.2f}",color=color,fontsize=9,fontweight="bold",ha="center",va="bottom")
        ax.text(median,-ymax*0.06,f"Md {median:.1f}",color=TEXT_MUTED,fontsize=8,ha="center",va="top")
        ax.set_title(f"{ref['label']}  |  {pz(pct,lang_key)}  |  {status}",color=TEXT_DARK,fontsize=9,pad=8)
        ax.set_xlim(x[0],x[-1]); ax.set_ylim(-ymax*0.15,ymax*1.15)
        ax.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)
        ax.text(0.5,-0.08,T["ref_note"] if key!="ff" else "Ref: Platzhalter - KSW ausstehend",
                color="#94A3B8",fontsize=7,ha="center",transform=ax.transAxes)
    fig.text(0.5,0.01,f"{T['smi_note']}   |   {T['vat_note']}",color=TEXT_MUTED,fontsize=8,ha="center")
    plt.tight_layout(pad=1.8); return fig

def create_percentile_bar_figure(row, lang_key="DE", ff_value=None):
    T = LANG[lang_key]
    def sf(k):
        try: return float(row[k])
        except: return None
    from matplotlib.colors import LinearSegmentedColormap
    bar_cmap=LinearSegmentedColormap.from_list("bar",["#1e3a8a","#3b82f6","#0284C7","#16A34A","#D97706","#DC2626"])
    keys=["smi","sat_index","vat_index","vat_sat_ratio"]
    if ff_value and ff_value>0: keys.append("ff")
    fig,ax=plt.subplots(figsize=(12,max(4,len(keys)*0.9+1)),facecolor="white")
    ax.set_facecolor("white"); ax.axis("off")
    bh,gap,y0=0.10,0.18,0.88
    for i,key in enumerate(keys):
        ref=FF_REFERENCE if key=="ff" else REFERENCE.get(key)
        val=ff_value if key=="ff" else sf(key)
        if val is None or val==0 or ref is None: continue
        pct=iqr_to_percentile(val,ref["median"],ref["q1"],ref["q3"])
        col=percentile_color(pct,ref["low_is_bad"]); stat=T["status"][percentile_status_key(pct,ref["low_is_bad"])]
        y=y0-i*gap
        ax.imshow(np.linspace(0,1,256).reshape(1,-1),aspect="auto",cmap=bar_cmap,
                  extent=[0.12,0.92,y,y+bh],transform=ax.transAxes,zorder=1)
        mx=0.12+(pct/100)*0.80
        ax.annotate("",xy=(mx,y+bh*1.9),xytext=(mx,y+bh),xycoords="axes fraction",textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="->",color=col,lw=2.5),zorder=5)
        ax.text(0.10,y+bh/2,f"{ref['label']}  {val:.2f} {ref['unit']}",
                transform=ax.transAxes,ha="right",va="center",fontsize=9,color=TEXT_DARK)
        ax.text(0.94,y+bh/2,f"{stat} · {pz(pct,lang_key)}",
                transform=ax.transAxes,ha="left",va="center",fontsize=9,color=col,fontweight="bold")
    ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.text(0.5,y0-len(keys)*gap-0.05,f"{T['smi_note']}   |   {T['vat_note']}   |   {T['ref_note']}",
            transform=ax.transAxes,ha="center",va="top",fontsize=8,color=TEXT_MUTED)
    plt.tight_layout(pad=1.0); return fig

# =============================================================================
# SUMMARY TABLE HTML — light theme
# =============================================================================
def summary_table_html(row, lang_key="DE", ff_value=None):
    T = LANG[lang_key]
    def sf(k):
        try: return float(row[k])
        except: return None
    rh=""
    for key,ref in REFERENCE.items():
        val=sf(key)
        if val is None: continue
        pct=iqr_to_percentile(val,ref["median"],ref["q1"],ref["q3"])
        color=percentile_color(pct,ref["low_is_bad"]); pz_=pz(pct,lang_key)
        rh+=(f'<tr style="border-bottom:1px solid {BORDER};">'
             f'<td style="padding:10px 14px;font-size:12px;font-weight:600;color:{TEXT_DARK};">{ref["label"]}</td>'
             f'<td style="padding:10px 14px;font-size:12px;color:{TEXT_MUTED};font-family:monospace;">{val:.2f} {ref["unit"]}</td>'
             f'<td style="padding:10px 14px;font-size:12px;color:{TEXT_MUTED};">{ref["median"]:.2f} {ref["unit"]}</td>'
             f'<td style="padding:10px 14px;"><span style="background:{color}18;color:{color};border:1px solid {color}66;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">{pz_}</span></td>'
             f'</tr>')
    iv=sf("imat_cm2"); ip=sf("imat_pct")
    if iv is not None:
        rh+=(f'<tr style="border-bottom:1px solid {BORDER};">'
             f'<td style="padding:10px 14px;font-size:12px;font-weight:600;color:{TEXT_DARK};">IMAT</td>'
             f'<td style="padding:10px 14px;font-size:12px;color:{TEXT_MUTED};font-family:monospace;">{iv:.2f} cm2 ({ip:.1f}%)</td>'
             f'<td style="padding:10px 14px;color:#94A3B8;">—</td>'
             f'<td style="padding:10px 14px;"><span style="font-size:10px;color:#94A3B8;">{T["no_ref"]}</span></td></tr>')
    if ff_value and ff_value>0:
        pct=iqr_to_percentile(ff_value,FF_REFERENCE["median"],FF_REFERENCE["q1"],FF_REFERENCE["q3"])
        color=percentile_color(pct,FF_REFERENCE["low_is_bad"]); pz_=pz(pct,lang_key)
        rh+=(f'<tr style="border-bottom:1px solid {BORDER};">'
             f'<td style="padding:10px 14px;font-size:12px;font-weight:600;color:{TEXT_DARK};">Fat Fraction (FF) ⚠</td>'
             f'<td style="padding:10px 14px;font-size:12px;color:{TEXT_MUTED};font-family:monospace;">{ff_value:.1f} %</td>'
             f'<td style="padding:10px 14px;font-size:12px;color:{TEXT_MUTED};">{FF_REFERENCE["median"]:.1f} %</td>'
             f'<td style="padding:10px 14px;"><span style="background:{color}18;color:{color};border:1px solid {color}66;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">{pz_}</span></td></tr>')
    return (f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;overflow:hidden;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr style="background:{BG_ALT};border-bottom:2px solid {BORDER};">'
            f'<th style="padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};">{T["metric_col"]}</th>'
            f'<th style="padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};">{T["value_col"]}</th>'
            f'<th style="padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};">{T["median_col"]}</th>'
            f'<th style="padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};">{T["pct_col"]}</th>'
            f'</tr></thead><tbody>{rh}</tbody></table>'
            f'<div style="padding:10px 14px;font-size:10px;color:#94A3B8;border-top:1px solid {BORDER};">{T["ref_note"]}</div></div>')

# =============================================================================
# CLINICAL PROFILES HTML — light theme
# =============================================================================
def metabolic_profile_html(row, waist, bmi, lang_key="DE"):
    T = LANG[lang_key]
    def sf(k):
        try: return float(row[k])
        except: return None
    vat_sat=sf("vat_sat_ratio")

    def card(label, value, unit, color, note=""):
        if value is None or value==0:
            vs="—"; cu=TEXT_MUTED
        else:
            vs=f"{value:.1f}" if isinstance(value,float) else str(value); cu=color
        note_html=f'<div style="font-size:10px;color:{TEXT_MUTED};margin-top:2px;">{note}</div>' if note else ""
        return (f'<div style="background:{BG_ALT};border:1px solid {BORDER};border-radius:10px;'
                f'padding:14px 16px;flex:1;min-width:140px;border-left:4px solid {color};">'
                f'<div style="font-size:22px;font-weight:600;color:{cu};font-family:monospace;">'
                f'{vs}<span style="font-size:12px;color:{TEXT_MUTED};margin-left:4px;">{unit}</span></div>'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};margin-top:4px;">{label}</div>'
                f'{note_html}</div>')

    return (f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;'
            f'padding:16px 20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
            f'<div style="font-size:12px;font-weight:700;color:{COLOR_METAB};text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:14px;border-bottom:1px solid {BORDER};padding-bottom:8px;">◆ {T["metab_profile"]}</div>'
            f'<div style="display:flex;gap:12px;flex-wrap:wrap;">'
            f'{card(T["bauchumfang"], waist, "cm", COLOR_METAB, T["waist_ref"])}'
            f'{card("BMI", bmi, "kg/m2", COLOR_METAB, T["bmi_normal"])}'
            f'{card("VAT/SAT Ratio", vat_sat, "", COLOR_METAB, T["vat_sat_risk"])}'
            f'</div></div>')

def cardiovascular_profile_html(score2, esc_cat, systolic, diastolic, lang_key="DE"):
    T = LANG[lang_key]
    ec={"esc_low":"#16A34A","esc_moderate":"#D97706","esc_high":"#DC2626","esc_very_high":"#7F1D1D"}
    esc_color=ec.get(esc_cat,TEXT_MUTED) if esc_cat else TEXT_MUTED
    esc_label=T.get(esc_cat,"—") if esc_cat else "—"
    bp_str=f"{systolic:.0f}/{diastolic:.0f}" if systolic and diastolic and systolic>0 and diastolic>0 else "—"
    s2_str=f"{score2:.1f}%" if score2 else "—"

    def card(label, value, unit, color, note=""):
        note_html=f'<div style="font-size:10px;color:{TEXT_MUTED};margin-top:2px;">{note}</div>' if note else ""
        return (f'<div style="background:{BG_ALT};border:1px solid {BORDER};border-radius:10px;'
                f'padding:14px 16px;flex:1;min-width:140px;border-left:4px solid {color};">'
                f'<div style="font-size:22px;font-weight:600;color:{color};font-family:monospace;">'
                f'{value}<span style="font-size:12px;color:{TEXT_MUTED};margin-left:4px;">{unit}</span></div>'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};margin-top:4px;">{label}</div>'
                f'{note_html}</div>')

    return (f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;'
            f'padding:16px 20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
            f'<div style="font-size:12px;font-weight:700;color:{COLOR_CARDIO};text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:14px;border-bottom:1px solid {BORDER};padding-bottom:8px;">◆ {T["cardio_profile"]}</div>'
            f'<div style="display:flex;gap:12px;flex-wrap:wrap;">'
            f'{card(T["bp"], bp_str, "mmHg", COLOR_CARDIO)}'
            f'{card(T["score2_label"], s2_str, "", COLOR_CARDIO, T["score2_note"])}'
            f'<div style="background:{BG_ALT};border:1px solid {BORDER};border-radius:10px;'
            f'padding:14px 16px;flex:1;min-width:140px;border-left:4px solid {esc_color};">'
            f'<div style="font-size:16px;font-weight:600;color:{esc_color};">{esc_label}</div>'
            f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};margin-top:4px;">{T["esc_cat"]}</div>'
            f'<div style="font-size:10px;color:#94A3B8;margin-top:2px;">{T["esc_guidelines"]}</div>'
            f'</div></div></div>')

# =============================================================================
# MRI FIGURE
# =============================================================================
def create_mri_figure_selective(water_path, fat_path, seg_path, z_index, visible):
    fig,axes=plt.subplots(1,2,figsize=(14,7),facecolor="white")
    try:
        seg_combined,label_map=load_seg_nrrd(seg_path)
        ml=[label_map[n][1] for n in ["Autochthon_R","Autochthon_L","Iliopsoas_R","Iliopsoas_L","Muscle"] if n in label_map]
        sl=label_map.get("SAT",(0,65))[1]; vl=label_map.get("VAT",(0,67))[1]; il=label_map.get("IMAT",(1,1))[1]
        seg_sl=seg_combined[:,:,z_index].T
    except:
        ml=[59,60,61,62,66]; sl,vl,il=65,67,1; seg_sl=None
    z_fat,zo=get_fat_z_index(water_path,fat_path,z_index)
    if zo!=0: print(f"[INFO] z_water={z_index}, z_fat={z_fat} (offset={zo})")
    for ai,(ax,nii,z_use,title) in enumerate([(axes[0],water_path,z_index,"L3  -  Water - Skeletal Muscle"),
                                               (axes[1],fat_path,z_fat,"L3  -  Fat - SAT / VAT / IMAT")]):
        ax.set_facecolor("#F8FAFC")
        try:
            s=load_mri_slice(nii,z_use)
            ax.imshow(s,cmap="gray",aspect="equal",vmin=np.percentile(s,1),vmax=np.percentile(s,99))
            if seg_sl is not None:
                ov=np.zeros((*seg_sl.shape,4),dtype=np.float32)
                if ai==0 and "Muscle" in visible:
                    rgb=[int(COLOR_MUSCLE[j:j+2],16)/255 for j in (1,3,5)]
                    for lbl in ml: ov[seg_sl==lbl]=[*rgb,0.55]
                if ai==1:
                    if "SAT"  in visible: rgb=[int(COLOR_SAT[j:j+2],16)/255  for j in (1,3,5)];  ov[seg_sl==sl]=[*rgb,0.55]
                    if "VAT"  in visible: rgb=[int(COLOR_VAT[j:j+2],16)/255  for j in (1,3,5)];  ov[seg_sl==vl]=[*rgb,0.55]
                    if "IMAT" in visible: rgb=[int(COLOR_IMAT[j:j+2],16)/255 for j in (1,3,5)]; ov[seg_sl==il]=[*rgb,0.65]
                ax.imshow(ov,aspect="equal")
        except Exception as e:
            ax.text(0.5,0.5,f"Error:\n{e}",color="black",ha="center",va="center",transform=ax.transAxes)
        patches=[]
        if ai==0 and "Muscle" in visible: patches.append(mpatches.Patch(color=COLOR_MUSCLE,label="Skeletal Muscle"))
        if ai==1:
            if "SAT"  in visible: patches.append(mpatches.Patch(color=COLOR_SAT,label="SAT"))
            if "VAT"  in visible: patches.append(mpatches.Patch(color=COLOR_VAT,label="VAT"))
            if "IMAT" in visible: patches.append(mpatches.Patch(color=COLOR_IMAT,label="IMAT"))
        if patches: ax.legend(handles=patches,loc="lower right",framealpha=0.9,facecolor="white",edgecolor=BORDER,labelcolor=TEXT_DARK,fontsize=10)
        ax.set_title(title,color=TEXT_DARK,fontsize=11,fontfamily="monospace",pad=10); ax.axis("off")
    plt.tight_layout(pad=0.5); return fig

# =============================================================================
# PDF HELPERS
# =============================================================================
def _style_tbl(tbl):
    tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.scale(1,1.3)
    for (r,c),cell in tbl.get_celld().items():
        cell.set_edgecolor("#E5E7EB")
        if r==0: cell.set_facecolor("#EFF6FF"); cell.set_text_props(fontweight="bold",color="#1E3A5F")
        else: cell.set_facecolor("white" if r%2==0 else "#F8FAFC")

def _pdf_header(fig, T, patient_id, date_val, height_m, role_label):
    # KSW blue accent bar
    fig.add_artist(plt.Line2D([0,1],[0.965,0.965],transform=fig.transFigure,color="#00AEEF",linewidth=4))
    fig.text(0.07,0.952,f"{T['title']} — {role_label}",fontsize=15,fontweight="bold",color="#1E3A5F")
    fig.text(0.07,0.937,f"ZHAW x KSW  ·  {patient_id}  ·  {T['date_lbl']}: {date_val}  ·  {T['height_lbl']}: {height_m:.2f} m",
             fontsize=9,color=TEXT_MUTED)
    fig.add_artist(plt.Line2D([0.07,0.96],[0.930,0.930],transform=fig.transFigure,color="#BFDBFE",linewidth=0.8))

def _pdf_footer(fig, T):
    fig.add_artist(plt.Line2D([0.07,0.96],[0.035,0.035],transform=fig.transFigure,color="#BFDBFE",linewidth=0.5))
    fig.text(0.07,0.025,f"* FF: {T['ff_placeholder']}. {T['disclaimer']}",fontsize=6.5,color="#94A3B8",style="italic")
    fig.text(0.07,0.012,f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  ZHAW Bachelor Thesis  ·  Confidential",fontsize=6.5,color="#CBD5E1")

def _pdf_metrics_table(ax, row, T, ff_value, extra=None, score2=None, esc_cat=None):
    def sf(k):
        try: return float(row[k])
        except: return None
    ax.axis("off"); ax.set_title(T["metrics"],fontsize=9,color="#1E3A5F",loc="left",pad=8,fontweight="bold")
    md=[["Metric","Value","Unit"],
        ["SAT Area",     f"{sf('sat_cm2'):.1f}"       if sf("sat_cm2")       else "-","cm²"],
        ["VAT Area",     f"{sf('vat_cm2'):.1f}"       if sf("vat_cm2")       else "-","cm²"],
        ["Muscle Area",  f"{sf('sma_cm2'):.1f}"       if sf("sma_cm2")       else "-","cm²"],
        ["IMAT Area",    f"{sf('imat_cm2'):.1f}"      if sf("imat_cm2")      else "-","cm²"],
        ["IMAT %",       f"{sf('imat_pct'):.1f}"      if sf("imat_pct")      else "-","%"],
        ["SMI",          f"{sf('smi'):.2f}"           if sf("smi")           else "-","cm²/m²"],
        ["SAT Index",    f"{sf('sat_index'):.2f}"     if sf("sat_index")     else "-","cm²/m²"],
        ["VAT Index",    f"{sf('vat_index'):.2f}"     if sf("vat_index")     else "-","cm²/m²"],
        ["VAT/SAT Ratio",f"{sf('vat_sat_ratio'):.3f}" if sf("vat_sat_ratio") else "-",""],
    ]
    if ff_value and ff_value>0: md.append(["Fat Fraction (FF) *",f"{ff_value:.1f}","%"])
    if extra:
        if extra.get("bmi"):    md.append(["BMI",f"{extra['bmi']:.1f}","kg/m²"])
        if extra.get("waist"):  md.append([T["bauchumfang"],f"{extra['waist']:.0f}","cm"])
        if extra.get("systolic") and extra.get("diastolic"):
            md.append([T["bp"],f"{extra['systolic']:.0f}/{extra['diastolic']:.0f}","mmHg"])
    if score2:
        md.append([T["score2_label"],f"{score2:.1f}","%"])
        md.append([T["esc_cat"],T.get(esc_cat,"—") if esc_cat else "—",""])
    tbl=ax.table(cellText=[r for r in md[1:]],colLabels=md[0],loc="center",cellLoc="center")
    _style_tbl(tbl)

def _pdf_normal_distribution(ax, row, T, lang_key, ff_value):
    """Render a compact 2x2 normal distribution grid into a PDF axes."""
    def sf(k):
        try: return float(row[k])
        except: return None
    from matplotlib.colors import LinearSegmentedColormap
    keys=[("smi","#0284C7"),("sat_index","#D97706"),("vat_index","#DC2626"),("vat_sat_ratio","#7C3AED")]
    if ff_value and ff_value>0: keys.append(("ff","#059669"))
    n=len(keys); cols=2; rows_=(n+cols-1)//cols
    ax.axis("off"); ax.set_title(T["percentile"],fontsize=9,color="#1E3A5F",loc="left",pad=8,fontweight="bold")
    fig_=ax.get_figure()
    # Create nested axes inside the parent axes using inset_axes approach
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    w_pct=0.48; h_pct=0.44; margins=[(0.01,0.52),(0.51,0.52),(0.01,0.04),(0.51,0.04)]
    for i,(key,color) in enumerate(keys[:4]):
        if i>=4: break
        ref=FF_REFERENCE if key=="ff" else REFERENCE[key]
        val=ff_value if key=="ff" else sf(key)
        if val is None or val==0: continue
        x0,y0=margins[i]
        sub=ax.inset_axes([x0,y0,w_pct,h_pct])
        sub.set_facecolor("#F8FAFC")
        for sp in sub.spines.values(): sp.set_color("#D1E8F7"); sp.set_linewidth(0.5)
        sigma=(ref["q3"]-ref["q1"])/1.35; median=ref["median"]
        x=np.linspace(median-3.8*sigma,median+3.8*sigma,200); y=stats.norm.pdf(x,median,sigma)
        pct=iqr_to_percentile(val,median,ref["q1"],ref["q3"])
        status=T["status"][percentile_status_key(pct,ref["low_is_bad"])]
        sub.plot(x,y,color="#CBD5E1",linewidth=1)
        xf=x[x<=val]; rgb=tuple(int(color.lstrip("#")[j:j+2],16)/255 for j in (0,2,4))
        sub.fill_between(xf,stats.norm.pdf(xf,median,sigma),alpha=0.25,color=rgb)
        ymax=y.max()
        sub.axvline(val,color=color,linewidth=1.5,zorder=5)
        sub.axvline(median,color="#94A3B8",linewidth=0.8,linestyle="--",alpha=0.7)
        sub.text(val,ymax*0.90,f"{val:.1f}",color=color,fontsize=6,fontweight="bold",ha="center",va="bottom")
        sub.set_title(f"{ref['label']} | {pz(pct,lang_key)} | {status}",
                      color="#1E3A5F",fontsize=6.5,pad=3)
        sub.set_xlim(x[0],x[-1]); sub.set_ylim(-ymax*0.15,ymax*1.2)
        sub.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)

def _pdf_bar_chart(ax, row, T, lang_key, ff_value):
    def sf(k):
        try: return float(row[k])
        except: return None
    from matplotlib.colors import LinearSegmentedColormap
    bar_cmap=LinearSegmentedColormap.from_list("bar",["#1e3a8a","#3b82f6","#0284C7","#16A34A","#D97706","#DC2626"])
    ax.axis("off"); ax.set_title(T["percentile"],fontsize=9,color="#1E3A5F",loc="left",pad=8,fontweight="bold")
    keys=["smi","sat_index","vat_index","vat_sat_ratio"]
    if ff_value and ff_value>0: keys.append("ff")
    bh,gap,y0=0.09,0.19,0.92
    for i,key in enumerate(keys):
        ref=FF_REFERENCE if key=="ff" else REFERENCE.get(key)
        val=ff_value if key=="ff" else sf(key)
        if val is None or val==0 or ref is None: continue
        pct=iqr_to_percentile(val,ref["median"],ref["q1"],ref["q3"])
        col=percentile_color(pct,ref["low_is_bad"]); stat=T["status"][percentile_status_key(pct,ref["low_is_bad"])]
        y=y0-i*gap
        ax.imshow(np.linspace(0,1,256).reshape(1,-1),aspect="auto",cmap=bar_cmap,
                  extent=[0.08,0.95,y,y+bh],transform=ax.transAxes,zorder=1)
        mx=0.08+(pct/100)*0.87
        ax.annotate("",xy=(mx,y+bh*1.8),xytext=(mx,y+bh),xycoords="axes fraction",textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="->",color=col,lw=2),zorder=5)
        ax.text(0.06,y+bh/2,f"{ref['label']}  {val:.2f} {ref['unit']}",
                transform=ax.transAxes,ha="right",va="center",fontsize=8,color="#1E3A5F")
        ax.text(0.96,y+bh/2,f"{stat} - {pz(pct,lang_key)}",
                transform=ax.transAxes,ha="left",va="center",fontsize=8,color=col,fontweight="bold")
    ax.set_xlim(0,1); ax.set_ylim(0,1)

# =============================================================================
# PDF EXPORT — RADIOLOGY
# Layout (top to bottom):
#   1. Header
#   2. Metrics table (left) + Percentile visualization (right)
#   3. MRI overlays — water+muscle (left) + fat+SAT/VAT (right)
#   4. Footer
# =============================================================================
def export_pdf_radiology(row, lang_key, ff_value, patient_id, date_val, height_m, viz_mode="bar"):
    T=LANG[lang_key]
    fp=os.path.join(PDF_OUTPUT_DIR,
        f"BodyComp_{T['role_rad']}_{patient_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    with PdfPages(fp) as pdf:
        fig=plt.figure(figsize=(11.69,16.54)); fig.patch.set_facecolor("white")
        # 3 rows: metrics+percentile / MRI images / empty (footer space)
        gs=gridspec.GridSpec(3,2,figure=fig,
                             height_ratios=[1.0, 1.2, 0.05],
                             hspace=0.55,wspace=0.3,
                             left=0.06,right=0.97,top=0.925,bottom=0.04)
        _pdf_header(fig,T,patient_id,date_val,height_m,T["role_rad"])

        # Row 0: Metrics table (left) + Percentile visualization (right)
        _pdf_metrics_table(fig.add_subplot(gs[0,0]), row, T, ff_value)
        ax_viz = fig.add_subplot(gs[0,1])
        if viz_mode in ["Normalverteilung","Normal Distribution"]:
            _pdf_normal_distribution(ax_viz, row, T, lang_key, ff_value)
        else:
            _pdf_bar_chart(ax_viz, row, T, lang_key, ff_value)

        # Row 1: MRI overlays — full width, side by side
        ax_w=fig.add_subplot(gs[1,0]); ax_f=fig.add_subplot(gs[1,1])
        try:
            sc,lm=load_seg_nrrd(SEG_NRRD_PATH)
            ml=[lm[n][1] for n in ["Autochthon_R","Autochthon_L","Iliopsoas_R","Iliopsoas_L","Muscle"] if n in lm]
            sl_=lm.get("SAT",(0,65))[1]; vl_=lm.get("VAT",(0,67))[1]; seg_sl=sc[:,:,L3_Z_INDEX].T
        except:
            ml=[59,60,61,62,66]; sl_,vl_=65,67; seg_sl=None
        for ax,nii,um,uf,ttl in [(ax_w,WATER_NII_PATH,True,False,"Water — Skeletal Muscle"),
                                   (ax_f,FAT_NII_PATH,False,True,"Fat — SAT & VAT")]:
            try:
                s=load_mri_slice(nii,L3_Z_INDEX)
                ax.imshow(s,cmap="gray",aspect="equal",vmin=np.percentile(s,1),vmax=np.percentile(s,99))
                if seg_sl is not None:
                    ov=np.zeros((*seg_sl.shape,4),dtype=np.float32)
                    if um:
                        rgb=[int(COLOR_MUSCLE[j:j+2],16)/255 for j in (1,3,5)]
                        for lbl in ml: ov[seg_sl==lbl]=[*rgb,0.55]
                        ax.legend(handles=[mpatches.Patch(color=COLOR_MUSCLE,label="Muscle")],loc="lower right",fontsize=7,framealpha=0.9,facecolor="white")
                    if uf:
                        rs=[int(COLOR_SAT[j:j+2],16)/255 for j in (1,3,5)]; rv=[int(COLOR_VAT[j:j+2],16)/255 for j in (1,3,5)]
                        ov[seg_sl==sl_]=[*rs,0.55]; ov[seg_sl==vl_]=[*rv,0.55]
                        ax.legend(handles=[mpatches.Patch(color=COLOR_SAT,label="SAT"),mpatches.Patch(color=COLOR_VAT,label="VAT")],loc="lower right",fontsize=7,framealpha=0.9,facecolor="white")
                    ax.imshow(ov,aspect="equal")
            except Exception as e:
                ax.text(0.5,0.5,f"Error:\n{e}",ha="center",va="center")
            ax.set_title(f"L3 — {ttl}",fontsize=9,color="#1E3A5F",pad=6); ax.axis("off")

        fig.add_subplot(gs[2,:]).axis("off")
        _pdf_footer(fig,T)
        pdf.savefig(fig,facecolor="white"); plt.close(fig)
    return fp

# =============================================================================
# PDF EXPORT — CLINICAL
# Layout (top to bottom):
#   1. Header
#   2. Metrics table (left) + Percentile visualization (right)
#   3. Clinical profile cards (full width)
#   4. Lab values table (full width)
#   5. Footer
# =============================================================================
def export_pdf_clinical(row, lang_key, ff_value, extra, lab_df, score2, esc_cat,
                        patient_id, date_val, height_m, viz_mode="bar"):
    T=LANG[lang_key]
    fp=os.path.join(PDF_OUTPUT_DIR,
        f"BodyComp_{T['role_clin']}_{patient_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    def sf(k):
        try: return float(row[k])
        except: return None
    with PdfPages(fp) as pdf:
        fig=plt.figure(figsize=(11.69,16.54)); fig.patch.set_facecolor("white")
        # 4 rows: metrics+percentile / clinical profile / lab values / footer space
        gs=gridspec.GridSpec(4,2,figure=fig,
                             height_ratios=[1.1, 0.7, 1.0, 0.05],
                             hspace=0.5,wspace=0.3,
                             left=0.06,right=0.97,top=0.925,bottom=0.04)
        _pdf_header(fig,T,patient_id,date_val,height_m,T["role_clin"])

        # Row 0: Metrics table (left) + Percentile visualization (right)
        _pdf_metrics_table(fig.add_subplot(gs[0,0]), row, T, ff_value, extra, score2, esc_cat)
        ax_viz = fig.add_subplot(gs[0,1])
        if viz_mode in ["Normalverteilung","Normal Distribution"]:
            _pdf_normal_distribution(ax_viz, row, T, lang_key, ff_value)
        else:
            _pdf_bar_chart(ax_viz, row, T, lang_key, ff_value)

        # Row 1: Clinical profile — styled cards grid
        # Uses figure-level coordinates to avoid axes overlap issues
        ax_p=fig.add_subplot(gs[1,:]); ax_p.axis("off")

        # Get axes bounding box in figure coordinates for precise placement
        fig.canvas.draw()
        bbox=ax_p.get_position()
        x0f,y0f,wf,hf = bbox.x0, bbox.y0, bbox.width, bbox.height

        # Section title bar (top 15% of row)
        title_h = hf * 0.15
        fig.add_artist(plt.Rectangle((x0f, y0f+hf-title_h), wf, title_h,
                       transform=fig.transFigure, facecolor="#EFF6FF", edgecolor="none", zorder=2))
        fig.add_artist(plt.Rectangle((x0f, y0f+hf-title_h), wf*0.003, title_h,
                       transform=fig.transFigure, facecolor="#00AEEF", edgecolor="none", zorder=3))
        fig.text(x0f+wf*0.012, y0f+hf-title_h*0.5,
                 f"{T['metab_profile']} / {T['cardio_profile']}",
                 fontsize=9, fontweight="bold", color="#1E3A5F", va="center", zorder=4)

        # Build list of profile cards
        lines=[]
        if extra:
            if extra.get("bmi"):   lines.append(("BMI", f"{extra['bmi']:.1f} kg/m²", T["bmi_normal"]))
            if extra.get("waist"): lines.append((T["bauchumfang"], f"{extra['waist']:.0f} cm", T["waist_ref"]))
        vs=sf("vat_sat_ratio")
        if vs: lines.append(("VAT/SAT Ratio", f"{vs:.3f}", T["vat_sat_risk"]))
        if extra and extra.get("systolic") and extra.get("diastolic"):
            lines.append((T["bp"], f"{extra['systolic']:.0f}/{extra['diastolic']:.0f} mmHg", ""))
        if score2:
            lines.append(("SCORE2", f"{score2:.1f}%",
                          f"{T['esc_cat']}: {T.get(esc_cat, '—')}   ({T['esc_guidelines']})"))

        # Cards area: below title bar, in figure coords
        cards_area_y0 = y0f
        cards_area_h  = hf - title_h - hf*0.03   # small gap below title
        cards_area_y0_actual = y0f

        cols_   = 3
        pad_x   = wf * 0.01
        pad_y   = cards_area_h * 0.05
        card_w  = (wf - pad_x*(cols_+1)) / cols_
        card_h_ = min(cards_area_h * 0.42, 0.055)  # cap height
        gap_y   = card_h_ + cards_area_h * 0.08

        for idx,(label,value,note) in enumerate(lines):
            ci = idx % cols_
            ri = idx // cols_
            cx = x0f + pad_x + ci*(card_w + pad_x)
            cy = (y0f + hf - title_h - hf*0.04) - (ri+1)*gap_y

            # Card
            fig.add_artist(plt.Rectangle((cx, cy), card_w, card_h_,
                           transform=fig.transFigure,
                           facecolor="white", edgecolor="#BFDBFE", linewidth=0.6, zorder=2))
            # Left accent bar
            fig.add_artist(plt.Rectangle((cx, cy), card_w*0.008, card_h_,
                           transform=fig.transFigure,
                           facecolor="#00AEEF", edgecolor="none", zorder=3))
            # Label (top of card)
            fig.text(cx + card_w*0.03, cy + card_h_*0.78, label,
                     fontsize=6.5, color=TEXT_MUTED, fontweight="bold",
                     va="center", transform=fig.transFigure, zorder=4)
            # Value (middle)
            fig.text(cx + card_w*0.03, cy + card_h_*0.42, value,
                     fontsize=9, color="#1E3A5F", fontweight="bold",
                     va="center", transform=fig.transFigure, zorder=4)
            # Note (bottom)
            if note:
                fig.text(cx + card_w*0.03, cy + card_h_*0.12, note,
                         fontsize=6, color=TEXT_MUTED,
                         va="center", transform=fig.transFigure, zorder=4)

        ax_p.set_xlim(0,1); ax_p.set_ylim(0,1)

        # Row 2: Lab values table
        ax_l=fig.add_subplot(gs[2,:]); ax_l.axis("off")
        if lab_df is not None and not lab_df.empty:
            ax_l.add_patch(plt.Rectangle((0,0.88),1,0.12,transform=ax_l.transAxes,facecolor="#EFF6FF",edgecolor="none"))
            ax_l.add_patch(plt.Rectangle((0,0.88),0.003,0.12,transform=ax_l.transAxes,facecolor="#00AEEF",edgecolor="none"))
            ax_l.text(0.015,0.94,"Laborwerte",transform=ax_l.transAxes,
                      fontsize=9,fontweight="bold",color="#1E3A5F",va="center")
            lt=ax_l.table(cellText=lab_df.head(14).values.tolist(),
                          colLabels=lab_df.columns.tolist(),
                          loc="center",cellLoc="center",
                          bbox=[0,0,1,0.86])
            _style_tbl(lt); lt.set_fontsize(7); lt.scale(1,1.15)
        else:
            ax_l.text(0.5,0.5,"—",ha="center",va="center",color="#94A3B8",fontsize=10)

        fig.add_subplot(gs[3,:]).axis("off")
        _pdf_footer(fig,T)
        pdf.savefig(fig,facecolor="white"); plt.close(fig)
    return fp

# =============================================================================
# DASHBOARD
# =============================================================================
def _st(text):
    return (f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;'
            f'color:{KSW_BLUE};margin:24px 0 12px 0;padding-bottom:8px;'
            f'border-bottom:2px solid {BORDER};">{text}</div>')

def section_title(text):
    return pn.pane.HTML(_st(text), sizing_mode="stretch_width")

def build_dashboard():
    try:
        row,df=load_metrics(CSV_PATH); print(f"[OK] CSV loaded: {CSV_PATH}",flush=True)
    except Exception as e:
        print(f"[ERROR] {e}",flush=True); raise

    patient_id=str(row.get("patient_id","Unknown"))
    date_val=str(row.get("date",""))
    height_m=float(row.get("height_m",0))

    def sf(k):
        try: return float(row[k])
        except: return None
    def ss(k,d=1):
        v=sf(k); return f"{v:.{d}f}" if v is not None else "-"

    lang_select=pn.widgets.RadioButtonGroup(options=["DE","EN"],value="DE",button_type="light",width=120)
    role_select=pn.widgets.RadioButtonGroup(options=["Radiologie","Klinisch"],value="Klinisch",button_type="default",width=200)
    viz_select =pn.widgets.RadioButtonGroup(options=["Normalverteilung","Perzentilbalken"],value="Normalverteilung",button_type="light",width=260)

    header=pn.pane.HTML(
        f'<div style="padding:20px 0 12px 0;border-bottom:3px solid {KSW_BLUE};margin-bottom:4px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">'
        f'<div>'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;color:{KSW_BLUE};margin-bottom:6px;font-weight:700;">Body Composition Analysis — ZHAW x KSW</div>'
        f'<div style="font-size:26px;font-weight:700;color:{TEXT_DARK};">{patient_id}</div>'
        f'<div style="font-size:12px;color:{TEXT_MUTED};font-family:monospace;margin-top:4px;">Date: {date_val} &nbsp;·&nbsp; Height: {height_m:.2f} m</div>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:20px;padding-right:8px;">'
        f'{ZHAW_IMG_TAG}{KSW_IMG_TAG}'
        f'</div></div></div>',
        sizing_mode="stretch_width")

    def metric_card(label,value,unit,color=KSW_BLUE):
        return pn.pane.HTML(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;'
            f'padding:18px 20px;min-width:140px;box-shadow:0 1px 4px rgba(0,0,0,0.05);border-top:3px solid {color};">'
            f'<div style="font-family:monospace;font-size:26px;font-weight:600;color:{color};">{value}</div>'
            f'<div style="font-size:10px;color:{TEXT_MUTED};margin-top:2px;">{unit}</div>'
            f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:#94A3B8;margin-top:6px;">{label}</div>'
            f'</div>',sizing_mode="stretch_width")

    cards_row1=pn.Row(
        metric_card("SAT Area",     ss("sat_cm2"),         "cm²", COLOR_SAT),
        metric_card("VAT Area",     ss("vat_cm2"),         "cm²", COLOR_VAT),
        metric_card("IMAT %",       ss("imat_pct"),        "%",   COLOR_IMAT),
        metric_card("Muscle Area",  ss("sma_cm2"),         "cm²", COLOR_MUSCLE),
        metric_card("VAT/SAT Ratio",ss("vat_sat_ratio",3), "",    "#7C3AED"),
        sizing_mode="stretch_width")
    cards_row2=pn.Row(
        metric_card("SMI",      ss("smi"),      "cm²/m²",KSW_BLUE),
        metric_card("SAT Index",ss("sat_index"),"cm²/m²",COLOR_SAT),
        metric_card("VAT Index",ss("vat_index"),"cm²/m²",COLOR_VAT),
        sizing_mode="stretch_width")

    viz_pane     =pn.pane.Matplotlib(plt.figure(),tight=True,sizing_mode="stretch_width")
    summary_pane =pn.pane.HTML("",sizing_mode="stretch_width")
    section_viz  =pn.pane.HTML("",sizing_mode="stretch_width")
    section_sum  =pn.pane.HTML("",sizing_mode="stretch_width")
    export_btn   =pn.widgets.Button(name="PDF exportieren",button_type="primary",width=180)
    export_status=pn.pane.HTML("",sizing_mode="stretch_width")

    age_input      =pn.widgets.IntInput(name="Alter (Jahre)",value=0,start=0,end=120,width=150)
    weight_input   =pn.widgets.FloatInput(name="Gewicht (kg)",value=0.0,start=0.0,width=150)
    waist_input    =pn.widgets.FloatInput(name="Bauchumfang (cm)",value=0.0,start=0.0,width=150)
    systolic_input =pn.widgets.IntInput(name="Blutdruck syst. (mmHg)",value=0,start=0,width=150)
    diastolic_input=pn.widgets.IntInput(name="Blutdruck diast. (mmHg)",value=0,start=0,width=150)
    score2_input   =pn.widgets.FloatInput(name="SCORE2 Wert (%)",value=0.0,start=0.0,end=100.0,step=0.1,width=180)
    ff_input       =pn.widgets.FloatInput(name="Fat Fraction (FF) %",value=0.0,start=0.0,end=100.0,width=180)
    ff_note        =pn.pane.HTML(f'<div style="font-size:10px;color:#D97706;padding:4px 0;">⚠ Referenzwerte Platzhalter — werden durch KSW-Daten ersetzt</div>',sizing_mode="stretch_width")
    bmi_display    =pn.pane.HTML("",sizing_mode="stretch_width")
    score2_display =pn.pane.HTML("",sizing_mode="stretch_width")
    profiles_pane  =pn.pane.HTML("",sizing_mode="stretch_width")
    score2_state   ={"value":None,"cat":None}

    def update_widget_labels(lang):
        T=LANG[lang]
        age_input.name=T["age"]; weight_input.name=T["weight"]
        waist_input.name=T["bauchumfang"]+" (cm)"
        systolic_input.name=T["bp_systolic"]; diastolic_input.name=T["bp_diastolic"]
        score2_input.name=T["score2_input_lbl"]; ff_input.name=T["ff_label"]
        ff_note.object=f'<div style="font-size:10px;color:#D97706;padding:4px 0;">{T["ff_warning"]}</div>'
        lab_pdf_upload.name=T["lab_pdf_upload"]; lab_csv_upload.name=T["lab_csv_upload"]

    def update_profiles(event=None):
        lang=lang_select.value; T=LANG[lang]
        w=weight_input.value; bmi=w/(height_m**2) if w>0 and height_m>0 else None
        if bmi:
            bmi_display.object=(f'<div style="background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;'
                                f'padding:10px 16px;margin-top:8px;">'
                                f'<span style="color:{TEXT_MUTED};font-size:11px;">BMI: </span>'
                                f'<span style="color:{KSW_BLUE};font-size:16px;font-weight:600;">{bmi:.1f} kg/m²</span></div>')
        else: bmi_display.object=""
        # SCORE2: physician enters the value, we only classify
        s2_val = score2_input.value if score2_input.value > 0 else None
        age    = age_input.value
        cat    = classify_score2(s2_val, age) if s2_val else None
        score2_state["value"] = s2_val; score2_state["cat"] = cat
        ec={"esc_low":"#16A34A","esc_moderate":"#D97706","esc_high":"#DC2626"}
        if s2_val and cat:
            col=ec.get(cat,TEXT_MUTED)
            score2_display.object=(f'<div style="background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;'
                                   f'padding:10px 16px;margin-top:8px;display:flex;gap:20px;align-items:center;">'
                                   f'<div><span style="color:{TEXT_MUTED};font-size:11px;">SCORE2: </span>'
                                   f'<span style="color:{col};font-size:18px;font-weight:600;">{s2_val:.1f}%</span></div>'
                                   f'<div><span style="color:{TEXT_MUTED};font-size:11px;">ESC: </span>'
                                   f'<span style="color:{col};font-size:14px;font-weight:600;">{T.get(cat,"—")}</span></div>'
                                   f'<div style="font-size:10px;color:#94A3B8;">{T["esc_guidelines"]}</div></div>')
        else:
            score2_display.object=""
        profiles_pane.object=(
            metabolic_profile_html(row,waist_input.value if waist_input.value>0 else None,bmi,lang)+
            cardiovascular_profile_html(score2_state["value"],score2_state["cat"],
                                        systolic_input.value,diastolic_input.value,lang))

    for w in [weight_input,waist_input,age_input,systolic_input,diastolic_input,score2_input]:
        w.param.watch(update_profiles,"value")

    score2_hint=pn.pane.HTML(
        f'<div style="font-size:10px;color:{TEXT_MUTED};padding-top:4px;">'
        f'Vom Arzt mit offiziellem ESC-Rechner berechnet (ESC Guidelines 2021)</div>',
        sizing_mode="stretch_width")
    patient_inputs=pn.Column(
        pn.Row(age_input,weight_input,waist_input),
        pn.Row(systolic_input,diastolic_input),
        pn.Row(score2_input,score2_hint),
        bmi_display,score2_display,sizing_mode="stretch_width")

    lab_pdf_upload=pn.widgets.FileInput(accept=".pdf",name="KSW Laborbefund PDF hochladen")
    lab_csv_upload=pn.widgets.FileInput(accept=".csv",name="oder CSV hochladen")
    lab_pane      =pn.pane.HTML("",sizing_mode="stretch_width")
    lab_df_state  ={"df":None}

    def render_lab_table(df_lab):
        rh=""
        for _,r in df_lab.iterrows():
            flag=str(r.get("Flag","")); is_flag=flag in ["*","H","L","!","HH","LL"]
            rb="#FFF1F2" if is_flag else "transparent"
            fh=(f"<span style='background:#FEE2E2;color:#DC2626;border:1px solid #FECACA;"
                f"border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;'>{flag}</span>") if is_flag else ""
            vc="#DC2626" if is_flag else TEXT_DARK
            rh+=(f'<tr style="background:{rb};border-bottom:1px solid {BORDER};">'
                 f'<td style="padding:10px 16px;font-size:12px;color:{TEXT_DARK};width:35%;">{r.get("Untersuchung","")}</td>'
                 f'<td style="padding:10px 16px;font-size:12px;font-weight:600;color:{vc};font-family:monospace;width:15%;">{r.get("Resultat","")}</td>'
                 f'<td style="padding:10px 16px;font-size:11px;color:{TEXT_MUTED};width:10%;">{r.get("Einheit","")}</td>'
                 f'<td style="padding:10px 16px;font-size:11px;color:{TEXT_MUTED};width:25%;">{r.get("Referenzbereich","")}</td>'
                 f'<td style="padding:10px 16px;width:15%;">{fh}</td></tr>')
        return (f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;overflow:hidden;margin-top:8px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
                f'<table style="width:100%;border-collapse:collapse;">'
                f'<thead><tr style="background:{BG_ALT};border-bottom:2px solid {BORDER};">'
                f'<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};width:35%;">Untersuchung</th>'
                f'<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};width:15%;">Resultat</th>'
                f'<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};width:10%;">Einheit</th>'
                f'<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};width:25%;">Referenzbereich</th>'
                f'<th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{TEXT_MUTED};width:15%;">Flag</th>'
                f'</tr></thead><tbody>{rh}</tbody></table></div>')

    def on_lab_pdf_upload(event):
        val=lab_pdf_upload.value
        if val is None: return
        try:
            pb=val if isinstance(val,bytes) else (val.encode("latin-1") if isinstance(val,str) else bytes(val))
            df_lab,err=parse_ksw_lab_pdf(pb)
            if err: lab_pane.object=f'<div style="color:#DC2626;padding:8px;">Fehler: {err}</div>'; return
            lab_df_state["df"]=df_lab; n=len(df_lab); flagged=len(df_lab[df_lab["Flag"]!=""]) if "Flag" in df_lab.columns else 0
            T=LANG[lang_select.value]
            lab_pane.object=(f'<div style="color:#16A34A;font-size:11px;padding:4px 0 8px 0;">✓ {n} {T["lab_parsed"]}, {flagged} {T["lab_outside"]}</div>'
                             +render_lab_table(df_lab))
        except Exception as e:
            lab_pane.object=f'<div style="color:#DC2626;padding:8px;">Fehler: {e}</div>'

    def on_lab_csv_upload(event):
        if lab_csv_upload.value is None: return
        try:
            c=lab_csv_upload.value
            df_lab=pd.read_csv(io.BytesIO(c) if isinstance(c,bytes) else io.StringIO(c),sep=None,engine="python")
            lab_df_state["df"]=df_lab; lab_pane.object=render_lab_table(df_lab)
        except Exception as e:
            lab_pane.object=f'<div style="color:#DC2626;padding:8px;">Fehler: {e}</div>'

    lab_pdf_upload.param.watch(on_lab_pdf_upload,"value")
    lab_pdf_upload.param.watch(on_lab_pdf_upload,"filename")
    lab_csv_upload.param.watch(on_lab_csv_upload,"value")

    seg_toggle=pn.widgets.CheckBoxGroup(name="Segmentierungen",value=["SAT","VAT","Muscle"],
        options=["SAT","VAT","Muscle","IMAT"],inline=True)
    try:    _max_z=nib.load(WATER_NII_PATH).shape[2]-1
    except: _max_z=300
    z_slider   =pn.widgets.IntSlider(name="L3 Z-Index",value=L3_Z_INDEX,
                                     start=max(0,L3_Z_INDEX-15),end=min(_max_z,L3_Z_INDEX+15),step=1,width=300)
    z_minus_btn=pn.widgets.Button(name="-1",button_type="light",width=45)
    z_plus_btn =pn.widgets.Button(name="+1",button_type="light",width=45)
    zfi,zoi=get_fat_z_index(WATER_NII_PATH,FAT_NII_PATH,L3_Z_INDEX)
    z_display=pn.pane.HTML(
        f'<span style="color:{TEXT_MUTED};font-size:11px;">Water Z={L3_Z_INDEX} | Fat Z={zfi}'
        f'{f" (offset: {zoi:+d})" if zoi!=0 else ""}</span>',sizing_mode="stretch_width")
    current_z={"value":L3_Z_INDEX}
    mri_pane=pn.pane.Matplotlib(
        create_mri_figure_selective(WATER_NII_PATH,FAT_NII_PATH,SEG_NRRD_PATH,L3_Z_INDEX,["SAT","VAT","Muscle"]),
        tight=True,sizing_mode="fixed",width=1100,height=560)

    def update_mri(event=None):
        plt.close("all")
        mri_pane.object=create_mri_figure_selective(WATER_NII_PATH,FAT_NII_PATH,SEG_NRRD_PATH,current_z["value"],seg_toggle.value)
    def on_z_slider(event=None):
        current_z["value"]=z_slider.value; zf,zo=get_fat_z_index(WATER_NII_PATH,FAT_NII_PATH,z_slider.value)
        z_display.object=(f'<span style="color:{TEXT_MUTED};font-size:11px;">Water Z={z_slider.value} | Fat Z={zf}'
                          f'{f" (offset: {zo:+d})" if zo!=0 else ""}</span>')
        update_mri()

    seg_toggle.param.watch(update_mri,"value"); z_slider.param.watch(on_z_slider,"value")
    z_minus_btn.on_click(lambda e: setattr(z_slider,"value",max(z_slider.start,z_slider.value-1)))
    z_plus_btn.on_click( lambda e: setattr(z_slider,"value",min(z_slider.end,  z_slider.value+1)))

    seg_sec=pn.pane.HTML("",sizing_mode="stretch_width")
    metcardio_sec=pn.pane.HTML("",sizing_mode="stretch_width")
    patdata_sec=pn.pane.HTML("",sizing_mode="stretch_width")
    ff_sec=pn.pane.HTML("",sizing_mode="stretch_width")
    lab_sec=pn.pane.HTML("",sizing_mode="stretch_width")
    lab_hint_pane=pn.pane.HTML("",sizing_mode="stretch_width")
    all_res_sec=pn.pane.HTML("",sizing_mode="stretch_width")

    radiology_wrapper=pn.Column(
        seg_sec,pn.Row(seg_toggle),
        pn.Row(pn.pane.HTML(f'<span style="color:{TEXT_MUTED};font-size:11px;padding-top:8px;">Z-Slice anpassen:</span>'),
               z_minus_btn,z_slider,z_plus_btn,align="center",sizing_mode="stretch_width"),
        z_display,pn.Row(mri_pane,sizing_mode="stretch_width"),sizing_mode="stretch_width")

    clinical_wrapper=pn.Column(
        metcardio_sec,profiles_pane,
        patdata_sec,patient_inputs,
        ff_sec,pn.Column(ff_input,ff_note),
        lab_sec,lab_hint_pane,
        lab_pdf_upload,lab_csv_upload,lab_pane,
        sizing_mode="stretch_width")

    table_cols=["patient_id","date","height_m","sat_cm2","vat_cm2","imat_cm2","imat_pct",
                "sma_cm2","smi","sat_index","vat_index","vat_sat_ratio"]
    available=[c for c in table_cols if c in df.columns]
    table=pn.widgets.DataFrame(df[available].round(3),sizing_mode="stretch_width",height=90,show_index=False)

    def update_all(event=None):
        lang=lang_select.value; role=role_select.value; viz=viz_select.value
        ff_val=ff_input.value if ff_input.value>0 else None; T=LANG[lang]
        section_viz.object=_st(T["percentile"]); section_sum.object=_st(T["summary"])
        all_res_sec.object=_st(T["all_results"]); seg_sec.object=_st(T["seg_title"])
        metcardio_sec.object=_st(T["metab_cardio"]); patdata_sec.object=_st(T["patient_data"])
        ff_sec.object=_st(T["fat_frac_title"]); lab_sec.object=_st(T["lab_title"])
        lab_hint_pane.object=f'<div style="font-size:11px;color:{TEXT_MUTED};margin-bottom:8px;">{T["lab_hint"]}</div>'
        update_widget_labels(lang)
        plt.close("all")
        viz_pane.object=(create_normal_distribution_figure(row,lang,ff_val) if viz in ["Normalverteilung","Normal Distribution"]
                         else create_percentile_bar_figure(row,lang,ff_val))
        summary_pane.object=summary_table_html(row,lang,ff_val)
        export_btn.name=T["export_btn"]
        radiology_wrapper.visible=role in ["Radiologie","Radiology"]
        clinical_wrapper.visible =role in ["Klinisch","Clinical"]
        update_profiles()

    def on_export(event=None):
        lang=lang_select.value; role=role_select.value; ff_val=ff_input.value if ff_input.value>0 else None
        T=LANG[lang]
        export_status.object=f'<div style="color:#D97706;font-size:12px;padding:8px 0;">{T["exporting"]}</div>'
        try:
            pid=str(row.get("patient_id","Unknown")); dv=str(row.get("date",datetime.date.today())); hm=float(row.get("height_m",0))
            viz=viz_select.value
            if role in ["Radiologie","Radiology"]:
                path=export_pdf_radiology(row,lang,ff_val,pid,dv,hm,viz)
            else:
                w=weight_input.value
                extra={"bmi":w/(hm**2) if w>0 and hm>0 else None,
                       "waist":waist_input.value if waist_input.value>0 else None,
                       "systolic":systolic_input.value if systolic_input.value>0 else None,
                       "diastolic":diastolic_input.value if diastolic_input.value>0 else None} if w>0 else None
                path=export_pdf_clinical(row,lang,ff_val,extra,lab_df_state["df"],
                                         score2_state["value"],score2_state["cat"],pid,dv,hm,viz)
            export_status.object=f'<div style="color:#16A34A;font-size:12px;padding:8px 0;">{T["exported"]}: {os.path.basename(path)}</div>'
        except Exception as e:
            export_status.object=f'<div style="color:#DC2626;font-size:12px;padding:8px 0;">Error: {e}</div>'

    for w in [lang_select,role_select,viz_select]: w.param.watch(update_all,"value")
    ff_input.param.watch(update_all,"value"); export_btn.on_click(on_export)
    update_all()

    layout=pn.Column(
        pn.Row(header,pn.Spacer(),
               pn.Column(
                   pn.Row(pn.pane.HTML(f'<span style="color:{TEXT_MUTED};font-size:11px;">{LANG["DE"]["role_lbl"]}</span>'),role_select),
                   pn.Row(pn.pane.HTML(f'<span style="color:{TEXT_MUTED};font-size:11px;">{LANG["DE"]["view_lbl"]}</span>'),viz_select),
                   pn.Row(pn.pane.HTML(f'<span style="color:{TEXT_MUTED};font-size:11px;">{LANG["DE"]["lang_lbl"]}</span>'),lang_select),
               ),align="start"),
        section_title("Clinical Metrics"),
        cards_row1,cards_row2,
        section_viz,viz_pane,
        section_sum,summary_pane,
        pn.Row(export_btn,export_status,align="center"),
        all_res_sec,table,
        radiology_wrapper,clinical_wrapper,
        sizing_mode="stretch_width",margin=(0,40))

    # Light theme, no toggle
    return pn.template.FastListTemplate(
        title="Body Composition - ZHAW x KSW",
        main=[layout],
        accent_base_color=KSW_BLUE,
        header_background="#FFFFFF",
        theme="default",
        theme_toggle=False,
    )

# =============================================================================
# RUN
# =============================================================================
dashboard=build_dashboard()
dashboard.servable()

if __name__=="__main__":
    print("Starting Body Composition Dashboard...")
    print("Open http://localhost:5006 in your browser")
    pn.serve(dashboard,port=5006,show=True,title="Body Composition Dashboard")