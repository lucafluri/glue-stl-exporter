
from glue.config import viewer_tool
from glue.viewers.common.tool import Tool
import pyvista as pv
from scipy.ndimage import filters

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

import glue
from stlexporter import ICON

import sys


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Choose Layers and Sublayers to save")
        self.setMinimumSize(300, 400)



    def create_layout(self, viewer, layers):
        # Create an outer layout
        outerLayout = QVBoxLayout()
        # Create a form layout for the label and line edit
        topLayout = QVBoxLayout()
        listView = QListWidget()
        detailView = QHBoxLayout() # detailView for selecting options for the selected layer

        layersDict = {}

        # Create the options:
        for layer in layers:

            #check if subset object
            if isinstance(layer.layer,glue.core.subset_group.GroupedSubset):
                # Name file with main data layer at beginning if subset
                filename = layer.layer.data.label + "_" + layer.layer.label

                isSubLayer = True

                # Search the vmin in the parent-layer
                for i in range(0,len(layers)):
                    if layers[i].layer is layer.layer.data:
                        isomin=layers[i].vmin

            #otherwise a data object
            else:
                isSubLayer = False
                isomin=layer.vmin

                filename = layer.layer.label

            item = QListWidgetItem(filename)
            item.setCheckState(Qt.Checked)
            listView.addItem(item)

            layersDict[filename] = {
                "layer": layer,
                "item": item,
                "isSubLayer": isSubLayer,
                "filename": filename,
                "isomin": isomin,
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

        detailView.addWidget(self.selectedLabel)
        detailView.addWidget(self.isoInputLabel)
        detailView.addWidget(self.isoInput)



        # optionsLayout for Save/Cancel buttons
        optionsLayout = QHBoxLayout()
        # Add some checkboxes to the layout
        self.buttonSave = QPushButton("Save")
        self.buttonCancel = QPushButton("Cancel")

        self.buttonSave.clicked.connect(lambda: self.show_new_window(viewer, layersDict))
        self.buttonCancel.clicked.connect(self.close)

        optionsLayout.addWidget(self.buttonSave)
        optionsLayout.addWidget(self.buttonCancel)
        # Nest the inner layouts into the outer layout

        topLayout.addWidget(listView)
        outerLayout.addLayout(topLayout)
        outerLayout.addLayout(detailView)
        outerLayout.addLayout(optionsLayout)
        # Set the window's main layout
        self.setLayout(outerLayout)


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
        progress = QProgressDialog("Creating STL files...", None, 0, len(selectedDict))
        progress.setWindowTitle("STL Export")
        progress.setWindowModality(Qt.WindowModal)
        progress.forceShow()
        progress.setValue(0)

        count = 0

        for selectedItem in selectedDict.values():

            layer = selectedItem['layer']
            filename = selectedItem['filename']
            isomin = selectedItem['isomin']

            #check if subset object
            if isinstance(layer.layer,glue.core.subset_group.GroupedSubset):

                subcube=layer.layer.data.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data,
                                                                         bounds=bounds,
                                                                         subset_state=layer.layer.subset_state)
                datacube=layer.layer.data.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data,
                                                                          bounds=bounds,
                                                                          target_cid=layer.attribute)
                data=subcube*datacube

            #otherwise a data object
            else:
                data=layer.layer.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data,
                                                                 bounds=bounds,
                                                                 target_cid=layer.attribute)


            #apply smoothing to the data to create nicer surfaces on the model. Ultimately we will probably want users to set this
            data = filters.gaussian_filter(data,1)

            x_origin = viewer.state.x_min #collect the lower left hand corner pixel x,y,z values of the grid for pyvista
            y_origin = viewer.state.y_min
            z_origin = viewer.state.z_min

            #I think the voxel spacing will always be 1, because of how glue downsamples to a fixed resolution grid. But don't hold me to this!
            x_dist = 1
            y_dist = 1
            z_dist = 1

            #weird conventions between pyvista and glue data storage.
            data = data.transpose(2,1,0)

            #create pyvista grid
            grid = pv.UniformGrid() #create a spatial reference

            grid.dimensions = (viewer.state.resolution, viewer.state.resolution, viewer.state.resolution) # set the grid dimensions to match our data

            #edit the spatial reference assuming pixel coordinates using the info extracted from the header earlier
            grid.origin = (x_origin, y_origin, z_origin)  #the bottom left corner of the data set
            grid.spacing = (z_dist, y_dist, x_dist)  #the cell sizes along each axis

            grid.point_arrays["values"] = data.flatten(order="F")  #add the data values to the cell data and flatten the array

            # We will want to ultimately open a GUI for user to pick this themselves.
            # Currently the min limit of the main layer is used
            iso_data = grid.contour([isomin])

            iso_data.save(self.savePath + "\\" + filename + ".stl") #save an STL file

            count += 1
            progress.setValue(count)



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


        # app = QApplication([])
        # # self.dialog.setWindowModality(Qt.WindowModal)
        dialog.create_layout(viewer, layers)
        dialog.show()
        # app.exec_()

        # ------------------





    def close(self):
        pass

