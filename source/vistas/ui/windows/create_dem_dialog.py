import sys
import asyncio

from vistas.core.gis.elevation import ElevationService
from vistas.core.threading import Thread
from vistas.core.task import Task
from vistas.ui.project import DataNode
from vistas.ui.windows.data_dialog import CalculateStatsThread


class GenerateDEMThread(Thread):

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

        plugin = self.service.create_dem(self.data_plugin, self.path)
        DataNode(plugin, plugin.data_name, self.controller.project.data_root)
        self.controller.PopulateTreesFromProject(self.controller.project)
        self.task.status = Task.COMPLETE

        thread = CalculateStatsThread(plugin)
        thread.start()
