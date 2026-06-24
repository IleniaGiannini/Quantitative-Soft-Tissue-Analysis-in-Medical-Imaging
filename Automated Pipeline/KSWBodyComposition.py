# -*- coding: utf-8 -*-
"""
KSWBodyComposition.py
=====================
3D Slicer Extension Module — KSW Body Composition Pipeline
ZHAW Bachelorarbeit 2026

Installation:
  1. Place this file in a folder, e.g.:
       <any path>\\KSWBodyComposition\\KSWBodyComposition.py
  2. Place run_pipeline.py, compute_metrics.py and dashboard.py
     in the SAME folder as this file (or adjust CONFIG below).
  3. In 3D Slicer: Edit -> Application Settings -> Modules
  4. Add the folder containing this file to "Additional module paths"
  5. Restart 3D Slicer
  6. Find module under: Modules -> KSW -> KSW Body Composition

  The VIBESegmentator conda environment must be installed separately.
  Set PYTHON_VIBE below to the correct python.exe path for your machine.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

import qt
import vtk
import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleWidget,
    ScriptedLoadableModuleLogic,
)

# =============================================================================
# CONFIG — only PYTHON_VIBE needs to be adjusted per machine.
# All scripts are resolved relative to this file automatically.
# =============================================================================

# Folder containing this module file — scripts must be in the same folder
_MODULE_DIR = Path(__file__).parent.resolve()

PIPELINE_SCRIPT  = str(_MODULE_DIR / "run_pipeline.py")
COMPUTE_SCRIPT   = str(_MODULE_DIR / "compute_metrics.py")
DASHBOARD_SCRIPT = str(_MODULE_DIR / "dashboard.py")

# !! Adjust this to your VIBESegmentator python.exe path !!
PYTHON_VIBE = r"C:\Users\<username>\anaconda3\envs\VIBESegmentator\python.exe"

# =============================================================================
# MODULE METADATA
# =============================================================================

class KSWBodyComposition(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title        = "KSW Body Composition"
        self.parent.categories   = ["KSW"]
        self.parent.dependencies = []
        self.parent.contributors = ["Luca Meier, Ilenia Giannini (ZHAW)"]
        self.parent.helpText     = """
            Automated body composition pipeline for DIXON MRI data.
            Extracts SAT, VAT, SMA, IMAT metrics at the L3 vertebral level.
            KSW / ZHAW Bachelorarbeit 2026.
        """
        self.parent.acknowledgementText = """
            Developed as part of the Bachelor Thesis at ZHAW School of Life Sciences.
            In collaboration with Kantonsspital Winterthur (KSW).
        """

# =============================================================================
# WIDGET (UI)
# =============================================================================

class KSWBodyCompositionWidget(ScriptedLoadableModuleWidget):

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = KSWBodyCompositionLogic()

        # ── Main scroll area ──────────────────────────────────────────────────
        mainWidget = qt.QWidget()
        mainLayout = qt.QVBoxLayout()
        mainWidget.setLayout(mainLayout)
        self.layout.addWidget(mainWidget)

        # ── Header ───────────────────────────────────────────────────────────
        headerLabel = qt.QLabel("KSW Body Composition Pipeline")
        headerLabel.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #003F8A; padding: 8px 0px;"
        )
        mainLayout.addWidget(headerLabel)

        subLabel = qt.QLabel("ZHAW Bachelorarbeit 2026 — Quantitative Soft-Tissue Analysis")
        subLabel.setStyleSheet("font-size: 10px; color: gray; padding-bottom: 10px;")
        mainLayout.addWidget(subLabel)

        mainLayout.addWidget(self._makeLine())

        # ── STEP 1 — Patient Selection ────────────────────────────────────────
        step1Box = qt.QGroupBox("Step 1 — Patient Selection")
        step1Box.setStyleSheet("QGroupBox { font-weight: bold; color: white; }")
        step1Layout = qt.QVBoxLayout()
        step1Box.setLayout(step1Layout)

        folderLayout = qt.QHBoxLayout()
        self.patientFolderEdit = qt.QLineEdit()
        self.patientFolderEdit.setPlaceholderText("Select patient folder...")
        browseBtn = qt.QPushButton("Browse...")
        browseBtn.setMaximumWidth(80)
        browseBtn.connect("clicked()", self.onBrowsePatient)
        folderLayout.addWidget(qt.QLabel("Patient folder:"))
        folderLayout.addWidget(self.patientFolderEdit)
        folderLayout.addWidget(browseBtn)
        step1Layout.addLayout(folderLayout)

        heightLayout = qt.QHBoxLayout()
        heightLayout.addWidget(qt.QLabel("Patient height (m):"))
        self.heightEdit = qt.QLineEdit("1.75")
        self.heightEdit.setMaximumWidth(80)
        heightLayout.addWidget(self.heightEdit)
        heightLayout.addStretch()
        step1Layout.addLayout(heightLayout)

        mainLayout.addWidget(step1Box)

        # ── STEP 2 — Run Pipeline ─────────────────────────────────────────────
        step2Box = qt.QGroupBox("Step 2 — Automated Pipeline")
        step2Box.setStyleSheet("QGroupBox { font-weight: bold; color: white; }")
        step2Layout = qt.QVBoxLayout()
        step2Box.setLayout(step2Layout)

        infoLabel2 = qt.QLabel("Runs: DICOM decompression → NIfTI conversion → VIBESegmentator")
        infoLabel2.setStyleSheet("font-size: 10px; color: gray;")
        infoLabel2.setWordWrap(True)
        step2Layout.addWidget(infoLabel2)

        self.runPipelineBtn = qt.QPushButton("Run Pipeline")
        self.runPipelineBtn.setStyleSheet(self._btnStyle("#003F8A"))
        self.runPipelineBtn.connect("clicked()", self.onRunPipeline)
        step2Layout.addWidget(self.runPipelineBtn)

        mainLayout.addWidget(step2Box)

        # ── STEP 3 — Load, Correct & IMAT ────────────────────────────────────
        step3Box = qt.QGroupBox("Step 3 — Load, Correct & IMAT")
        step3Box.setStyleSheet("QGroupBox { font-weight: bold; color: white; }")
        step3Layout = qt.QVBoxLayout()
        step3Box.setLayout(step3Layout)

        infoLabel3 = qt.QLabel(
            "Loads water.nii, fat.nii, ff.nii and seg.nii.gz into Slicer.\n"
            "Cleanup removes irrelevant segments.\n"
            "IMAT: threshold-based detection on fat image within muscle region.\n"
            "Then correct VAT & IMAT in Segment Editor below."
        )
        infoLabel3.setStyleSheet("font-size: 10px; color: gray;")
        infoLabel3.setWordWrap(True)
        step3Layout.addWidget(infoLabel3)

        self.loadSlicerBtn = qt.QPushButton("Load Images into Slicer")
        self.loadSlicerBtn.setStyleSheet(self._btnStyle("#1565C0"))
        self.loadSlicerBtn.connect("clicked()", self.onLoadSlicer)
        step3Layout.addWidget(self.loadSlicerBtn)

        self.cleanupBtn = qt.QPushButton("Cleanup Segments (remove irrelevant labels)")
        self.cleanupBtn.setStyleSheet(self._btnStyle("#1976D2"))
        self.cleanupBtn.connect("clicked()", self.onCleanup)
        step3Layout.addWidget(self.cleanupBtn)

        # IMAT threshold input + button
        imatLayout = qt.QHBoxLayout()
        imatLayout.addWidget(qt.QLabel("IMAT Fat Threshold:"))
        self.imatThresholdEdit = qt.QLineEdit("100")
        self.imatThresholdEdit.setMaximumWidth(60)
        self.imatThresholdEdit.setToolTip(
            "Fat intensity threshold for IMAT detection.\n"
            "Pixels above this value within the muscle mask are classified as IMAT.\n"
            "Typical range: 80-130. Default: 100."
        )
        imatLayout.addWidget(self.imatThresholdEdit)
        imatLayout.addWidget(qt.QLabel("(typical: 80-130)"))
        imatLayout.addStretch()
        step3Layout.addLayout(imatLayout)

        self.imatBtn = qt.QPushButton("Create IMAT Segment")
        self.imatBtn.setStyleSheet(self._btnStyle("#00695C"))
        self.imatBtn.connect("clicked()", self.onCreateIMAT)
        step3Layout.addWidget(self.imatBtn)

        mainLayout.addWidget(step3Box)

        # ── SEGMENT EDITOR (embedded) ─────────────────────────────────────────
        segEditorBox = qt.QGroupBox("Segment Editor — Correct VAT & IMAT")
        segEditorBox.setStyleSheet("QGroupBox { font-weight: bold; color: white; }")
        segEditorLayout = qt.QVBoxLayout()
        segEditorBox.setLayout(segEditorLayout)

        segEditorInfo = qt.QLabel(
            "Use the Segment Editor below to manually correct VAT and IMAT.\n"
            "Switch source volume to 'fat' for VAT/IMAT correction.\n"
            "Use 'Threshold', 'Paint', 'Erase' and 'Logical operators' tools."
        )
        segEditorInfo.setStyleSheet("font-size: 10px; color: gray;")
        segEditorInfo.setWordWrap(True)
        segEditorLayout.addWidget(segEditorInfo)

        # Embed the Segment Editor widget
        try:
            import qSlicerSegmentationsModuleWidgetsPythonQt as segWidgets
            self.segmentEditorWidget = segWidgets.qMRMLSegmentEditorWidget()
            self.segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
            segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
            self.segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
            self.segmentEditorWidget.setMaximumNumberOfUndoStates(10)
            segEditorLayout.addWidget(self.segmentEditorWidget)
        except Exception as e:
            fallbackLabel = qt.QLabel(
                f"Segment Editor widget could not be embedded: {e}\n"
                "Please use Modules → Segment Editor manually."
            )
            fallbackLabel.setStyleSheet("color: gray; font-size: 10px;")
            fallbackLabel.setWordWrap(True)
            segEditorLayout.addWidget(fallbackLabel)
            self.segmentEditorWidget = None

        # Quick source volume switcher
        volSwitchLayout = qt.QHBoxLayout()
        volSwitchLayout.addWidget(qt.QLabel("Source volume:"))
        self.switchWaterBtn = qt.QPushButton("Water")
        self.switchWaterBtn.setMaximumWidth(80)
        self.switchWaterBtn.setStyleSheet(self._btnStyle("#455A64"))
        self.switchWaterBtn.connect("clicked()", lambda: self.onSwitchSourceVolume("water"))
        self.switchFatBtn = qt.QPushButton("Fat")
        self.switchFatBtn.setMaximumWidth(80)
        self.switchFatBtn.setStyleSheet(self._btnStyle("#455A64"))
        self.switchFatBtn.connect("clicked()", lambda: self.onSwitchSourceVolume("fat"))
        volSwitchLayout.addWidget(self.switchWaterBtn)
        volSwitchLayout.addWidget(self.switchFatBtn)
        volSwitchLayout.addStretch()
        segEditorLayout.addLayout(volSwitchLayout)

        mainLayout.addWidget(segEditorBox)

        # ── STEP 4 — Compute & Dashboard ─────────────────────────────────────
        step4Box = qt.QGroupBox("Step 4 — Compute Metrics & Dashboard")
        step4Box.setStyleSheet("QGroupBox { font-weight: bold; color: white; }")
        step4Layout = qt.QVBoxLayout()
        step4Box.setLayout(step4Layout)

        infoLabel4 = qt.QLabel(
            "Scroll to the L3 slice, click Auto-detect, then compute metrics."
        )
        infoLabel4.setStyleSheet("font-size: 10px; color: gray;")
        infoLabel4.setWordWrap(True)
        step4Layout.addWidget(infoLabel4)

        zLayout = qt.QHBoxLayout()
        zLayout.addWidget(qt.QLabel("L3 Z-Index:"))
        self.zEdit = qt.QLineEdit("130")
        self.zEdit.setMaximumWidth(80)
        zLayout.addWidget(self.zEdit)
        self.detectZBtn = qt.QPushButton("Auto-detect from cursor")
        self.detectZBtn.setMaximumWidth(180)
        self.detectZBtn.connect("clicked()", self.onDetectZ)
        zLayout.addWidget(self.detectZBtn)
        zLayout.addStretch()
        step4Layout.addLayout(zLayout)

        self.computeBtn = qt.QPushButton("Compute Metrics & Open Dashboard")
        self.computeBtn.setStyleSheet(self._btnStyle("#2E7D32"))
        self.computeBtn.connect("clicked()", self.onCompute)
        step4Layout.addWidget(self.computeBtn)

        mainLayout.addWidget(step4Box)

        # ── Status ───────────────────────────────────────────────────────────
        mainLayout.addWidget(self._makeLine())
        self.statusLabel = qt.QLabel("Ready.")
        self.statusLabel.setStyleSheet(
            "padding: 6px; font-size: 11px; color: #333; "
            "background: #F5F5F5; border-radius: 4px;"
        )
        self.statusLabel.setWordWrap(True)
        mainLayout.addWidget(self.statusLabel)
        mainLayout.addStretch()

    # ── UI Helpers ────────────────────────────────────────────────────────────

    def _makeLine(self):
        line = qt.QFrame()
        line.setFrameShape(qt.QFrame.HLine)
        line.setStyleSheet("color: #CCCCCC;")
        return line

    def _btnStyle(self, color):
        return (
            f"background-color: {color}; color: white; "
            f"padding: 10px; font-size: 12px; font-weight: bold; "
            f"border-radius: 4px; margin: 2px 0px;"
        )

    def setStatus(self, msg, color="#333"):
        self.statusLabel.setText(msg)
        self.statusLabel.setStyleSheet(
            f"padding: 6px; font-size: 11px; color: {color}; "
            f"background: #F5F5F5; border-radius: 4px;"
        )
        slicer.app.processEvents()

    # ── Handlers ─────────────────────────────────────────────────────────────

    def onBrowsePatient(self):
        folder = qt.QFileDialog.getExistingDirectory(
            None, "Select Patient Folder", str(Path.home())
        )
        if folder:
            self.patientFolderEdit.setText(folder)
            self.setStatus(f"Patient folder set: {Path(folder).name}")

    def onRunPipeline(self):
        patient = self.patientFolderEdit.text.strip()
        if not patient:
            slicer.util.errorDisplay("Please select a patient folder first!")
            return
        self.setStatus("Pipeline running in background...\nCheck terminal for progress.", "#1565C0")
        success = self.logic.runPipeline(patient)
        if success:
            self.setStatus(
                "Pipeline started! Watch the terminal for progress.\n"
                "When finished, click 'Load Images into Slicer'.", "#2E7D32"
            )
        else:
            self.setStatus("Pipeline failed to start!", "#C62828")

    def onLoadSlicer(self):
        patient = self.patientFolderEdit.text.strip()
        if not patient:
            slicer.util.errorDisplay("Please select a patient folder first!")
            return
        nifti_dir = Path(patient) / "output" / "nifti"
        self.setStatus("Loading images...", "#1565C0")
        success = self.logic.loadImages(nifti_dir)
        if success:
            # Update segment editor with loaded segmentation
            if self.segmentEditorWidget is not None:
                try:
                    seg_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
                    if seg_nodes:
                        self.segmentEditorWidget.setSegmentationNode(seg_nodes[0])
                    vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
                    for n in vol_nodes:
                        if n.GetName() == "water":
                            self.segmentEditorWidget.setSourceVolumeNode(n)
                            break
                except Exception as e:
                    print(f"[WARN] Could not update segment editor: {e}")
            # Enable horizontal slice intersection line to help find the L3 level
            try:
                sliceDisplayNodes = slicer.util.getNodesByClass("vtkMRMLSliceDisplayNode")
                for node in sliceDisplayNodes:
                    node.SetIntersectingSlicesVisibility(1)
                    node.SetIntersectingSlicesInteractive(False)
                    node.SetIntersectingSlicesLineThicknessMode(0)
                    node.SetIntersectingSlicesLineVisibility(0, True)   # horizontal — show
                    node.SetIntersectingSlicesLineVisibility(1, False)  # vertical  — hide
                print("[OK] Horizontal slice intersection line enabled")
            except Exception as e:
                print(f"[WARN] Could not enable slice intersection line: {e}")

            self.setStatus(
                "Images loaded!\n"
                "1. Click Cleanup Segments\n"
                "2. Click Create IMAT Segment\n"
                "3. Correct VAT & IMAT in Segment Editor below\n"
                "4. Click Compute Metrics", "#2E7D32"
            )
        else:
            self.setStatus("Could not load images! Run pipeline first.", "#C62828")

    def onCleanup(self):
        self.setStatus("Cleaning up segments...", "#1565C0")
        success = self.logic.cleanupSegments()
        if success:
            self.setStatus(
                "Cleanup done! Kept: Autochthon L/R, Iliopsoas L/R, Muscle, SAT, VAT.\n"
                "Next: Click 'Create IMAT Segment'.", "#2E7D32"
            )
        else:
            self.setStatus("No segmentation found! Load images first.", "#C62828")

    def onCreateIMAT(self):
        try:
            threshold = int(self.imatThresholdEdit.text.strip())
        except ValueError:
            threshold = 100
        self.setStatus(f"Creating IMAT segment (threshold={threshold})...", "#1565C0")
        success = self.logic.createIMATSegment(threshold)
        if success:
            # Switch source volume to fat for IMAT correction
            self.onSwitchSourceVolume("fat")
            self.setStatus(
                f"IMAT segment created (threshold={threshold})!\n"
                "Source volume switched to Fat for verification.\n"
                "Check the Segment Editor — adjust IMAT if needed.\n"
                "Use 'Logical operators > Intersect with Muscle' to refine.", "#2E7D32"
            )
        else:
            self.setStatus(
                "Could not create IMAT!\n"
                "Make sure Cleanup was run and Fat volume is loaded.", "#C62828"
            )

    def onSwitchSourceVolume(self, volume_name):
        """Switch the source volume in the embedded Segment Editor."""
        try:
            vol_node = slicer.util.getNode(volume_name)
            if self.segmentEditorWidget is not None:
                self.segmentEditorWidget.setSourceVolumeNode(vol_node)
            # Also set as background in viewers
            layoutManager = slicer.app.layoutManager()
            for viewName in ["Red", "Green", "Yellow"]:
                sliceWidget   = layoutManager.sliceWidget(viewName)
                compositeNode = sliceWidget.sliceLogic().GetSliceCompositeNode()
                compositeNode.SetBackgroundVolumeID(vol_node.GetID())
            self.setStatus(f"Source volume switched to: {volume_name}", "#2E7D32")
        except Exception as e:
            self.setStatus(f"Could not switch volume: {e}", "#C62828")

    def onDetectZ(self):
        try:
            layoutManager = slicer.app.layoutManager()
            sliceWidget   = layoutManager.sliceWidget("Red")
            sliceLogic    = sliceWidget.sliceLogic()
            offset        = sliceLogic.GetSliceOffset()

            nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
            if not nodes:
                slicer.util.errorDisplay("No volume loaded!")
                return

            volumeNode = nodes[0]
            rasToIjk   = vtk.vtkMatrix4x4()
            volumeNode.GetRASToIJKMatrix(rasToIjk)

            ras    = [0.0, 0.0, float(offset), 1.0]
            result = [0.0, 0.0, 0.0, 1.0]
            rasToIjk.MultiplyPoint(ras, result)
            z_index = int(round(result[2]))

            self.zEdit.setText(str(z_index))
            self.setStatus(
                f"Z-index detected: {z_index} (S={offset:.2f}mm)\n"
                f"Verify this is L3, then click Compute.", "#2E7D32"
            )
        except Exception as e:
            self.setStatus(f"Could not detect Z: {e}", "#C62828")

    def onCompute(self):
        patient = self.patientFolderEdit.text.strip()
        height  = self.heightEdit.text.strip()
        z       = self.zEdit.text.strip()

        if not patient:
            slicer.util.errorDisplay("Please select a patient folder first!")
            return
        if not height or not z:
            slicer.util.errorDisplay("Please enter height and Z-index!")
            return

        self.setStatus("Saving segmentation...", "#1565C0")
        self.logic.saveSegmentation(Path(patient) / "output" / "nifti")

        self.setStatus("Computing metrics & opening dashboard...", "#1565C0")
        success = self.logic.computeMetrics(patient, height, z)
        if success:
            self.setStatus(
                f"Done! Dashboard opening in browser.\n"
                f"Patient: {Path(patient).name} | Height: {height}m | Z: {z}",
                "#2E7D32"
            )
        else:
            self.setStatus("Error! Check Python console.", "#C62828")


# =============================================================================
# LOGIC
# =============================================================================

class KSWBodyCompositionLogic(ScriptedLoadableModuleLogic):

    KEEP_LABELS = {
        "Segment_59": "Autochthon_R",
        "Segment_60": "Autochthon_L",
        "Segment_61": "Iliopsoas_R",
        "Segment_62": "Iliopsoas_L",
        "Segment_65": "SAT",
        "Segment_66": "Muscle",
        "Segment_67": "VAT",
        "IMAT":       "IMAT",
    }

    def _clean_env(self):
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = ""
        env["PYTHONHOME"] = ""
        env["USERPROFILE"] = os.environ.get("USERPROFILE", str(Path.home()))
        env["HOMEPATH"]    = os.environ.get("HOMEPATH",    str(Path.home()))
        env["HOMEDRIVE"]   = os.environ.get("HOMEDRIVE",   "C:")
        env["APPDATA"]     = os.environ.get("APPDATA",     str(Path.home() / "AppData" / "Roaming"))
        env["TEMP"]        = os.environ.get("TEMP",        str(Path.home() / "AppData" / "Local" / "Temp"))
        env["TMP"]         = os.environ.get("TMP",         str(Path.home() / "AppData" / "Local" / "Temp"))
        env["PATH"] = ";".join([
            p for p in env.get("PATH", "").split(";")
            if "slicer" not in p.lower() and "3d slicer" not in p.lower()
        ])
        return env

    def runPipeline(self, patient_path):
        try:
            self._pipeline_process = subprocess.Popen(
                [PYTHON_VIBE, PIPELINE_SCRIPT, "--patient", patient_path],
                env=self._clean_env()
            )
            return True
        except Exception as e:
            print(f"[ERROR] Pipeline failed: {e}")
            return False

    def loadImages(self, nifti_dir):
        nifti_dir = Path(nifti_dir)
        loaded    = False

        for fname, name in [
            ("water.nii", "water"),
            ("fat.nii",   "fat"),
            ("ff.nii",    "ff"),
        ]:
            fpath = nifti_dir / fname
            if fpath.exists():
                node = slicer.util.loadVolume(str(fpath))
                node.SetName(name)
                loaded = True
                print(f"[OK] Loaded: {fname}")
            else:
                print(f"[INFO] Not found (optional): {fname}")

        seg_path = nifti_dir / "seg.nii.gz"
        if seg_path.exists():
            node = slicer.util.loadSegmentation(str(seg_path))
            node.SetName("seg")
            loaded = True
            print(f"[OK] Loaded: seg.nii.gz")

        try:
            layoutManager = slicer.app.layoutManager()
            waterNode     = slicer.util.getNode("water")
            for viewName in ["Red", "Green", "Yellow"]:
                sliceWidget   = layoutManager.sliceWidget(viewName)
                compositeNode = sliceWidget.sliceLogic().GetSliceCompositeNode()
                compositeNode.SetBackgroundVolumeID(waterNode.GetID())
            slicer.util.resetSliceViews()
        except Exception as e:
            print(f"[WARN] Could not set background: {e}")

        return loaded

    def cleanupSegments(self):
        nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        if not nodes:
            return False

        seg_node     = nodes[0]
        segmentation = seg_node.GetSegmentation()

        # Pass 1: collect IDs to remove and IDs to rename
        to_remove = []
        to_rename = []
        for i in range(segmentation.GetNumberOfSegments()):
            seg_id   = segmentation.GetNthSegmentID(i)
            segment  = segmentation.GetSegment(seg_id)
            seg_name = segment.GetName()
            if seg_name in self.KEEP_LABELS:
                to_rename.append((seg_id, seg_name, self.KEEP_LABELS[seg_name]))
            elif seg_name == "IMAT":
                # Keep IMAT if already created
                pass
            else:
                to_remove.append(seg_id)

        # Pass 2: remove irrelevant segments
        for seg_id in to_remove:
            seg_name = segmentation.GetSegment(seg_id).GetName()
            segmentation.RemoveSegment(seg_id)
            print(f"[REMOVED] {seg_name}")

        # Pass 3: rename remaining segments
        for seg_id, old_name, new_name in to_rename:
            seg = segmentation.GetSegment(seg_id)
            if seg is not None:
                seg.SetName(new_name)
                print(f"[OK] Renamed: {old_name} -> {new_name}")

        return True

    def createIMATSegment(self, threshold=100):
        """
        Create IMAT segment:
        1. Apply fat threshold within the combined muscle mask
        2. Subtract already-segmented structures (VAT, SAT etc.)
        3. Intersect with filled muscle region to keep only intra-muscular fat
        """
        try:
            import numpy as np
            from scipy.ndimage import binary_fill_holes

            # Get segmentation node
            seg_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
            if not seg_nodes:
                print("[ERROR] No segmentation node found!")
                return False
            seg_node     = seg_nodes[0]
            segmentation = seg_node.GetSegmentation()

            # Get fat volume
            try:
                fat_node = slicer.util.getNode("fat")
            except Exception:
                print("[ERROR] Fat volume not found! Load images first.")
                return False

            fat_array = slicer.util.arrayFromVolume(fat_node)

            # Export segmentation to labelmap to get numpy array
            labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
            slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
                seg_node, labelmap_node,
                slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY
            )
            seg_array = slicer.util.arrayFromVolume(labelmap_node)

            # Find label values for muscle segments dynamically
            muscle_label_values = []
            for i in range(segmentation.GetNumberOfSegments()):
                seg_id  = segmentation.GetNthSegmentID(i)
                seg_obj = segmentation.GetSegment(seg_id)
                name    = seg_obj.GetName()
                if name in ["Autochthon_R", "Autochthon_L",
                            "Iliopsoas_R",  "Iliopsoas_L", "Muscle"]:
                    muscle_label_values.append(i + 1)

            if not muscle_label_values:
                print("[WARN] No muscle segments found! Run Cleanup first.")
                slicer.mrmlScene.RemoveNode(labelmap_node)
                return False

            # Build masks
            muscle_mask   = np.isin(seg_array, muscle_label_values)
            muscle_filled = binary_fill_holes(muscle_mask)  # fills hollow regions
            already_seg   = seg_array > 0

            # IMAT = fat above threshold, within filled muscle, not already segmented
            imat_mask = (
                muscle_filled &
                (fat_array > threshold) &
                ~already_seg
            )

            n_imat = int(np.sum(imat_mask))
            print(f"[INFO] IMAT pixels found: {n_imat} (threshold={threshold})")

            if n_imat == 0:
                print("[WARN] No IMAT pixels found. Try lowering the threshold.")
                slicer.mrmlScene.RemoveNode(labelmap_node)
                return False

            # Create IMAT labelmap volume
            imat_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
            slicer.util.updateVolumeFromArray(imat_labelmap, imat_mask.astype(np.uint8))
            imat_labelmap.CopyOrientation(fat_node)

            # Add empty IMAT segment
            imat_seg_id = segmentation.AddEmptySegment("IMAT")
            imat_seg    = segmentation.GetSegment(imat_seg_id)
            imat_seg.SetColor(0.13, 0.83, 0.65)  # Teal #22D3A5

            # Import IMAT labelmap into segmentation
            slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
                imat_labelmap, seg_node
            )

            # Cleanup temporary nodes
            slicer.mrmlScene.RemoveNode(labelmap_node)
            slicer.mrmlScene.RemoveNode(imat_labelmap)

            # Remove any LabelMapVolume nodes that were created as side effects
            labelmap_nodes = slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode")
            for lm_node in labelmap_nodes:
                slicer.mrmlScene.RemoveNode(lm_node)

            # Find the newly created segment and rename it to IMAT
            # It will be the last segment that is not already named
            for i in range(segmentation.GetNumberOfSegments()):
                seg_id  = segmentation.GetNthSegmentID(i)
                seg_obj = segmentation.GetSegment(seg_id)
                name    = seg_obj.GetName()
                # Rename if it looks like an auto-generated name
                if name.startswith("Segment_") or name == "IMAT":
                    seg_obj.SetName("IMAT")
                    seg_obj.SetColor(0.13, 0.83, 0.65)  # Teal
                    print(f"[OK] Renamed segment to IMAT")
                    break

            print(f"[OK] IMAT segment created with {n_imat} pixels")
            return True

        except Exception as e:
            print(f"[ERROR] createIMATSegment: {e}")
            import traceback
            traceback.print_exc()
            return False

    def saveSegmentation(self, nifti_dir):
        nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        if not nodes:
            print("[WARN] No segmentation to save!")
            return False
        seg_node = nodes[0]
        seg_path = str(Path(nifti_dir) / "seg_corrected.seg.nrrd")
        slicer.util.saveNode(seg_node, seg_path)
        print(f"[OK] Segmentation saved: {seg_path}")
        return True

    def computeMetrics(self, patient_path, height, z_index):
        try:
            subprocess.Popen(
                [
                    PYTHON_VIBE, COMPUTE_SCRIPT,
                    "--patient", patient_path,
                    "--height",  str(height),
                    "--z",       str(z_index),
                    "--dashboard"
                ],
                env=self._clean_env()
            )
            return True
        except Exception as e:
            print(f"[ERROR] Compute failed: {e}")
            return False