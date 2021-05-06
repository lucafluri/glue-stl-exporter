from glue.config import viewer_tool
from glue.viewers.common.tool import Tool
from stlexporter import ICON

from .ui import MainWindow

@viewer_tool
class StlExporter(Tool):
    icon = ICON
    tool_id = 'stl_exporter'
    action_text = 'STL Exporter'
    tool_tip = 'STL Exporter'

    def __init__(self, viewer):
        super(StlExporter, self).__init__(viewer)

    def activate(self):
        dialog = MainWindow()
        viewer = self.viewer

        #get the data layers of the viewer.
        layers =  viewer.state.layers

        dialog.create_layout(viewer, layers)
        dialog.show()
    
    def close(self):
        pass

