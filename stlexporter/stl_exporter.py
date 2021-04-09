
from glue.config import viewer_tool
from glue.viewers.common.tool import Tool
import pyvista as pv
from scipy.ndimage import filters

from PyQt5.QtWidgets import QFileDialog, QProgressDialog
from PyQt5.QtCore import Qt 

import glue
from stlexporter import ICON


@viewer_tool
class StlExporter(Tool):

    icon = ICON
    tool_id = 'stl_exporter'
    action_text = 'STL Exporter'
    tool_tip = 'STL Exporter'

    def __init__(self, viewer):
        super(StlExporter, self).__init__(viewer)

    def activate(self):
        savePath = QFileDialog.getExistingDirectory()

        if(savePath == ""): # Cancel if Prompt was cancelled
            return

        # grab viewer
        viewer = self.viewer

        #get the data layers of the viewer.
        layers =  viewer.state.layers

        #grab the xyz bounds of the viewer
        bounds = [(viewer.state.z_min, viewer.state.z_max, viewer.state.resolution), (viewer.state.y_min, viewer.state.y_max, viewer.state.resolution), (viewer.state.x_min, viewer.state.x_max, viewer.state.resolution)]

        # Create Progress Dialog
        progress = QProgressDialog("Creating STL files...", None, 0, len(layers))
        progress.setWindowTitle("STL Export")
        progress.setWindowModality(Qt.WindowModal)
        progress.forceShow()
        progress.setValue(0)

        count = 0

        for layer in layers:
            #check if subset object
            if isinstance(layer.layer,glue.core.subset_group.GroupedSubset):
                subcube=layer.layer.data.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data, bounds=bounds, subset_state=layer.layer.subset_state)
                datacube=layer.layer.data.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data, bounds=bounds,target_cid=layer.attribute)
                data=subcube*datacube

                # Name file with main data layer at beginning if subset
                filename = layer.layer.data.label + "_" + layer.layer.label + ".stl"

                for i in range(0,len(viewer.state.layers)):
                    if layers[i].layer is layer.layer.data:
                        isomin=layers[i].vmin
                        isomax=layers[i].vmax

            #otherwise a data object
            else:            
                data=layer.layer.compute_fixed_resolution_buffer(target_data=viewer.state.reference_data, bounds=bounds, target_cid=layer.attribute)
                isomin=layer.vmin
                isomax=layer.vmax

                filename = layer.layer.label + ".stl"
            
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

            iso_data.save(savePath + "\\" + filename) #save an STL file

            count += 1
            progress.setValue(count)

    def close(self):
        pass

