from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QThread, pyqtSignal
import glue
from scipy.ndimage import filters
import pyvista as pv

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

