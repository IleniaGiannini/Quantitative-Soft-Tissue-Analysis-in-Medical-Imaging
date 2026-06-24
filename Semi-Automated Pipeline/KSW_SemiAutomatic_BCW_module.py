# =============================================================================
# 3D Slicer Scripted Module: KSW Semi-Automatic Body Composition Workflow
# =============================================================================
#
# Bachelor Thesis Project – ZHAW School of Life Sciences and Facility Management
# Collaboration partner: Kantonsspital Winterthur (KSW)
# Author: Ilenia Giannini, Luca Meier
#
# Purpose
# -------
# This scripted 3D Slicer module supports a semi-automatic workflow for
# MRI-based body composition analysis at the level of the third lumbar
# vertebra (L3). It was developed for Dixon MRI data and focuses on the
# extraction of clinically relevant 2D body composition metrics from a
# selected axial slice.
#
# Supported tissue compartments
# -----------------------------
# - Subcutaneous adipose tissue (SAT)
# - Visceral adipose tissue (VAT)
# - Skeletal muscle / skeletal muscle area (SMA)
# - Intramuscular adipose tissue (IMAT)
#
# Main workflow
# -------------
# 1. Load Dixon fat and water images, either as image files or DICOM folders.
# 2. Create or select a segmentation node.
# 3. Select the processing mode:
#       - 2D image mode: the first/only slice is used.
#       - 3D single-slice mode: the L3 slice is selected in the Red slice view.
# 4. Segment SAT and VAT using threshold-based single-slice segmentation.
# 5. Segment/refine skeletal muscle manually using the water image.
# 6. Derive IMAT automatically from fat-image intensities inside the muscle mask.
# 7. Compute 2D metrics such as SAT area, VAT area, SMA, SMI, VAT/SAT ratio,
#    SAT/VAT indices and IMAT percentage.
# 8. Export images, segmentation and metrics to the dashboard output folder.
# 9. Launch the dashboard for visualization and report generation.
#
# Notes and limitations
# ---------------------
# - The analysis is slice-based. In 3D mode, only the selected L3 slice is
#   segmented and quantified, not the full 3D volume.
# - Threshold values are project-/dataset-specific and may require adaptation
#   for other scanners, sequences or intensity scalings.
# - The module is intended as a research workflow prototype and does not replace
#   radiological review or clinical decision-making.
#
# File/class naming requirement for 3D Slicer
# -------------------------------------------
# The filename must match the main module class name:
#     KSW_SemiAutomatic_BCW_module.py
#     class KSW_SemiAutomatic_BCW_module(...)
# =============================================================================

# Standard library imports
import os
import csv
import time
import shutil
import subprocess
import webbrowser

# Numerical processing
import numpy as np

# 3D Slicer / Qt / VTK imports
import qt
import ctk
import vtk
import slicer
from slicer.ScriptedLoadableModule import *


# =============================================================================
# MODULE METADATA
# =============================================================================

class KSW_SemiAutomatic_BCW_module(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "KSW Semi-automatic MRI Body Composition Workflow"
        parent.categories = ["Segmentation"]
        parent.dependencies = ["Segmentations", "SegmentEditor"]
        parent.contributors = ["Ilenia Giannini, Luca Meier (ZHAW)"]
        parent.helpText = """
        Semi-automatic workflow for 2D/3D body composition segmentation in 3D Slicer.
        """
        self.parent.acknowledgementText = """
            Developed as part of the Bachelor Thesis at ZHAW School of Life Sciences.
            In collaboration with Kantonsspital Winterthur (KSW).
        """
    


# =============================================================================
# WIDGET / USER INTERFACE
# =============================================================================

class KSW_SemiAutomatic_BCW_moduleWidget(ScriptedLoadableModuleWidget):
    """
    User interface for the body composition workflow.

    This widget contains all input selectors, workflow buttons,
    the embedded Segment Editor and export functions for the
    Dashboard.
    """
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = KSW_SemiAutomatic_BCW_moduleLogic()

        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Workflow"
        self.layout.addWidget(parametersCollapsibleButton)

        formLayout = qt.QFormLayout(parametersCollapsibleButton)
        formLayout.setVerticalSpacing(4)
        formLayout.setContentsMargins(4, 4, 4, 4)
        
        # ---------- Styles ----------
        buttonStyle = """
        QPushButton {
            background-color: #2f6fd6;
            border: none;
            border-radius: 5px;
            padding: 8px;
            font-weight: bold;
            color: white;
        }
        QPushButton:hover {
            background-color: #2458aa;
        }
        QPushButton:pressed {
            background-color: #1d4788;
        }
        """

        secondaryButtonStyle = """
        QPushButton {
            background-color: #e6e6e6;
            border: none;
            border-radius: 5px;
            padding: 7px;
            font-weight: bold;
            color: #222222;
        }
        QPushButton:hover {
            background-color: #d4d4d4;
        }
        """
        
        def addText(text):
            label = qt.QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    padding: 0px 4px 8px 4px;
                    margin: 0px;
                    color: #d6d6d6;
                    font-size: 12px;
                }
            """)
            label.setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Maximum)
            formLayout.addRow(label)
            return label

        def addSection(title):
            label = qt.QLabel(f"<b>{title}</b>")
            label.setStyleSheet("""
                QLabel {
                    color: #1f4e99;
                    font-size: 13px;
                    padding-top: 6px;
                    padding-bottom: 2px;
                    margin: 0px;
                }
            """)
            label.setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Maximum)
            formLayout.addRow(label)
            return label

        # ---------- Title ----------
        titleLabel = qt.QLabel("""
        <h2 style='color:#1f4e99; margin-bottom:2px;'>
        KSW Semi-automatic Body Composition Workflow
        </h2>
        <p style='color:#333333;'>
        Semi-automatic MRI segmentation for SAT, VAT and muscle,
        including quantitative metric extraction.
        </p>
        """)
        titleLabel.setWordWrap(True)
        titleLabel.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        formLayout.addRow(titleLabel)


        # ---------- Input ----------
        addSection("1. Input images")
        addText(
            "Select the Dixon fat image for SAT/VAT segmentation and IMAT calculation. "
            "Select the Dixon water image for muscle segmentation. "
            "Leave the Segmentation empty initially; it will be created automatically."
        )

        # ---------- Load images ----------
        loadImageLayout = qt.QHBoxLayout()

        self.loadFatButton = qt.QPushButton("Load Fat Image")
        self.loadFatButton.clicked.connect(self.onLoadFatImage)
        self.loadFatButton.setStyleSheet(secondaryButtonStyle)

        self.loadWaterButton = qt.QPushButton("Load Water Image")
        self.loadWaterButton.clicked.connect(self.onLoadWaterImage)
        self.loadWaterButton.setStyleSheet(secondaryButtonStyle)

        loadImageLayout.addWidget(self.loadFatButton)
        loadImageLayout.addWidget(self.loadWaterButton)

        formLayout.addRow("Load images:", loadImageLayout)

        self.fatSelector = slicer.qMRMLNodeComboBox()
        self.fatSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.fatSelector.selectNodeUponCreation = True
        self.fatSelector.addEnabled = False
        self.fatSelector.removeEnabled = False
        self.fatSelector.noneEnabled = True
        self.fatSelector.setMRMLScene(slicer.mrmlScene)
        formLayout.addRow("Fat image:", self.fatSelector)

        self.waterSelector = slicer.qMRMLNodeComboBox()
        self.waterSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.waterSelector.selectNodeUponCreation = True
        self.waterSelector.addEnabled = False
        self.waterSelector.removeEnabled = False
        self.waterSelector.noneEnabled = True
        self.waterSelector.setMRMLScene(slicer.mrmlScene)
        formLayout.addRow("Water image:", self.waterSelector)

        self.segmentationSelector = slicer.qMRMLNodeComboBox()
        self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.segmentationSelector.selectNodeUponCreation = True
        self.segmentationSelector.addEnabled = True
        self.segmentationSelector.removeEnabled = False
        self.segmentationSelector.noneEnabled = True
        self.segmentationSelector.renameEnabled = True
        self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
        formLayout.addRow("Segmentation:", self.segmentationSelector)

        # ---------- Patient Info ----------
        addSection("2. Patient information")
        addText(
            "Optionally enter a patient name or patient ID and, if useful, "
            "the year of birth. The patient height is required to calculate the "
            "Skeletal Muscle Index (SMI)."
        )

        self.patientNameLineEdit = qt.QLineEdit()
        self.patientNameLineEdit.setPlaceholderText("e.g. Patient_name or 001")
        formLayout.addRow("Patient name / ID:", self.patientNameLineEdit)

        self.birthYearSpinBox = qt.QSpinBox()
        self.birthYearSpinBox.setRange(0, 2100)
        self.birthYearSpinBox.setSpecialValueText("")
        self.birthYearSpinBox.setValue(0)
        formLayout.addRow("Year of birth:", self.birthYearSpinBox)

        self.heightSpinBox = qt.QDoubleSpinBox()
        self.heightSpinBox.setRange(0.00, 2.50)
        self.heightSpinBox.setSingleStep(0.01)
        self.heightSpinBox.setDecimals(2)
        # Show an empty field initially. Internally, the empty field equals 0.00.
        self.heightSpinBox.setSpecialValueText("")
        self.heightSpinBox.setValue(0.00)
        self.heightSpinBox.setSuffix(" m")
        formLayout.addRow("Patient height:", self.heightSpinBox)


        # ---------- Processing mode ----------
        addSection("3. Processing mode")
        addText(
            "Choose whether you are working with a 2D image or a 3D volume. "
            "For 3D volumes, scroll to the desired L3 slice in the Red slice viewer "
            "and then press the Auto-detect button to store this slice index. "
            "The same selected slice index is used for the fat image, water image, "
            "segmentation, metric calculation and dashboard export. "
            "No automatic fat-water slice offset is applied."
        )
        

        self.modeComboBox = qt.QComboBox()
        self.modeComboBox.addItems([
            "2D image mode",
            "3D single-slice mode"
        ])
        self.modeComboBox.currentTextChanged.connect(self.onProcessingModeChanged)
        formLayout.addRow("Processing mode:", self.modeComboBox)

        # L3 slice selection row
        self.sliceRowWidget = qt.QWidget()
        sliceLayout = qt.QHBoxLayout(self.sliceRowWidget)
        sliceLayout.setContentsMargins(0, 0, 0, 0)

        self.sliceSpinBox = qt.QSpinBox()
        self.sliceSpinBox.setRange(0, 1000)
        self.sliceSpinBox.setValue(0)

        self.autoDetectButton = qt.QPushButton("Auto-detect")
        self.autoDetectButton.toolTip = "Use the currently selected slice in the Red slice viewer."
        self.autoDetectButton.clicked.connect(self.onAutoDetectSliceIndex)

        sliceLayout.addWidget(self.sliceSpinBox)
        sliceLayout.addWidget(self.autoDetectButton)

        formLayout.addRow("L3 slice index:", self.sliceRowWidget)

        # ---------- 2D workflow ----------
        self.workflow2DWidget = qt.QWidget()
        workflow2DLayout = qt.QVBoxLayout(self.workflow2DWidget)
        workflow2DLayout.setContentsMargins(0, 0, 0, 0)

        self.runFatWorkflowButton = qt.QPushButton("Run automatic SAT/VAT segmentation")
        self.runFatWorkflowButton.clicked.connect(self.onRunFatWorkflow)
        self.runFatWorkflowButton.setStyleSheet(buttonStyle)
        workflow2DLayout.addWidget(self.runFatWorkflowButton)

        formLayout.addRow(self.workflow2DWidget)

        # ---------- 3D workflow ----------
        self.workflow3DText = addText(
            "3D mode uses a step-by-step workflow on one shared L3 slice: "
            "first segment SAT, manually correct SAT if needed, then segment VAT, "
            "create and refine the Muscle segment, run IMAT segmentation, and finally "
            "compute/export the metrics."
        )

        self.workflow3DWidget = qt.QWidget()
        workflow3DLayout = qt.QVBoxLayout(self.workflow3DWidget)
        workflow3DLayout.setContentsMargins(0, 0, 0, 0)

        self.runSAT3DButton = qt.QPushButton("1. Run SAT threshold")
        self.runSAT3DButton.clicked.connect(self.onRunSAT3DWorkflow)
        self.runSAT3DButton.setStyleSheet(buttonStyle)
        workflow3DLayout.addWidget(self.runSAT3DButton)

        self.editSATButton = qt.QPushButton("2. Edit SAT Segment")
        self.editSATButton.clicked.connect(lambda: self.onPrepareSegmentEditing("SAT"))
        self.editSATButton.setStyleSheet(secondaryButtonStyle)
        workflow3DLayout.addWidget(self.editSATButton)

        self.runVAT3DButton = qt.QPushButton("3. Run VAT threshold + subtract SAT")
        self.runVAT3DButton.clicked.connect(self.onRunVAT3DWorkflow)
        self.runVAT3DButton.setStyleSheet(buttonStyle)
        workflow3DLayout.addWidget(self.runVAT3DButton)

        self.runMuscle3DButton = qt.QPushButton("4. Run Muscle threshold + clean fat overlap")
        self.runMuscle3DButton.clicked.connect(self.onRunMuscle3DWorkflow)
        self.runMuscle3DButton.setStyleSheet(buttonStyle)
        workflow3DLayout.addWidget(self.runMuscle3DButton)
        
        formLayout.addRow(self.workflow3DWidget)

        # ---------- Muscle editing ----------
        addSection("4. Manual muscle editing")
        addText(
            "Initialises the Muscle segment on the selected shared L3 slice using the water image. "
            "Fat overlap from SAT/VAT is reduced automatically where possible. "
            "Use the embedded Segment Editor below to refine the Muscle segment manually."
        )
        self.prepareMuscleButton = qt.QPushButton("Edit Muscle Segment")
        self.prepareMuscleButton.clicked.connect(self.onPrepareMuscle)
        self.prepareMuscleButton.setStyleSheet(secondaryButtonStyle)
        formLayout.addRow(self.prepareMuscleButton)

        self.embeddedSegmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        self.embeddedSegmentEditorWidget.setMRMLScene(slicer.mrmlScene)

        self.segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentEditorNode"
        )

        self.embeddedSegmentEditorWidget.setMRMLSegmentEditorNode(
            self.segmentEditorNode
        )

        formLayout.addRow("Manual editing:", self.embeddedSegmentEditorWidget)

        # ---------- IMAT ----------
        addSection("5. Automatic IMAT segmentation")
        addText(
            "Enter the fat-image intensity threshold for IMAT. "
            "The recommended starting threshold is 53-233. "
            "After pressing the button, the module thresholds the fat image on the "
            "selected shared L3 slice and keeps only pixels overlapping with the "
            "Muscle segment. The threshold values can be adjusted before running IMAT."
        )

        # IMAT threshold input row
        # The values can be adapted by the user before the IMAT segment is created.
        imatThresholdWidget = qt.QWidget()
        imatThresholdLayout = qt.QHBoxLayout(imatThresholdWidget)
        imatThresholdLayout.setContentsMargins(0, 0, 0, 0)

        self.imatThresholdMinSpinBox = qt.QSpinBox()
        self.imatThresholdMinSpinBox.setRange(-100000, 100000)
        self.imatThresholdMinSpinBox.setValue(53)
        self.imatThresholdMinSpinBox.setToolTip("Lower IMAT threshold on the fat image")

        self.imatThresholdMaxSpinBox = qt.QSpinBox()
        self.imatThresholdMaxSpinBox.setRange(-100000, 100000)
        self.imatThresholdMaxSpinBox.setValue(233)
        self.imatThresholdMaxSpinBox.setToolTip("Upper IMAT threshold on the fat image")

        recommendedIMATLabel = qt.QLabel("Recommended: 53-233")
        recommendedIMATLabel.setStyleSheet("color: #d6d6d6; font-size: 12px; padding-left: 8px;")

        imatThresholdLayout.addWidget(qt.QLabel("Min:"))
        imatThresholdLayout.addWidget(self.imatThresholdMinSpinBox)
        imatThresholdLayout.addWidget(qt.QLabel("Max:"))
        imatThresholdLayout.addWidget(self.imatThresholdMaxSpinBox)
        imatThresholdLayout.addWidget(recommendedIMATLabel)
        imatThresholdLayout.addStretch(1)

        formLayout.addRow("IMAT threshold:", imatThresholdWidget)

        self.runIMATButton = qt.QPushButton("Run automatic IMAT segmentation")
        self.runIMATButton.clicked.connect(self.onRunIMATWorkflow)
        self.runIMATButton.setStyleSheet(buttonStyle)
        formLayout.addRow(self.runIMATButton)

        # ---------- Metrics ----------
        addSection("6. Metrics and export")
        addText(
            "Computes quantitative metrics on the selected shared L3 slice, including "
            "SAT area, VAT area, Muscle area, VAT/SAT ratio, SMI and IMAT%. "
            "The fat image, water image, segmentation and CSV results are exported "
            "to the dashboard output folder."
        )
        self.computeMetricsButton = qt.QPushButton("Compute Metrics + Export to Dashboard")
        self.computeMetricsButton.clicked.connect(self.onComputeMetrics)
        self.computeMetricsButton.setStyleSheet(buttonStyle)
        formLayout.addRow(self.computeMetricsButton)

        self.statusLabel = qt.QLabel("Ready.")
        self.statusLabel.setWordWrap(True)
        formLayout.addRow("Status:", self.statusLabel)

        addText(
            "Then open the Dashboard for visualization, reports and metric analysis."
        )

        self.openDashboardButton = qt.QPushButton("Open Dashboard")
        self.openDashboardButton.clicked.connect(self.onOpenDashboard)
        self.openDashboardButton.setStyleSheet(buttonStyle)
        formLayout.addRow(self.openDashboardButton)

        # ---------- Reset ----------
        addSection("7. Reset workflow")
        addText(
            "Clears loaded images, segmentations and workflow selections "
            "to start a new patient analysis."
        )

        self.resetWorkflowButton = qt.QPushButton("Start New Patient")
        self.resetWorkflowButton.clicked.connect(self.onResetWorkflow)
        self.resetWorkflowButton.setStyleSheet(secondaryButtonStyle)

        formLayout.addRow(self.resetWorkflowButton)

        self.onProcessingModeChanged(self.modeComboBox.currentText)
        
        # Enable slice intersection lines
        sliceDisplayNodes = slicer.util.getNodesByClass("vtkMRMLSliceDisplayNode")
        for node in sliceDisplayNodes:
            node.SetIntersectingSlicesVisibility(1)
            node.SetIntersectingSlicesInteractive(False)
            node.SetIntersectingSlicesLineThicknessMode(0)
            node.SetIntersectingSlicesLineVisibility(0, True) # horizontal
            node.SetIntersectingSlicesLineVisibility(1, False) # vertical

    # ── Processing mode and image loading handlers ──────────────────────────────

    def onProcessingModeChanged(self, mode):
        is3D = mode == "3D single-slice mode"

        self.sliceRowWidget.setVisible(is3D)
        self.workflow2DWidget.setVisible(not is3D)
        self.workflow3DWidget.setVisible(is3D)
        self.workflow3DText.setVisible(is3D)

        if is3D:
            self.statusLabel.text = (
                "3D mode selected. Use the step-by-step 3D workflow."
            )
        else:
            self.statusLabel.text = (
                "2D mode selected. The original automatic SAT/VAT workflow is used."
            )

    def onLoadFatImage(self):
        """Load the Dixon fat image and assign it to the fat selector."""
        volumeNode = self.askAndLoadImage("fat")

        if volumeNode:
            volumeNode.SetName(slicer.mrmlScene.GenerateUniqueName("fat_image"))

            self.fatSelector.setCurrentNode(volumeNode)
            self.statusLabel.text = f"Fat image loaded: {volumeNode.GetName()}"


    def onLoadWaterImage(self):
        """Load the Dixon water image and assign it to the water selector."""
        volumeNode = self.askAndLoadImage("water")

        if volumeNode:
            volumeNode.SetName(slicer.mrmlScene.GenerateUniqueName("water_image"))

            self.waterSelector.setCurrentNode(volumeNode)
            self.statusLabel.text = f"Water image loaded: {volumeNode.GetName()}"
    
    def askAndLoadImage(self, imageType):
        """Ask whether the user wants to load an image file or a DICOM folder.

        Parameters
        ----------
        imageType : str
            Descriptive name used in dialogs, usually ``"fat"`` or ``"water"``.

        Returns
        -------
        vtkMRMLScalarVolumeNode or None
            Loaded scalar volume node, or ``None`` if the user cancels or loading fails.
        """
        dialog = qt.QMessageBox()
        dialog.setWindowTitle(f"Load {imageType.capitalize()} Image")
        dialog.setText("What would you like to load?")

        fileButton = dialog.addButton("Image File", qt.QMessageBox.AcceptRole)
        folderButton = dialog.addButton("DICOM Folder", qt.QMessageBox.ActionRole)
        cancelButton = dialog.addButton("Cancel", qt.QMessageBox.RejectRole)

        dialog.exec_()
        clickedButton = dialog.clickedButton()

        if clickedButton == cancelButton:
            return None

        try:
            if clickedButton == fileButton:
                filePath = qt.QFileDialog.getOpenFileName(
                    slicer.util.mainWindow(),
                    f"Select Dixon {imageType} image",
                    "",
                    "Image files (*.nrrd *.nii *.nii.gz *.dcm);;All files (*)"
                )

                if not filePath:
                    return None

                return slicer.util.loadVolume(filePath)

            if clickedButton == folderButton:
                folderPath = qt.QFileDialog.getExistingDirectory(
                    slicer.util.mainWindow(),
                    f"Select Dixon {imageType} DICOM folder",
                    ""
                )

                if not folderPath:
                    return None

                return self.logic.loadDicomFolderAsVolume(folderPath)

        except Exception as e:
            slicer.util.errorDisplay(f"Could not load {imageType} image:\n{str(e)}")

        return None

    def getCurrentNodes(self):
        """Return the currently selected fat image, water image and segmentation."""
        fatNode = self.fatSelector.currentNode()
        waterNode = self.waterSelector.currentNode()
        segmentationNode = self.segmentationSelector.currentNode()
        return fatNode, waterNode, segmentationNode
    
    # ── Slice selection and workflow control ───────────────────────────────────

    def onAutoDetectSliceIndex(self):
        """Read the currently displayed Red slice and store it as the shared L3 index."""
        fatNode, waterNode, _ = self.getCurrentNodes()

        referenceNode = fatNode if fatNode else waterNode

        if not referenceNode:
            slicer.util.errorDisplay("Please select at least a fat or water image first.")
            return

        sliceIndex = self.logic.getCurrentSliceIndexFromViewer(referenceNode, "Red")
        self.sliceSpinBox.setValue(sliceIndex)

        self.statusLabel.text = (
            f"Detected L3 slice: shared fat/water/segmentation index {sliceIndex}. "
            "No automatic fat-water slice offset is applied."
        )

    # ── 2D segmentation workflow ────────────────────────────────────────────────

    def onRunFatWorkflow(self):
        """
        Runs the semi-automatic SAT/VAT segmentation workflow.

        Depending on the selected mode, either the first slice of a 2D image
        or the currently selected L3 slice in the Red slice viewer is used.
        SAT and VAT are segmented by predefined thresholds and post-processed
        using island operations and logical subtraction.
        """
        fatNode, _, segmentationNode = self.getCurrentNodes()

        if not fatNode:
            slicer.util.errorDisplay("Please select a fat image.")
            return

        mode = self.modeComboBox.currentText

        if mode == "2D image mode":
            sliceIndex = 0
        else:
            sliceIndex = self.logic.getCurrentSliceIndexFromViewer(fatNode, "Red")
            self.sliceSpinBox.setValue(sliceIndex)


        if not segmentationNode:
            segmentationNode = self.logic.createSegmentation(fatNode)
            self.segmentationSelector.setCurrentNode(segmentationNode)

        self.logic.initializeSegments(segmentationNode, fatNode)

        self.logic.applyThresholdSingleSlice(segmentationNode, fatNode, "SAT", 162, 697, sliceIndex)
        self.logic.keepLargestIsland(segmentationNode, "SAT", 100)

        self.logic.applyThresholdSingleSlice(segmentationNode, fatNode, "VAT", 27, 318, sliceIndex)
        self.logic.removeSmallIslands(segmentationNode, "VAT", 10)

        self.logic.copySegment(
            segmentationNode,
            sourceSegmentName="SAT",
            targetSegmentName="NOT"
        )

        self.logic.subtractSegment(
            segmentationNode,
            modifierSegmentName="NOT",
            selectedSegmentName="VAT"
        )
        notId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName("NOT")

        if notId:
            segmentationNode.GetSegmentation().RemoveSegment(notId)
            
        self.statusLabel.text = "SAT/VAT workflow completed. Please check and correct the segmentation if needed."

    # ── 3D segmentation workflow ────────────────────────────────────────────────

    def onRunSAT3DWorkflow(self):
        """Run the first 3D-mode step: threshold SAT on the selected L3 slice.

        The currently visible Red slice is stored as the shared workflow slice.
        No automatic fat-water slice offset is applied.
        """

        fatNode, _, segmentationNode = self.getCurrentNodes()

        if not fatNode:
            slicer.util.errorDisplay("Please select a fat image.")
            return

        sliceIndex = self.logic.getCurrentSliceIndexFromViewer(fatNode, "Red")
        self.sliceSpinBox.setValue(sliceIndex)

        if not segmentationNode:
            segmentationNode = self.logic.createSegmentation(fatNode)
            self.segmentationSelector.setCurrentNode(segmentationNode)

        self.logic.ensureSegment(segmentationNode, "SAT", [1.0, 1.0, 0.0])

        self.logic.applyThresholdSingleSlice(
            segmentationNode,
            fatNode,
            "SAT",
            460,
            2086,
            sliceIndex
        )

        self.statusLabel.text = (
            f"SAT threshold completed on slice {sliceIndex}. "
            "Please manually correct SAT."
        )

    def onRunVAT3DWorkflow(self):
        """Run the second 3D-mode step: threshold VAT and subtract SAT.

        The same shared workflow slice is used for SAT, VAT, Muscle and IMAT.
        """

        fatNode, _, segmentationNode = self.getCurrentNodes()

        if not fatNode or not segmentationNode:
            slicer.util.errorDisplay("Please select fat image and segmentation.")
            return

        sliceIndex = self.logic.getCurrentSliceIndexFromViewer(fatNode, "Red")
        self.sliceSpinBox.setValue(sliceIndex)

        self.logic.ensureSegment(segmentationNode, "VAT", [1.0, 0.5, 0.0])

        self.logic.applyThresholdSingleSlice(
            segmentationNode,
            fatNode,
            "VAT",
            417,
            1645,
            sliceIndex
        )

        self.logic.subtractSegment(
            segmentationNode,
            modifierSegmentName="SAT",
            selectedSegmentName="VAT"
        )

        self.logic.removeSmallIslands(
            segmentationNode,
            "VAT",
            10
        )

        self.statusLabel.text = (
            f"VAT segmentation completed on slice {sliceIndex}."
        )

    def onRunMuscle3DWorkflow(self):
        """Run the third 3D-mode step: initialize a rough muscle mask.

        Muscle is thresholded on the water image, but the resulting mask is
        written into the fat/segmentation geometry at the same slice index.
        This keeps SAT, VAT, Muscle and IMAT on one shared slice without using
        any automatic fat-water slice offset.
        """

        fatNode, waterNode, segmentationNode = self.getCurrentNodes()

        if not fatNode or not waterNode or not segmentationNode:
            slicer.util.errorDisplay("Please select fat image, water image and segmentation.")
            return

        # Use the currently visible slice in the Red slice viewer and store it as shared workflow slice.
        sliceIndex = self.logic.getCurrentSliceIndexFromViewer(fatNode, "Red")
        self.sliceSpinBox.setValue(sliceIndex)

        self.logic.ensureSegment(segmentationNode, "Muscle", [0.8, 0.2, 0.2])

        # Important correction:
        # The threshold is taken from the WATER image, but the labelmap is written
        # into the FAT/segmentation reference geometry. Otherwise the Muscle
        # segment can appear empty when IMAT is later evaluated in fat geometry.
        self.logic.applyThresholdMappedSlice(
            segmentationNode=segmentationNode,
            thresholdVolumeNode=waterNode,
            referenceVolumeNode=fatNode,
            segmentName="Muscle",
            minimum=354,
            maximum=1342,
            thresholdSliceIndex=sliceIndex,
            referenceSliceIndex=sliceIndex
        )

        self.logic.subtractSegment(
            segmentationNode,
            modifierSegmentName="SAT",
            selectedSegmentName="Muscle"
        )

        self.logic.subtractSegment(
            segmentationNode,
            modifierSegmentName="VAT",
            selectedSegmentName="Muscle"
        )

        self.statusLabel.text = (
            f"Muscle threshold completed on shared slice {sliceIndex}. "
            "Please manually correct Muscle."
        )

    # ── Manual editing helpers ─────────────────────────────────────────────────

    def onPrepareSegmentEditing(self, segmentName):
        """Activate the requested segment in the embedded Segment Editor.

        SAT/VAT editing uses the fat image as source volume. Muscle editing uses the
        water image. Overwrite mode is set to ``OverwriteNone`` so that existing
        segments are not erased unintentionally while painting.
        """

        fatNode, waterNode, segmentationNode = self.getCurrentNodes()

        if not segmentationNode:
            slicer.util.errorDisplay("Please select a segmentation.")
            return

        # SAT and VAT should use fat image
        if segmentName in ["SAT", "VAT"]:
            sourceVolume = fatNode
        else:
            sourceVolume = waterNode

        if not sourceVolume:
            slicer.util.errorDisplay(
                f"Please select the correct source image for {segmentName}."
            )
            return

        segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)

        if not segmentId:
            slicer.util.errorDisplay(f"Segment '{segmentName}' not found.")
            return

        self.embeddedSegmentEditorWidget.setSegmentationNode(segmentationNode)
        self.embeddedSegmentEditorWidget.setSourceVolumeNode(sourceVolume)
        self.embeddedSegmentEditorWidget.setCurrentSegmentID(segmentId)

        self.segmentEditorNode.SetOverwriteMode(
            slicer.vtkMRMLSegmentEditorNode.OverwriteNone
        )

        self.statusLabel.text = f"Editing segment: {segmentName}"
    
    def onPrepareMuscle(self):
        """Prepare manual muscle editing on the selected shared L3 slice."""

        fatNode, waterNode, segmentationNode = self.getCurrentNodes()

        if not fatNode or not waterNode or not segmentationNode:
            slicer.util.errorDisplay("Please select fat image, water image and segmentation.")
            return

        mode = self.modeComboBox.currentText

        if mode == "2D image mode":
            sliceIndex = 0
        else:
            sliceIndex = int(self.sliceSpinBox.value)

        muscleId = self.logic.ensureSegment(segmentationNode, "Muscle", [0.8, 0.2, 0.2])

        self.embeddedSegmentEditorWidget.setSegmentationNode(segmentationNode)
        self.embeddedSegmentEditorWidget.setSourceVolumeNode(waterNode)
        self.embeddedSegmentEditorWidget.setCurrentSegmentID(muscleId)

        self.segmentEditorNode.SetOverwriteMode(
            slicer.vtkMRMLSegmentEditorNode.OverwriteNone
        )

        self.statusLabel.text = (
            f"Muscle editing ready on shared slice {sliceIndex}. "
            "Use the embedded Segment Editor."
        )

    # ── IMAT, metrics, dashboard and reset handlers ────────────────────────────

    def onRunIMATWorkflow(self):
        """Create IMAT from fat intensities inside the Muscle segment.
        No automatic fat/water slice offset is applied. The same slice index is
        used for the fat image and the water image. The Muscle segment is read using 
        the available reference image. The resulting IMAT segment is created on the 
        selected shared workflow slice. This prevents IMAT from failing when the
        Muscle mask appears empty in fat-image geometry.
        """

        fatNode, waterNode, segmentationNode = self.getCurrentNodes()

        if not fatNode or not segmentationNode:
            slicer.util.errorDisplay("Please select fat image and segmentation.")
            return

        mode = self.modeComboBox.currentText

        if mode == "2D image mode":
            sliceIndex = 0
        else:
            sliceIndex = int(self.sliceSpinBox.value)

        try:
            minimum = self.imatThresholdMinSpinBox.value
            maximum = self.imatThresholdMaxSpinBox.value

            if minimum >= maximum:
                slicer.util.errorDisplay(
                    "Invalid IMAT threshold: the minimum value must be smaller than the maximum value."
                )
                return

            imatResult = self.logic.createIMATSegment2D(
                segmentationNode=segmentationNode,
                fatVolumeNode=fatNode,
                waterVolumeNode=waterNode,
                sliceIndex=sliceIndex,
                minimum=minimum,
                maximum=maximum
            )

            # Keep the user-selected shared slice index fixed.
            # If Muscle is detected one slice nearby, createIMATSegment2D uses that
            # nearby Muscle mask only as a temporary source mask, but writes the
            # final IMAT segment back to the originally selected slice.
            if len(imatResult) == 4:
                imatPixels, musclePixels, thresholdPixels, usedSliceIndex = imatResult
            else:
                imatPixels, musclePixels, thresholdPixels = imatResult
                usedSliceIndex = sliceIndex

            imatId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName("IMAT")

            self.logic.showWorkflowSegments(segmentationNode)

            if imatId:
                self.embeddedSegmentEditorWidget.setSegmentationNode(segmentationNode)
                self.embeddedSegmentEditorWidget.setSourceVolumeNode(waterNode if waterNode else fatNode)
                self.embeddedSegmentEditorWidget.setCurrentSegmentID(imatId)

                self.segmentEditorNode.SetOverwriteMode(
                    slicer.vtkMRMLSegmentEditorNode.OverwriteNone
                )

                # Show the water image if available for easier anatomical review.
                if waterNode:
                    self.logic.showVolumeInRedView(waterNode)
                    self.logic.jumpRedSliceToVolumeSlice(waterNode, int(sliceIndex))
                else:
                    self.logic.showVolumeInRedView(fatNode)
                    self.logic.jumpRedSliceToVolumeSlice(fatNode, int(sliceIndex))

            self.statusLabel.text = (
                f"IMAT segmentation completed on shared slice {sliceIndex} "
                f"with threshold {minimum}-{maximum}. "
                f"IMAT pixels: {imatPixels}, muscle pixels: {musclePixels}."
            )

        except Exception as e:
            slicer.util.errorDisplay(f"IMAT segmentation failed: {str(e)}")

    def onComputeMetrics(self):
        """
        Compute metrics and export the current patient data for the dashboard.

        All workflow segments are evaluated on the detected workflow slice.
        For 3-slice datasets, the dashboard export may shift image and segmentation
        copies together so that the dashboard displays the correct anatomical slice.
        """
        fatNode, waterNode, segmentationNode = self.getCurrentNodes()

        if not fatNode or not segmentationNode:
            slicer.util.errorDisplay("Please select fat image and segmentation.")
            return

        height_m = self.heightSpinBox.value

        if height_m <= 0:
            slicer.util.errorDisplay(
                "Please enter the patient height before computing metrics."
            )
            return

        mode = self.modeComboBox.currentText

        if mode == "2D image mode":
            sliceIndex = 0
        else:
            sliceIndex = int(self.sliceSpinBox.value)

        patientName = self.patientNameLineEdit.text.strip()
        birthYear = int(self.birthYearSpinBox.value)

        if not patientName:
            patientName = "Current patient"

        if birthYear > 0 and patientName != "Current patient":
            patientDisplayName = f"{patientName} (Jg. {birthYear})"
        else:
            patientDisplayName = patientName

        metrics = self.logic.computeMetrics2D(
            segmentationNode,
            fatNode,
            waterVolumeNode=waterNode,
            height_m=height_m,
            waterSliceIndex=sliceIndex,
            fatSliceIndex=sliceIndex,
            patient_id=patientDisplayName,
            patient_name=patientName,
            birth_year=birthYear
        )

        scriptDir = os.path.dirname(os.path.abspath(__file__))

        # Export to the folder structure expected by dashboard.py.
        patientDir = os.path.join(scriptDir, "Dashboard", "current_patient")
        outputDir = os.path.join(patientDir, "output")
        niftiDir = os.path.join(outputDir, "nifti")
        os.makedirs(niftiDir, exist_ok=True)

        workflowSliceIndex = int(metrics.get("slice_index", sliceIndex))

        referenceNode = fatNode
        referenceDepth = slicer.util.arrayFromVolume(referenceNode).shape[0]

        # True slice where the segmentation and metrics were created.
        # This is the source slice that will be read from the Slicer segmentation.
        exportSourceSliceIndex = workflowSliceIndex

        # Slice that the dashboard should display.
        # For normal volumes this is the same as the workflow slice.
        # For 3-slice datasets, the dashboard displays 1-based style indexing,
        # therefore the output slice is shifted by +1.
        dashboardSliceIndex = workflowSliceIndex

        if referenceDepth <= 3:
            dashboardSliceIndex = int(np.clip(workflowSliceIndex + 1, 0, referenceDepth - 1))

        metrics["workflow_slice_index"] = workflowSliceIndex
        metrics["dashboard_slice_index"] = dashboardSliceIndex

        # Important:
        # The dashboard may read "slice_index" from the CSV.
        # Therefore, store the dashboard display slice here.
        metrics["slice_index"] = dashboardSliceIndex
        metrics["water_slice_index"] = dashboardSliceIndex
        metrics["fat_slice_index"] = dashboardSliceIndex

        for filename in ["slice_index.txt", "dashboard_start_slice.txt"]:
            path = os.path.join(outputDir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(dashboardSliceIndex))

        print(f"[Dashboard export] Final dashboard start slice written: {dashboardSliceIndex}")

        # Read back immediately for debugging.
        for filename in ["slice_index.txt", "dashboard_start_slice.txt"]:
            path = os.path.join(outputDir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    print(f"[Dashboard export check] {filename} = {f.read().strip()}")
            except Exception as e:
                print(f"[Dashboard export check] Could not read {filename}: {e}")
        print(
            f"[Dashboard export] workflow slice index: {workflowSliceIndex}, "
            f"source slice index: {exportSourceSliceIndex}, "
            f"dashboard/output slice index: {dashboardSliceIndex}, "
            f"volume depth: {referenceDepth}"
        )

        
        self.logic.saveDashboardVolumeForSlice(
            fatNode,
            os.path.join(niftiDir, "fat.nii"),
            sourceSliceIndex=exportSourceSliceIndex,
            outputSliceIndex=dashboardSliceIndex
        )

        if waterNode:
            self.logic.saveDashboardVolumeForSlice(
                waterNode,
                os.path.join(niftiDir, "water.nii"),
                sourceSliceIndex=exportSourceSliceIndex,
                outputSliceIndex=dashboardSliceIndex
            )

        # Export a dashboard-compatible segmentation NRRD.
        # The dashboard reads labels by SegmentName/LabelValue and does not
        # reliably handle overlapping Slicer segmentation layers. Therefore,
        # a flat labelmap with fixed, unique label values is written here.
        referenceNode = fatNode
        self.logic.exportDashboardSegmentationNRRD(
            segmentationNode,
            referenceNode,
            os.path.join(niftiDir, "seg_corrected.seg.nrrd"),
            sliceIndex=exportSourceSliceIndex,
            outputSliceIndex=dashboardSliceIndex
        )

        outputPath = os.path.join(outputDir, "body_composition_results.csv")
        self.logic.exportMetrics(metrics, outputPath)

        self.statusLabel.text = f"Metrics exported to dashboard folder: {outputPath}"

    def onOpenDashboard(self):
        """Start the local dashboard application."""
        try:
            self.logic.launchDashboard()
            self.statusLabel.text = "Dashboard launched."
        except Exception as e:
            slicer.util.errorDisplay(f"Failed to launch dashboard: {str(e)}")


    def onResetWorkflow(self):
        """Reset the scene and UI selectors for a new patient/workflow run."""
        # Clear selectors
        self.fatSelector.setCurrentNode(None)
        self.waterSelector.setCurrentNode(None)
        self.segmentationSelector.setCurrentNode(None)

        # Reset slice index
        self.sliceSpinBox.setValue(0)

        # Reset height
        self.heightSpinBox.setValue(0)

        # Remove all segmentation nodes
        segmentationNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        for node in segmentationNodes:
            slicer.mrmlScene.RemoveNode(node)

        # Remove scalar volumes
        volumeNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        for node in volumeNodes:
            slicer.mrmlScene.RemoveNode(node)

        # Clear segment editor
        self.embeddedSegmentEditorWidget.setSegmentationNode(None)
        self.embeddedSegmentEditorWidget.setSourceVolumeNode(None)

        self.statusLabel.text = (
            "Workflow reset completed. Ready for new patient."
        )

        self.patientNameLineEdit.clear()
        self.birthYearSpinBox.setValue(0)


# =============================================================================
# LOGIC / PROCESSING FUNCTIONS
# =============================================================================

class KSW_SemiAutomatic_BCW_moduleLogic(ScriptedLoadableModuleLogic):
    """Processing logic for the KSW body composition workflow.

    The widget class handles user interaction. This logic class contains reusable
    functions for DICOM loading, slice-index detection, segment creation,
    single-slice thresholding, logical segment operations, metric calculation and
    dashboard launching.
    """
    # Default segment names and display colors used throughout the workflow.
    DEFAULT_SEGMENTS = {
        "SAT": [1.0, 1.0, 0.0],
        "VAT": [1.0, 0.5, 0.0],
        "NOT": [0.4, 0.4, 0.4],
        "Muscle": [0.8, 0.2, 0.2],
        "IMAT": [0.4, 1.0, 0.4],
    }

    # ── DICOM loading and slice-view helpers ──────────────────────────────────

    def loadDicomFolderAsVolume(self, folderPath):
        """
        Loads only the selected DICOM folder as one scalar volume.
        """

        if not os.path.isdir(folderPath):
            raise ValueError("Selected path is not a folder.")

        dicomFiles = []
        for root, _, files in os.walk(folderPath):
            for file in files:
                filePath = os.path.join(root, file)
                if file.lower().endswith(".dcm") or "." not in file:
                    dicomFiles.append(filePath)

        if not dicomFiles:
            raise ValueError("No DICOM files found in selected folder.")

        loadedBefore = set(
            node.GetID()
            for node in slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        )

        import DICOMScalarVolumePlugin
        plugin = DICOMScalarVolumePlugin.DICOMScalarVolumePluginClass()

        loadables = plugin.examine([dicomFiles])

        if not loadables:
            raise RuntimeError("No loadable scalar volume found in selected DICOM folder.")

        loadables.sort(key=lambda l: l.confidence, reverse=True)
        selectedLoadable = loadables[0]

        plugin.load(selectedLoadable)

        loadedAfter = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        newNodes = [
            node for node in loadedAfter
            if node.GetID() not in loadedBefore
        ]

        if not newNodes:
            raise RuntimeError("DICOM folder was imported, but no new volume was loaded.")

        return newNodes[-1]

    def getCurrentSliceIndexFromViewer(self, volumeNode, sliceViewName="Red"):
        """
        Reads the currently displayed slice position from the Slicer slice viewer
        and converts it to the corresponding voxel slice index of the selected volume.
        """

        if volumeNode is None:
            raise ValueError("No volume selected.")

        layoutManager = slicer.app.layoutManager()
        sliceWidget = layoutManager.sliceWidget(sliceViewName)

        if sliceWidget is None:
            raise ValueError(f"Slice view '{sliceViewName}' not found.")

        sliceNode = sliceWidget.sliceLogic().GetSliceNode()

        # Get current slice position in RAS coordinates
        sliceToRAS = sliceNode.GetSliceToRAS()
        ras = [
            sliceToRAS.GetElement(0, 3),
            sliceToRAS.GetElement(1, 3),
            sliceToRAS.GetElement(2, 3),
            1.0
        ]

        # Convert RAS to IJK voxel coordinates
        rasToIJK = vtk.vtkMatrix4x4()
        volumeNode.GetRASToIJKMatrix(rasToIJK)

        ijk = [0, 0, 0, 0]
        rasToIJK.MultiplyPoint(ras, ijk)

        sliceIndex = int(round(ijk[2]))

        volumeArray = slicer.util.arrayFromVolume(volumeNode)
        maxIndex = volumeArray.shape[0] - 1

        if sliceIndex < 0:
            sliceIndex = 0
        if sliceIndex > maxIndex:
            sliceIndex = maxIndex

        return sliceIndex

    def showVolumeInRedView(self, volumeNode):
        """Show the selected volume as background in the Red slice viewer."""
        if volumeNode is None:
            return

        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActiveVolumeID(volumeNode.GetID())
        slicer.app.applicationLogic().PropagateVolumeSelection(0)

    def jumpRedSliceToVolumeSlice(self, volumeNode, sliceIndex):
        """Jump the Red slice viewer to a specific voxel slice of a volume."""
        if volumeNode is None:
            return

        volumeArray = slicer.util.arrayFromVolume(volumeNode)
        sliceIndex = int(np.clip(sliceIndex, 0, volumeArray.shape[0] - 1))

        dims = volumeNode.GetImageData().GetDimensions()

        # Slicer array order is [k, j, i], while IJK coordinates are [i, j, k].
        i = dims[0] / 2.0
        j = dims[1] / 2.0
        k = sliceIndex

        ijkToRAS = vtk.vtkMatrix4x4()
        volumeNode.GetIJKToRASMatrix(ijkToRAS)

        ras = [0, 0, 0, 0]
        ijkToRAS.MultiplyPoint([i, j, k, 1.0], ras)

        layoutManager = slicer.app.layoutManager()
        redWidget = layoutManager.sliceWidget("Red")
        if redWidget:
            redSliceNode = redWidget.sliceLogic().GetSliceNode()
            redSliceNode.JumpSliceByCentering(ras[0], ras[1], ras[2])

    # ── Segmentation node and segment management ──────────────────────────────

    def createSegmentation(self, sourceVolumeNode):
        """Create a new segmentation node with geometry linked to the source volume."""
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode",
            "BodyCompositionSegmentation"
        )
        segmentationNode.CreateDefaultDisplayNodes()
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(sourceVolumeNode)
        return segmentationNode

    def initializeSegments(self, segmentationNode, sourceVolumeNode):
        """Reset a segmentation and create all default workflow segments."""
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(sourceVolumeNode)

        segmentation = segmentationNode.GetSegmentation()
        segmentation.RemoveAllSegments()

        for name, color in self.DEFAULT_SEGMENTS.items():
            self.ensureSegment(segmentationNode, name, color)

    def ensureSegment(self, segmentationNode, segmentName, color):
        """Return an existing segment ID or create the segment if it does not exist."""
        segmentation = segmentationNode.GetSegmentation()
        segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)

        if segmentId:
            segment = segmentation.GetSegment(segmentId)
            segment.SetName(segmentName)
            segment.SetColor(color)
            return segmentId

        segmentId = segmentation.AddEmptySegment(segmentName)
        segment = segmentation.GetSegment(segmentId)
        segment.SetName(segmentName)
        segment.SetColor(color)
        return segmentId

    def showWorkflowSegments(self, segmentationNode):
        """Make all main workflow segments visible in the 2D viewer."""
        if segmentationNode is None:
            return

        displayNode = segmentationNode.GetDisplayNode()
        if displayNode is None:
            segmentationNode.CreateDefaultDisplayNodes()
            displayNode = segmentationNode.GetDisplayNode()

        segmentation = segmentationNode.GetSegmentation()

        colors = {
            "SAT": [1.0, 1.0, 0.0],
            "VAT": [1.0, 0.5, 0.0],
            "Muscle": [0.8, 0.2, 0.2],
            "IMAT": [0.4, 1.0, 0.4],
        }

        for segmentName, color in colors.items():
            segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
            if not segmentId:
                continue

            segment = segmentation.GetSegment(segmentId)
            segment.SetColor(color)

            displayNode.SetSegmentVisibility(segmentId, True)
            displayNode.SetSegmentOpacity2DFill(segmentId, 0.55)
            displayNode.SetSegmentOpacity2DOutline(segmentId, 1.0)


    # ── Segment Editor effect helpers ─────────────────────────────────────────

    def getSegmentEditorWidget(self):
        """Create a temporary Segment Editor widget for scripted effects.

        The temporary widget is used for Segment Editor effects such as Islands
        and Logical operators. Its MRML node is removed after each operation.
        """
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)

        editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorWidget.setMRMLSegmentEditorNode(editorNode)

        return segmentEditorWidget, editorNode

    # ── Thresholding and labelmap import ──────────────────────────────────────

    def applyThresholdMappedSlice(self, segmentationNode, thresholdVolumeNode,
                              referenceVolumeNode, segmentName,
                              minimum, maximum,
                              thresholdSliceIndex, referenceSliceIndex):
        """
        Threshold one slice from thresholdVolumeNode and write the mask into
        referenceVolumeNode geometry.

        This is used when the threshold image and the reference geometry are different,
        for example when Muscle is thresholded on the water image but stored in the
        fat/segmentation geometry.
        """

        thresholdArray = slicer.util.arrayFromVolume(thresholdVolumeNode)
        referenceArray = slicer.util.arrayFromVolume(referenceVolumeNode)

        if thresholdSliceIndex < 0 or thresholdSliceIndex >= thresholdArray.shape[0]:
            raise ValueError(
                f"Threshold slice index {thresholdSliceIndex} is outside range "
                f"0-{thresholdArray.shape[0] - 1}"
            )

        if referenceSliceIndex < 0 or referenceSliceIndex >= referenceArray.shape[0]:
            raise ValueError(
                f"Reference slice index {referenceSliceIndex} is outside range "
                f"0-{referenceArray.shape[0] - 1}"
            )

        thresholdSlice2d = thresholdArray[thresholdSliceIndex, :, :]

        if thresholdSlice2d.shape != referenceArray[referenceSliceIndex, :, :].shape:
            raise ValueError(
                "Threshold image and reference image have different in-plane dimensions. "
                f"Threshold: {thresholdSlice2d.shape}, "
                f"Reference: {referenceArray[referenceSliceIndex, :, :].shape}"
            )

        mask2d = np.logical_and(
            thresholdSlice2d >= minimum,
            thresholdSlice2d <= maximum
        ).astype(np.uint8)

        self.updateSegmentFrom2DMask(
            segmentationNode,
            referenceVolumeNode,
            segmentName,
            mask2d,
            referenceSliceIndex
        )

    def applyThresholdSingleSlice(self, segmentationNode, volumeNode, segmentName,
                                minimum, maximum, sliceIndex):
        """
        Threshold one slice of a volume and write the result into the same
        volume geometry.

        This is used when the threshold image and the segmentation/reference
        image are the same, for example Muscle on the water image or the 2D mode.
        """

        volumeArray = slicer.util.arrayFromVolume(volumeNode)
        sliceIndex = int(np.clip(sliceIndex, 0, volumeArray.shape[0] - 1))

        imageSlice2d = volumeArray[sliceIndex, :, :]

        mask2d = np.logical_and(
            imageSlice2d >= minimum,
            imageSlice2d <= maximum
        ).astype(np.uint8)

        self.updateSegmentFrom2DMask(
            segmentationNode,
            volumeNode,
            segmentName,
            mask2d,
            sliceIndex
        )
        
    def updateSegmentFrom2DMask(self, segmentationNode, referenceVolumeNode,
                                segmentName, mask2d, sliceIndex):
        """
        Writes a 2D mask into one slice of a 3D labelmap and imports it as a segment.
        """

        volumeArray = slicer.util.arrayFromVolume(referenceVolumeNode)

        labelArray = np.zeros(volumeArray.shape, dtype=np.uint8)
        labelArray[sliceIndex, :, :] = mask2d

        segmentation = segmentationNode.GetSegmentation()

        oldSegmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
        if oldSegmentId:
            segmentation.RemoveSegment(oldSegmentId)

        labelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode",
            f"temp_{segmentName}_label"
        )

        slicer.util.updateVolumeFromArray(labelNode, labelArray)
        labelNode.CopyOrientation(referenceVolumeNode)
        labelNode.SetSpacing(referenceVolumeNode.GetSpacing())
        labelNode.SetOrigin(referenceVolumeNode.GetOrigin())

     
        beforeIds = [
            segmentation.GetNthSegmentID(i)
            for i in range(segmentation.GetNumberOfSegments())
        ]

        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelNode,
            segmentationNode
        )

        afterIds = [
            segmentation.GetNthSegmentID(i)
            for i in range(segmentation.GetNumberOfSegments())
        ]

        newIds = [sid for sid in afterIds if sid not in beforeIds]

        if newIds:
            newSegmentId = newIds[0]
            segment = segmentation.GetSegment(newSegmentId)
            segment.SetName(segmentName)
            segment.SetColor(self.DEFAULT_SEGMENTS.get(segmentName, [1, 1, 1]))


        slicer.mrmlScene.RemoveNode(labelNode)


    # ── IMAT creation and metric calculation ──────────────────────────────────

    def createIMATSegment2D(self, segmentationNode, fatVolumeNode, waterVolumeNode=None,
                        sliceIndex=0, minimum=53, maximum=233):
        """
        Create IMAT on the selected shared workflow slice.

        IMAT is defined as fat-image pixels within the selected intensity range
        that overlap with the Muscle segment. Muscle is thresholded from the
        water image, but stored in the fat/segmentation reference geometry.
        Therefore, the Muscle mask is read in fat geometry and the IMAT segment
        is written back to the same selected slice.
        """

        segmentation = segmentationNode.GetSegmentation()
        muscleId = segmentation.GetSegmentIdBySegmentName("Muscle")

        if not muscleId:
            raise ValueError("Muscle segment not found. Please segment Muscle first.")

        # All workflow segments are stored in the fat/segmentation reference geometry.
        # Muscle is thresholded from the water image, but written into fat geometry.
        # Therefore IMAT must read Muscle and write IMAT in fat geometry.
        referenceVolumeNode = fatVolumeNode

        fatArray = slicer.util.arrayFromVolume(fatVolumeNode)
        referenceArray = slicer.util.arrayFromVolume(referenceVolumeNode)

        sliceIndex = int(sliceIndex)
        sliceIndex = int(np.clip(sliceIndex, 0, fatArray.shape[0] - 1))
        referenceSliceIndex = int(np.clip(sliceIndex, 0, referenceArray.shape[0] - 1))

        fatSlice2d = fatArray[sliceIndex, :, :]

        muscleArray = slicer.util.arrayFromSegmentBinaryLabelmap(
            segmentationNode,
            muscleId,
            referenceVolumeNode
        )

        muscleMask2d = muscleArray[referenceSliceIndex, :, :] > 0
        musclePixels = int(np.sum(muscleMask2d))

        if musclePixels == 0:
            # Diagnostic fallback only: look whether the Muscle exists nearby.
            bestIndex = referenceSliceIndex
            bestPixels = 0
            searchStart = max(0, referenceSliceIndex - 2)
            searchEnd = min(muscleArray.shape[0] - 1, referenceSliceIndex + 2)

            for idx in range(searchStart, searchEnd + 1):
                pixels = int(np.sum(muscleArray[idx, :, :] > 0))
                if pixels > bestPixels:
                    bestPixels = pixels
                    bestIndex = idx

            if bestPixels > 0:
                print(
                    f"IMAT locked-slice correction: Muscle is empty on selected "
                    f"slice {referenceSliceIndex}, but exists on nearby slice "
                    f"{bestIndex} ({bestPixels} pixels). Using the nearby Muscle "
                    f"mask only for IMAT calculation, but writing IMAT back to "
                    f"the selected slice {referenceSliceIndex}."
                )

                # Keep all final workflow segments on the same selected slice.
                # The nearby Muscle mask is used only as a temporary source mask.
                # The fat threshold and the final IMAT segment stay on the original
                # selected slice, so SAT, VAT, Muscle and IMAT appear together in
                # Slicer and in the dashboard.
                muscleMask2d = muscleArray[int(bestIndex), :, :] > 0
                musclePixels = int(np.sum(muscleMask2d))
            else:
                raise ValueError(
                    f"Muscle mask is empty on selected slice {referenceSliceIndex}. "
                    "Please rerun Muscle threshold and correct Muscle before IMAT."
                )

        if muscleMask2d.shape != fatSlice2d.shape:
            raise ValueError(
                "Fat slice and Muscle mask have different in-plane dimensions. "
                f"Fat: {fatSlice2d.shape}, Muscle: {muscleMask2d.shape}."
            )

        fatThresholdMask2d = np.logical_and(
            fatSlice2d >= minimum,
            fatSlice2d <= maximum
        )

        thresholdPixels = int(np.sum(fatThresholdMask2d))

        imatMask2d = np.logical_and(
            fatThresholdMask2d,
            muscleMask2d
        ).astype(np.uint8)

        imatPixels = int(np.sum(imatMask2d))

        print(
            f"IMAT segmentation completed: shared slice {sliceIndex}, "
            f"reference slice {referenceSliceIndex}, threshold {minimum}-{maximum}, "
            f"threshold pixels {thresholdPixels}, muscle pixels {musclePixels}, "
            f"IMAT pixels {imatPixels}"
        )

        self.updateSegmentFrom2DMask(
            segmentationNode,
            referenceVolumeNode,
            "IMAT",
            imatMask2d,
            referenceSliceIndex
        )

        return imatPixels, musclePixels, thresholdPixels, referenceSliceIndex

    def computeMetrics2D(self, segmentationNode, fatVolumeNode, waterVolumeNode=None,
                        height_m=1.75, waterSliceIndex=0, fatSliceIndex=0,
                        patient_id="Current patient", patient_name="Current patient",
                        birth_year=0):
        """
        Compute 2D body composition metrics on the actual segmentation slice.

        The UI slice index can sometimes be one slice off after manual editing
        or after IMAT was created from a neighbouring Muscle mask. Therefore,
        this function first searches a small neighbourhood around the selected
        slice and uses the slice with the largest amount of workflow
        segmentation pixels. This keeps the Slicer view, metrics and dashboard
        export consistent without applying a fat/water offset.
        """

        referenceVolumeNode = fatVolumeNode
        referenceArray = slicer.util.arrayFromVolume(referenceVolumeNode)

        requestedSliceIndex = int(waterSliceIndex)
        requestedSliceIndex = int(np.clip(requestedSliceIndex, 0, referenceArray.shape[0] - 1))

        segmentation = segmentationNode.GetSegmentation()
        segmentNames = ["SAT", "VAT", "Muscle", "IMAT"]

        # Search for the actual non-empty workflow slice around the requested index.
        searchRadius = 3
        startIndex = max(0, requestedSliceIndex - searchRadius)
        endIndex = min(referenceArray.shape[0] - 1, requestedSliceIndex + searchRadius)

        bestSliceIndex = requestedSliceIndex
        bestScore = -1

        for idx in range(startIndex, endIndex + 1):
            score = 0
            for segmentName in segmentNames:
                segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
                if not segmentId:
                    continue
                try:
                    segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(
                        segmentationNode,
                        segmentId,
                        referenceVolumeNode
                    )
                    score += int(np.sum(segmentArray[idx, :, :] > 0))
                except Exception:
                    continue

            if score > bestScore:
                bestScore = score
                bestSliceIndex = idx

        sliceIndex = bestSliceIndex

        if sliceIndex != requestedSliceIndex:
            print(
                f"Metrics slice adjusted from {requestedSliceIndex} to {sliceIndex} "
                f"because the workflow segments are on slice {sliceIndex}."
            )

        spacing = referenceVolumeNode.GetSpacing()
        pixelAreaCm2 = (spacing[0] * spacing[1]) / 100.0

        results = {}

        for segmentName in segmentNames:
            segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)

            if not segmentId:
                results[f"{segmentName}_area_cm2"] = 0.0
                continue

            try:
                segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(
                    segmentationNode,
                    segmentId,
                    referenceVolumeNode
                )
            except Exception:
                results[f"{segmentName}_area_cm2"] = 0.0
                continue

            if sliceIndex < 0 or sliceIndex >= segmentArray.shape[0]:
                results[f"{segmentName}_area_cm2"] = 0.0
                continue

            mask2d = segmentArray[sliceIndex, :, :] > 0
            pixels = int(np.sum(mask2d))

            results[f"{segmentName}_area_cm2"] = float(pixels * pixelAreaCm2)

        satArea = results.get("SAT_area_cm2", 0.0)
        vatArea = results.get("VAT_area_cm2", 0.0)
        muscleArea = results.get("Muscle_area_cm2", 0.0)
        imatArea = results.get("IMAT_area_cm2", 0.0)

        finalResults = {
            "sat_cm2": satArea,
            "vat_cm2": vatArea,
            "sma_cm2": muscleArea,
            "imat_cm2": imatArea,
            "imat_pct": imatArea / muscleArea * 100 if muscleArea > 0 else 0,
            "vat_sat_ratio": vatArea / satArea if satArea > 0 else 0,
            "smi": muscleArea / (height_m ** 2) if height_m > 0 else 0,
            "sat_index": satArea / (height_m ** 2) if height_m > 0 else 0,
            "vat_index": vatArea / (height_m ** 2) if height_m > 0 else 0,
            "height_m": height_m,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "birth_year": birth_year if birth_year > 0 else "",
            "slice_index": sliceIndex,
            "water_slice_index": sliceIndex,
            "fat_slice_index": sliceIndex,
        }

        print(
            f"Metrics computed on workflow slice {sliceIndex}: "
            f"SAT {satArea:.2f} cm², VAT {vatArea:.2f} cm², "
            f"Muscle {muscleArea:.2f} cm², IMAT {imatArea:.2f} cm²"
        )

        return finalResults


    # ── Post-processing effects and logical segment operations ────────────────

    def keepLargestIsland(self, segmentationNode, segmentName, minimumSize=100):
        self._runIslands(
            segmentationNode,
            segmentName,
            operation="KEEP_LARGEST_ISLAND",
            minimumSize=minimumSize
        )

    def removeSmallIslands(self, segmentationNode, segmentName, minimumSize=10):
        self._runIslands(
            segmentationNode,
            segmentName,
            operation="REMOVE_SMALL_ISLANDS",
            minimumSize=minimumSize
        )

    def _runIslands(self, segmentationNode, segmentName, operation, minimumSize):
        segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)

        if not segmentId:
            raise ValueError(f"Segment '{segmentName}' not found.")

        segmentEditorWidget, editorNode = self.getSegmentEditorWidget()

        try:
            segmentEditorWidget.setSegmentationNode(segmentationNode)
            segmentEditorWidget.setCurrentSegmentID(segmentId)

            segmentEditorWidget.setActiveEffectByName("Islands")
            effect = segmentEditorWidget.activeEffect()
            effect.setParameter("Operation", operation)
            effect.setParameter("MinimumSize", str(minimumSize))
            effect.self().onApply()

        finally:
            segmentEditorWidget = None
            slicer.mrmlScene.RemoveNode(editorNode)

    def copySegment(self, segmentationNode, sourceSegmentName, targetSegmentName):
        segmentation = segmentationNode.GetSegmentation()
        sourceId = segmentation.GetSegmentIdBySegmentName(sourceSegmentName)
        targetId = self.ensureSegment(
            segmentationNode,
            targetSegmentName,
            self.DEFAULT_SEGMENTS.get(targetSegmentName, [1, 1, 1])
        )

        if not sourceId:
            raise ValueError(f"Source segment '{sourceSegmentName}' not found.")

        segmentEditorWidget, editorNode = self.getSegmentEditorWidget()

        try:
            segmentEditorWidget.setSegmentationNode(segmentationNode)
            segmentEditorWidget.setCurrentSegmentID(targetId)

            segmentEditorWidget.setActiveEffectByName("Logical operators")
            effect = segmentEditorWidget.activeEffect()
            effect.setParameter("Operation", "COPY")
            effect.setParameter("ModifierSegmentID", sourceId)
            effect.self().onApply()

        finally:
            segmentEditorWidget = None
            slicer.mrmlScene.RemoveNode(editorNode)

    def subtractSegment(self, segmentationNode, modifierSegmentName, selectedSegmentName):
        segmentation = segmentationNode.GetSegmentation()
        modifierId = segmentation.GetSegmentIdBySegmentName(modifierSegmentName)
        selectedId = segmentation.GetSegmentIdBySegmentName(selectedSegmentName)

        if not modifierId or not selectedId:
            raise ValueError("Modifier or selected segment not found.")

        segmentEditorWidget, editorNode = self.getSegmentEditorWidget()

        try:
            segmentEditorWidget.setSegmentationNode(segmentationNode)
            segmentEditorWidget.setCurrentSegmentID(selectedId)

            segmentEditorWidget.setActiveEffectByName("Logical operators")
            effect = segmentEditorWidget.activeEffect()
            effect.setParameter("Operation", "SUBTRACT")
            effect.setParameter("ModifierSegmentID", modifierId)
            effect.self().onApply()

        finally:
            segmentEditorWidget = None
            slicer.mrmlScene.RemoveNode(editorNode)


    # ── Dashboard export and launch helpers ───────────────────────────────────
    def saveDashboardVolumeForSlice(self, volumeNode, filepath,
                                    sourceSliceIndex=None,
                                    outputSliceIndex=None):
        """
        Save a dashboard-compatible NIfTI volume.

        Slicer arrays are ordered as [slice, y, x]. The dashboard expects NIfTI
        arrays as [x, y, z] and displays image[:, :, z].T. Therefore the array is
        transposed before saving so that the dashboard z-slider corresponds to the
        Slicer slice index.
        """
        import nibabel as nib

        if volumeNode is None:
            raise ValueError("No volume node provided.")

        volumeArrayKJI = slicer.util.arrayFromVolume(volumeNode)
        depth = volumeArrayKJI.shape[0]

        # Convert from Slicer array order [k, j, i] to dashboard/NIfTI order [i, j, k].
        volumeArrayIJK = np.transpose(volumeArrayKJI, (2, 1, 0)).astype(np.float32)

        # For very small 2D/3-slice datasets, optionally copy the selected source
        # slice to the dashboard display slice.
        if (
            sourceSliceIndex is not None
            and outputSliceIndex is not None
            and depth <= 3
            and int(sourceSliceIndex) != int(outputSliceIndex)
        ):
            sourceSliceIndex = int(np.clip(int(sourceSliceIndex), 0, depth - 1))
            outputSliceIndex = int(np.clip(int(outputSliceIndex), 0, depth - 1))

            volumeArrayIJK[:, :, outputSliceIndex] = volumeArrayIJK[:, :, sourceSliceIndex]

            print(
                f"[Dashboard export] Saved shifted dashboard volume: "
                f"source slice {sourceSliceIndex} -> output slice {outputSliceIndex}"
            )

        # Simple identity affine is enough for dashboard visualization.
        affine = np.eye(4)

        niftiImage = nib.Nifti1Image(volumeArrayIJK, affine)
        nib.save(niftiImage, filepath)

        print(
            f"[Dashboard export] Wrote dashboard-compatible volume: {filepath}, "
            f"shape={volumeArrayIJK.shape}"
        )
    
    def exportDashboardSegmentationNRRD(self, segmentationNode, referenceVolumeNode,
                                    filepath, sliceIndex=None, outputSliceIndex=None):
        """
        Export a dashboard-compatible .seg.nrrd without changing the Slicer scene.

        The dashboard reads one flat labelmap. A flat labelmap cannot store true
        overlap, therefore IMAT would normally overwrite Muscle in the dashboard
        and make the muscle mask look incomplete. To keep the dashboard file
        compatible without editing dashboard.py, IMAT is exported with its own
        label value and the header also exposes this label as an additional
        muscle-type label (Autochthon_R). The dashboard already treats
        Autochthon_R as skeletal muscle in the water panel, while still treating
        the same label as IMAT in the fat panel.

        Fixed label values:
            SAT    = 65
            Muscle = 66
            VAT    = 67
            IMAT   = 68
        """
        if segmentationNode is None:
            raise ValueError("No segmentation node provided for dashboard export.")

        if referenceVolumeNode is None:
            raise ValueError("No reference volume provided for dashboard export.")

        folder = os.path.dirname(filepath)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        referenceArray = slicer.util.arrayFromVolume(referenceVolumeNode)

        # Slicer array order is [k, j, i]
        kSize, jSize, iSize = referenceArray.shape

        # Dashboard reads arrays as [i, j, k] and displays [:, :, z].T
        # Therefore, build the exported labelmap directly in [i, j, k].
        combinedIJK = np.zeros((iSize, jSize, kSize), dtype=np.uint8)

        if sliceIndex is not None:
            sliceIndex = int(np.clip(int(sliceIndex), 0, kSize - 1))

        if outputSliceIndex is None:
            outputSliceIndex = sliceIndex

        if outputSliceIndex is not None:
            outputSliceIndex = int(np.clip(int(outputSliceIndex), 0, kSize - 1))

        labelValues = {
            "SAT": 65,
            "Muscle": 66,
            "VAT": 67,
            "IMAT": 68,
        }

        colors = {
            "SAT": "1 1 0",
            "Muscle": "0.8 0.2 0.2",
            "VAT": "1 0.5 0",
            "IMAT": "0.4 1 0.4",
            "Autochthon_R": "0.8 0.2 0.2",
        }

        exportOrder = ["SAT", "VAT", "Muscle", "IMAT"]
        segmentation = segmentationNode.GetSegmentation()

        for segmentName in exportOrder:
            segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)

            if not segmentId:
                print(f"[Dashboard export] Segment not found, skipped: {segmentName}")
                continue

            segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(
                segmentationNode,
                segmentId,
                referenceVolumeNode
            )

            if sliceIndex is not None:
                # Take the real workflow slice in Slicer order [j, i]
                mask2dJI = segmentArray[sliceIndex, :, :] > 0

                # Convert to dashboard order [i, j]
                mask2dIJ = mask2dJI.T

                pixels = int(np.sum(mask2dIJ))

                if pixels == 0:
                    print(
                        f"[Dashboard export] Segment is empty on export slice "
                        f"{sliceIndex}: {segmentName}"
                    )
                    continue

                combinedIJK[:, :, outputSliceIndex][mask2dIJ] = labelValues[segmentName]

            else:
                maskKJI = segmentArray > 0
                pixels = int(np.sum(maskKJI))

                if pixels == 0:
                    print(f"[Dashboard export] Segment is empty: {segmentName}")
                    continue

                maskIJK = np.transpose(maskKJI, (2, 1, 0))
                combinedIJK[maskIJK] = labelValues[segmentName]

            print(
                f"[Dashboard export] {segmentName}: label {labelValues[segmentName]}, "
                f"pixels {pixels}"
            )

        # Debug: show which labels are really present on each exported dashboard slice.
        for z in range(combinedIJK.shape[2]):
            uniqueLabels = np.unique(combinedIJK[:, :, z])
            if len(uniqueLabels) > 1:
                print(f"[Dashboard export debug] z={z}, labels={uniqueLabels}")

        spacing = referenceVolumeNode.GetSpacing()
        origin = referenceVolumeNode.GetOrigin()
        sizes = combinedIJK.shape

        # Autochthon_R is a header-only alias for the IMAT label value. The
        # dashboard already includes Autochthon_R in the muscle label list.
        segmentHeader = [
            ("SAT", labelValues["SAT"], colors["SAT"]),
            ("Muscle", labelValues["Muscle"], colors["Muscle"]),
            ("VAT", labelValues["VAT"], colors["VAT"]),
            ("IMAT", labelValues["IMAT"], colors["IMAT"]),
            ("Autochthon_R", labelValues["IMAT"], colors["Autochthon_R"]),
        ]

        headerLines = [
            "NRRD0005",
            "# Dashboard-compatible segmentation exported from 3D Slicer",
            "type: unsigned char",
            "dimension: 3",
            f"sizes: {sizes[0]} {sizes[1]} {sizes[2]}",
            "encoding: raw",
            "endian: little",
            "kinds: domain domain domain",
            f"space directions: ({spacing[0]},0,0) (0,{spacing[1]},0) (0,0,{spacing[2]})",
            f"space origin: ({origin[0]},{origin[1]},{origin[2]})",
        ]

        for i, (segmentName, labelValue, color) in enumerate(segmentHeader):
            headerLines.extend([
                f"Segment{i}_ID:=Segment_{i + 1}",
                f"Segment{i}_Name:={segmentName}",
                f"Segment{i}_Layer:=0",
                f"Segment{i}_LabelValue:={labelValue}",
                f"Segment{i}_Color:={color}",
            ])

        headerText = "\n".join(headerLines) + "\n\n"

        with open(filepath, "wb") as f:
            f.write(headerText.encode("ascii"))
            f.write(combinedIJK.tobytes(order="F"))

        print(f"[Dashboard export] Wrote dashboard-compatible segmentation: {filepath}")


    def exportMetrics(self, metricsDict, filepath):
        """
        Exports metrics as one CSV row with column headers.

        """

        folder = os.path.dirname(filepath)

        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter( f, fieldnames=metricsDict.keys())
            writer.writeheader()
            writer.writerow(metricsDict)

    def launchDashboard(self):
        """Start the Panel dashboard with the exported dashboard slice index."""
        scriptDir = os.path.dirname(os.path.abspath(__file__))
        dashboardDir = os.path.join(scriptDir, "Dashboard")
        dashboardScript = os.path.join(dashboardDir, "dashboard.py")
        patientDir = os.path.join(dashboardDir, "current_patient")
        outputDir = os.path.join(patientDir, "output")

        if not os.path.exists(dashboardScript):
            raise FileNotFoundError(f"Dashboard file not found: {dashboardScript}")

        csvPath = os.path.join(outputDir, "body_composition_results.csv")
        if not os.path.exists(csvPath):
            raise FileNotFoundError(
                "Dashboard input not found. Please run 'Compute Metrics + Export to Dashboard' first."
            )

        # Read the slice written during export.
        # Prefer dashboard_start_slice.txt because it is written directly for launching.
        sliceIndex = None

        for filename in ["dashboard_start_slice.txt", "slice_index.txt"]:
            sliceIndexPath = os.path.join(outputDir, filename)

            if os.path.exists(sliceIndexPath):
                try:
                    with open(sliceIndexPath, "r", encoding="utf-8") as f:
                        sliceIndex = int(f.read().strip())
                    print(f"[Dashboard launch] Using {filename}: z={sliceIndex}")
                    break
                except Exception as e:
                    print(f"[Dashboard launch] Could not read {filename}: {e}")

        if sliceIndex is None:
            sliceIndex = 0
            print("[Dashboard launch] No slice index file found. Falling back to z=0.")

        # Synchronise both files again directly before launching.
        for filename in ["slice_index.txt", "dashboard_start_slice.txt"]:
            path = os.path.join(outputDir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(sliceIndex))

        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)

        if os.name == "nt":
            batPath = os.path.join(dashboardDir, "start_dashboard_from_slicer.bat")

            with open(batPath, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("set PYTHONHOME=\n")
                f.write("set PYTHONPATH=\n")
                f.write(f'cd /d "{dashboardDir}"\n')
                f.write(f'echo Starting dashboard with z={sliceIndex}\n')

                # Stop old Panel servers on port 5006.
                f.write(
                    'powershell -NoProfile -Command '
                    '"Get-NetTCPConnection -LocalPort 5006 -State Listen -ErrorAction SilentlyContinue '
                    '| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"\n'
                )
                # Important: --z is passed after --args.
                f.write(
                    f'py -3.13 -m panel serve dashboard.py --port 5006 '
                    f'--args --patient "{patientDir}" --z {sliceIndex}\n'
                )

            subprocess.Popen(
                ["cmd.exe", "/c", batPath],
                cwd=dashboardDir,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        else:
            pythonExe = shutil.which("python")
            if not pythonExe:
                raise RuntimeError("No external Python executable found in PATH.")

            command = [
                pythonExe, "-m", "panel", "serve",
                dashboardScript,
                "--port", "5006",
                "--args",
                "--patient", patientDir,
                "--z", str(sliceIndex),
            ]
            subprocess.Popen(command, cwd=dashboardDir, env=env)

        time.sleep(4)
        webbrowser.open(f"http://localhost:5006/dashboard?t={int(time.time())}")
