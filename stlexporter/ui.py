from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread

from stlexporter.workers import *


class MainWindow(QWidget):
    
    def __init__(self, controller):
        super().__init__()
        self.setWindowTitle("Choose Layers and Sublayers to save")
        self.setMinimumSize(300, 400)
        
        self.controller = controller
        

    def createMainWindow(self):
        # Create an outer layout
        outerLayout = QVBoxLayout()
        # Create a form layout for the label and line edit
        topLayout = QVBoxLayout()
        listView = QListWidget()
        detailView = QVBoxLayout() # detailView for selecting options for the selected layer
        isoView = QHBoxLayout()

        layersDict = self.controller.getAndAddLayersDict(listView)

        # detailView for selecting options for the selected layer
        # Register action -> https://stackoverflow.com/questions/9313227/how-to-send-the-selected-item-in-the-listwidget-to-another-function-as-a-paramet/9315013
        listView.itemClicked.connect(lambda item: self.updateDetailView(item, layersDict[item.text()]))

        self.selectedLabel = QLabel()
        self.isoInputLabel = QLabel()
        self.isoInput = QSpinBox()
        self.isoInput.setDisabled(True)
        self.isoInput.setRange(-10000000, 10000000)  # possible range value for isoInput

        # Align the labels
        self.selectedLabel.setAlignment(Qt.AlignVCenter)
        self.isoInputLabel.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        self.checkboxSTL = QCheckBox("Export STL Files")
        self.checkboxSTL.setDisabled(False)
        self.checkboxSTL.setChecked(True)
        self.checkboxSTL.toggled.connect(lambda: self.controller.toggleSTLExport())

        self.checkboxOBJ = QCheckBox("Export OBJ Files")
        self.checkboxOBJ.setDisabled(False)
        self.checkboxOBJ.toggled.connect(lambda: self.controller.toggleOBJExport())

        topLayout.addWidget(self.checkboxOBJ)
        topLayout.addWidget(self.checkboxSTL)

        isoView.addWidget(self.selectedLabel)
        isoView.addWidget(self.isoInputLabel)
        isoView.addWidget(self.isoInput)

        detailView.addLayout(isoView)

        # optionsLayout for Save/Cancel buttons
        optionsLayout = QHBoxLayout()
        # Add some checkboxes to the layout
        self.buttonCancel = QPushButton("Cancel")
        self.buttonSave = QPushButton("Save")

        self.buttonSave.clicked.connect(lambda: self.showProgressDialog(layersDict))
        self.buttonCancel.clicked.connect(self.close)

        optionsLayout.addWidget(self.buttonCancel)
        optionsLayout.addWidget(self.buttonSave)
        # Nest the inner layouts into the outer layout

        topLayout.addWidget(listView)
        outerLayout.addLayout(topLayout)
        outerLayout.addLayout(detailView)
        outerLayout.addLayout(optionsLayout)
        # Set the window's main layout
        self.setLayout(outerLayout)


    def updateProgress(self, n):
    #     print(f"Progress: {n}")
        self.progress.setValue(n)


    def updateDetailView(self, clickedItem, itemDict):
        self.selectedLabel.setText(clickedItem.text())
        self.isoInputLabel.setText("Isosurface level:")

        # Disconnect necessary, because otherwise, the self.isoInput.valueChanged.connect(..)
        # would still be active and change OTHER layers instead as well, when switching back
        # and forth between layers!
        # Tested with    glue ..\subsets-test\perseus_and_taurus.glu
        self.isoInput.disconnect()

        ## Isomin should be set for all (layers and sublayers). If not, activate the following if/else clause again.
        ## -> be careful about this when saving later on!
        # if itemDict['isSubLayer']:
        #     self.isoInput.setDisabled(True)
        # else:
        #     self.isoInput.setValue(itemDict['isomin'])
        #     self.isoInput.setDisabled(False)
        #     self.isoInput.valueChanged.connect(lambda newValue: self.update_isomin(newValue, itemDict))
        self.isoInput.setValue(itemDict['isomin'])
        self.isoInput.setDisabled(False)
        self.isoInput.valueChanged.connect(lambda newValue: self.controller.update_isomin(newValue, itemDict))

    def showProgressDialog(self, layersDict):
        selectedDict = self.controller.getSelectedItems(layersDict)
        
        if not self.controller.getSavePath():
            return

        self.close() #Close main window

        stl_or_obj = self.controller.getSTLOBJString()

        # Create Progress Dialog
        self.progress = QProgressDialog("Creating " + stl_or_obj + "files...", None, 0, len(selectedDict))
        self.progress.setWindowTitle(stl_or_obj + "Export")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.forceShow()
        self.progress.setValue(0)


        # Multithreading:
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = SaveItemsWorker(self.controller)
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(lambda: self.worker.run(selectedDict))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.updateProgress)
        self.progress.canceled.connect(self.worker.stop)
        # Step 6: Start the thread
        self.thread.start()
