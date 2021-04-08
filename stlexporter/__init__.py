import os

ICON = os.path.abspath(os.path.join(os.path.dirname(__file__), 'btn_icon.png'))


def setup():

    from glue.config import qt_client
    from .stl_exporter import StlExporter

    from glue_vispy_viewers.volume.volume_viewer import VispyVolumeViewer
    VispyVolumeViewer.tools.append('stl_exporter')

