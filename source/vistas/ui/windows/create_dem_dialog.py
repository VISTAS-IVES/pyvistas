import asyncio
import sys

from vistas.core.gis.elevation import ElevationService
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.project import DataNode


class GenerateDEMThread(Thread):
    """ A worker thread for generating a Digital Elevation Map (DEM) from a DataPlugin. """

    def __init__(self, node, controller, path):
        super().__init__()
        self.data_plugin = node.data
        self.controller = controller
        self.path = path
        self.service = ElevationService()
        self.task = Task(
            "Generating DEM from template data source", "Please wait: Generating DEM from template data source"
        )
        self.task.status = Task.INDETERMINATE

    def run(self):

        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        plugin = self.service.create_dem_from_plugin(self.data_plugin, self.path, self.task)
        DataNode(plugin, plugin.data_name, self.controller.project.data_root)
        self.controller.PopulateTreesFromProject(self.controller.project)
        self.task.status = Task.COMPLETE
