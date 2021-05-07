from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import glue
from scipy.ndimage import filters
import pyvista as pv

from matplotlib.colors import *

class Controller():
    def __init__(self, viewer, layers):
        self.viewer = viewer
        self.layers = layers
        self.bounds = [(viewer.state.z_min, viewer.state.z_max, viewer.state.resolution), (viewer.state.y_min, viewer.state.y_max, viewer.state.resolution), (viewer.state.x_min, viewer.state.x_max, viewer.state.resolution)]

        self.exportSTL = True
        self.exportOBJ = False

        self.savePath = ""
    
    def toggleSTLExport(self):
        self.exportSTL = not self.exportSTL

    def toggleOBJExport(self):
        self.exportOBJ = not self.exportOBJ

    def getSavePath(self):
        self.savePath = QFileDialog.getExistingDirectory()
        return self.savePath != ""
        
    def update_isomin(self, newValue, itemDict):
        # ONLY change the value, if there was a actual change:
        if newValue != itemDict['isomin']:
            itemDict['isomin'] = newValue
    
    def getAndAddLayersDict(self, listView):
        layersDict = {}

        # Create the options:
        # for layer in layers:
        for idx in range(len(self.layers)):
            layer = self.layers[idx]

            #check if subset object
            if isinstance(layer.layer,glue.core.subset_group.GroupedSubset):
                # Name file with main data layer at beginning if subset
                filename = layer.layer.data.label + "_" + layer.layer.label

                isSubLayer = True

                # color = viewer.get_subset_layer_artist(layer.layer).get_layer_color() #getting layer artist succeeds but crashed Vispy!
                color = self.viewer.layers[idx].get_layer_color()

                # Search the vmin in the parent-layer
                for i in range(0,len(self.layers)):
                    if self.layers[i].layer is layer.layer.data:
                        isomin=self.layers[i].vmin

            #otherwise a data object
            else:
                isSubLayer = False
                isomin=layer.vmin

                color = self.viewer.layers[idx].get_layer_color()

                filename = layer.layer.label

            # add layers to listview
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
            
        return layersDict
    
    def getSelectedItems(self, layersDict):
        selectedDict = {}
        for dictItem in layersDict.values():
            if(dictItem['item'].checkState() == Qt.Checked):
                filename = dictItem['filename']
                selectedDict[filename] = dictItem
        return selectedDict

        
    def getSTLOBJString(self):
        # STL and/or OBJ export - string-creation:
        stl_or_obj = ""
        if(self.exportSTL):
            stl_or_obj += "STL "
        if(self.exportSTL and self.exportOBJ):
            stl_or_obj += "and "
        if(self.exportOBJ):
            stl_or_obj += "OBJ "
            
        return stl_or_obj
    
    def saveSelectedItem(self, selectedItem):
        layer = selectedItem['layer']
        filename = selectedItem['filename']
        isomin = selectedItem['isomin']

        # check if subset object
        if isinstance(layer.layer, glue.core.subset_group.GroupedSubset):
            subcube = layer.layer.data.compute_fixed_resolution_buffer(target_data=self.viewer.state.reference_data,
                                                                    bounds=self.bounds,
                                                                    subset_state=layer.layer.subset_state)
            datacube = layer.layer.data.compute_fixed_resolution_buffer(target_data=self.viewer.state.reference_data,
                                                                        bounds=self.bounds,
                                                                        target_cid=layer.attribute)
            data = subcube * datacube

        # otherwise a data object
        else:
            data = layer.layer.compute_fixed_resolution_buffer(target_data=self.viewer.state.reference_data,
                                                            bounds=self.bounds,
                                                            target_cid=layer.attribute)

        # apply smoothing to the data to create nicer surfaces on the model. Ultimately we will probably want users to set this
        data = filters.gaussian_filter(data, 1)

        x_origin = self.viewer.state.x_min  # collect the lower left hand corner pixel x,y,z values of the grid for pyvista
        y_origin = self.viewer.state.y_min
        z_origin = self.viewer.state.z_min

        # I think the voxel spacing will always be 1, because of how glue downsamples to a fixed resolution grid. But don't hold me to this!
        x_dist = 1
        y_dist = 1
        z_dist = 1

        # weird conventions between pyvista and glue data storage.
        data = data.transpose(2, 1, 0)

        # create pyvista grid
        grid = pv.UniformGrid()  # create a spatial reference

        grid.dimensions = (self.viewer.state.resolution, self.viewer.state.resolution,
                        self.viewer.state.resolution)  # set the grid dimensions to match our data

        # edit the spatial reference assuming pixel coordinates using the info extracted from the header earlier
        grid.origin = (x_origin, y_origin, z_origin)  # the bottom left corner of the data set
        grid.spacing = (z_dist, y_dist, x_dist)  # the cell sizes along each axis

        grid.point_arrays["values"] = data.flatten(
            order="F")  # add the data values to the cell data and flatten the array

        # We will want to ultimately open a GUI for user to pick this themselves.
        # Currently the min limit of the main layer is used
        iso_data = grid.contour([isomin])

        if self.exportSTL:
            stl_path = Path(self.savePath, filename + ".stl")
            iso_data.save(stl_path)  # save an STL file

        if self.exportOBJ:
            obj_path = Path(self.savePath, filename) 
            plotter = pv.Plotter()  # create a scene
            _ = plotter.add_mesh(iso_data, color=selectedItem['color'])
            plotter.export_obj(obj_path)  # save as an OBJ
