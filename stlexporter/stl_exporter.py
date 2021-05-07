from glue.config import viewer_tool
from glue.viewers.common.tool import Tool
from stlexporter import ICON

from stlexporter.ui import MainWindow
from stlexporter.controller import Controller

@viewer_tool
class StlExporter(Tool):
    icon = ICON
    tool_id = 'stl_exporter'
    action_text = 'STL Exporter'
    tool_tip = 'STL Exporter'

    def __init__(self, viewer):
        super(StlExporter, self).__init__(viewer)

    def activate(self):
        viewer = self.viewer
        layers =  viewer.state.layers
        
        dialog = MainWindow(Controller(viewer, layers))

        dialog.createMainWindow()
        dialog.show()
    
    def close(self):
        pass

