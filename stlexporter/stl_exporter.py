
from glue.config import viewer_tool
from glue.viewers.common.tool import Tool
import pyvista as pv
from scipy.ndimage import filters

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QThread, pyqtSignal

import glue
from stlexporter import ICON

from matplotlib.colors import *

from pathlib import Path
from time import sleep
import sys

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self):
        super(Worker, self).__init__()
        self._isRunning = True

    def stop(self):
        self._isRunning = False

    def run(self, viewer, selectedDict, bounds, exportSTL, exportOBJ, savePath):
        """Long-running task."""
        count = 0
        for selectedItem in selectedDict.values():
            if not self._isRunning:
                break

            layer = selectedItem['layer']
            filename = selectedItem['filename']
            isomin = selectedItem['isomin']

            # check if subset object
            if isinstance(layer.layer, glue.core.subset_group.GroupedSubset):

                subcube = layer.layer.data.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data,
                                                                           bounds=bounds,
                                                                           subset_state=layer.layer.subset_state)
                datacube = layer.layer.data.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data,
                                                                            bounds=bounds,
                                                                            target_cid=layer.attribute)
                data = subcube * datacube

            # otherwise a data object
            else:
                data = layer.layer.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data,
                                                                   bounds=bounds,
                                                                   target_cid=layer.attribute)

            # apply smoothing to the data to create nicer surfaces on the model. Ultimately we will probably want users to set this
            data = filters.gaussian_filter(data, 1)

            x_origin = viewer.state.x_min  # collect the lower left hand corner pixel x,y,z values of the grid for pyvista
            y_origin = viewer.state.y_min
            z_origin = viewer.state.z_min

            # I think the voxel spacing will always be 1, because of how glue downsamples to a fixed resolution grid. But don't hold me to this!
            x_dist = 1
            y_dist = 1
            z_dist = 1

            # weird conventions between pyvista and glue data storage.
            data = data.transpose(2, 1, 0)

            # create pyvista grid
            grid = pv.UniformGrid()  # create a spatial reference

            grid.dimensions = (viewer.state.resolution, viewer.state.resolution,
                               viewer.state.resolution)  # set the grid dimensions to match our data

            # edit the spatial reference assuming pixel coordinates using the info extracted from the header earlier
            grid.origin = (x_origin, y_origin, z_origin)  # the bottom left corner of the data set
            grid.spacing = (z_dist, y_dist, x_dist)  # the cell sizes along each axis

            grid.point_arrays["values"] = data.flatten(
                order="F")  # add the data values to the cell data and flatten the array

            # We will want to ultimately open a GUI for user to pick this themselves.
            # Currently the min limit of the main layer is used
            iso_data = grid.contour([isomin])

            if exportSTL:
                stl_path = Path(savePath, filename + ".stl")
                iso_data.save(stl_path)  # save an STL file

            if exportOBJ:
                obj_path = Path(savePath, filename)
                plotter = pv.Plotter()  # create a scene
                _ = plotter.add_mesh(iso_data, color=selectedItem['color'])
                plotter.export_obj(obj_path)  # save as an OBJ

            self.progress.emit(count + 1)
            count += 1
        self.finished.emit()


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Choose Layers and Sublayers to save")
        self.setMinimumSize(300, 400)
        self.exportSTL = True
        self.exportOBJ = False



    def create_layout(self, viewer, layers):
        # Create an outer layout
        outerLayout = QVBoxLayout()
        # Create a form layout for the label and line edit
        topLayout = QVBoxLayout()
        listView = QListWidget()
        detailView = QVBoxLayout() # detailView for selecting options for the selected layer
        isoView = QHBoxLayout()

        layersDict = {}

        # Create the options:
        # for layer in layers:
        for idx in range(len(layers)):
            layer = layers[idx]

            #check if subset object
            if isinstance(layer.layer,glue.core.subset_group.GroupedSubset):
                # Name file with main data layer at beginning if subset
                filename = layer.layer.data.label + "_" + layer.layer.label

                isSubLayer = True

                # color = viewer.get_subset_layer_artist(layer.layer).get_layer_color() #getting layer artist succeeds but crashed Vispy!
                color = viewer.layers[idx].get_layer_color()

                # Search the vmin in the parent-layer
                for i in range(0,len(layers)):
                    if layers[i].layer is layer.layer.data:
                        isomin=layers[i].vmin

            #otherwise a data object
            else:
                isSubLayer = False
                isomin=layer.vmin

                color = viewer.layers[idx].get_layer_color()

                filename = layer.layer.label

            item = QListWidgetItem(filename)
            item.setCheckState(Qt.Checked)
            listView.addItem(item)

            color = rgb2hex(ColorConverter.to_rgb(color))

            layersDict[filename] = {
                "layer": layer,
                "item": item,
                "isSubLayer": isSubLayer,
                "filename": filename,
                "isomin": isomin,
                "color": color
            }

        # detailView for selecting options for the selected layer
        # Register action -> https://stackoverflow.com/questions/9313227/how-to-send-the-selected-item-in-the-listwidget-to-another-function-as-a-paramet/9315013
        listView.itemClicked.connect(lambda item: self.update_detailView(item, layersDict[item.text()]))

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
        self.checkboxSTL.toggled.connect(lambda: self.toggleSTLExport())

        self.checkboxOBJ = QCheckBox("Export OBJ Files")
        self.checkboxOBJ.setDisabled(False)
        self.checkboxOBJ.toggled.connect(lambda: self.toggleOBJExport())

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

        self.buttonSave.clicked.connect(lambda: self.show_new_window(viewer, layersDict))
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


    def reportProgress(self, n):
        print(f"Progress: {n}")
        self.progress.setValue(n)
        # self.stepLabel.setText(f"Long Running Step: {n}")


    def update_detailView(self, clickedItem, itemDict):
        # print('selectedItem in update_detailView: ', clickedItem.text())
        # print(itemDict)
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
        self.isoInput.valueChanged.connect(lambda newValue: self.update_isomin(newValue, itemDict))



    def update_isomin(self, newValue, itemDict):
        # ONLY change the value, if there was a actual change:
        if newValue != itemDict['isomin']:
            itemDict['isomin'] = newValue
            # print('isomin of', itemDict['filename'], 'changed to', newValue)


    def toggleSTLExport(self):
        self.exportSTL = not self.exportSTL


    def toggleOBJExport(self):
        self.exportOBJ = not self.exportOBJ


    def show_new_window(self, viewer, layersDict):
        selectedDict = {}
        for dictItem in layersDict.values():
            if(dictItem['item'].checkState() == Qt.Checked):
                filename = dictItem['filename']
                selectedDict[filename] = dictItem

        # print('layersDict', layersDict)
        # print('selectedDict', selectedDict)

        self.savePath = QFileDialog.getExistingDirectory()

        if(self.savePath == ""): # Cancel if Prompt was cancelled
            return

        self.close()

        #grab the xyz bounds of the viewer
        bounds = [(viewer.state.z_min, viewer.state.z_max, viewer.state.resolution), (viewer.state.y_min, viewer.state.y_max, viewer.state.resolution), (viewer.state.x_min, viewer.state.x_max, viewer.state.resolution)]

        # Create Progress Dialog

        stl_or_obj = ""
        if(self.exportSTL):
            stl_or_obj += "STL "
        if(self.exportSTL and self.exportOBJ):
            stl_or_obj += "and "
        if(self.exportOBJ):
            stl_or_obj += "OBJ "

        self.progress = QProgressDialog("Creating " + stl_or_obj + "files...", None, 0, len(selectedDict))
        self.progress.setWindowTitle(stl_or_obj + "Export")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.forceShow()
        self.progress.setValue(0)

        count = 0

        # Multithreading:
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker()
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(lambda: self.worker.run(viewer, selectedDict, bounds, self.exportSTL, self.exportOBJ, self.savePath))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.reportProgress)
        self.progress.canceled.connect(self.worker.stop)
        # Step 6: Start the thread
        self.thread.start()

        # TODO: Final resets  ???
        # self.longRunningBtn.setEnabled(False)
        # self.thread.finished.connect(
        #     lambda: self.longRunningBtn.setEnabled(True)
        # )
        # self.thread.finished.connect(
        #     lambda: self.stepLabel.setText("Long-Running Step: 0")
        # )





@viewer_tool
class StlExporter(Tool):
    icon = ICON
    tool_id = 'stl_exporter'
    action_text = 'STL Exporter'
    tool_tip = 'STL Exporter'


    def __init__(self, viewer):
        super(StlExporter, self).__init__(viewer)


    def createAndSaveSTL(self):
        pass

    def activate(self):
        dialog = MainWindow()
        # Dialog Test
        # grab viewer
        viewer = self.viewer

        #get the data layers of the viewer.
        layers =  viewer.state.layers

        dialog.create_layout(viewer, layers)
        dialog.show()

        # ------------------





    def close(self):
        pass

