import mercantile

from vistas.core.bounds import union_bboxs
from vistas.core.graphics.bounding_box import BoundingBoxHelper
from vistas.core.graphics.object import Object3D
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay


def use_event_loop(func):
    """ Wraps a Thread run function to ensure an event loop is started and refreshes the UI when compeleted. """
    def decorator(*args, **kwargs):
        self = args[0]
        self.task.status = Task.RUNNING
        self.init_event_loop()
        func(*args, **kwargs)
        self.sync_with_main(post_redisplay)
        self.task.status = Task.COMPLETE
    return decorator


class MeshFactoryWorker(Thread):
    """ Interface for executing work from a MeshFactory in a separate thread. """

    task_name = "Creating Meshes"
    task_description = task_name

    def __init__(self, factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.factory = factory
        self.task = Task(self.task_name, self.task_description)


class MeshFactory(Object3D):
    """
    Interface for building grouped 3D objects that require neighborhood knowledge and can be rendered into a scene.
    """

    worker_class = MeshFactoryWorker

    def __init__(self):
        super().__init__()
        self.items = []     # List[Mesh]
        self.bbox_helper = BoundingBoxHelper(self)

    def update(self):
        self.bbox_helper.update()

    def build(self):
        """ Signal that work needs to be done. """

        self.worker_class(self).start()

    def dispose(self):
        """ Dispose of all current meshes. """

        for obj in self.items:
            obj.geometry.dispose()
        del self.items[:]

    @property
    def bounding_box(self):
        return union_bboxs([x.bounding_box_world for x in self.items])

    def raycast(self, raycaster):
        intersects = []
        for obj in self.items:
            intersects += obj.raycast(raycaster)
        return intersects

    def render_bounding_box(self, color, camera):
        for obj in self.items:
            obj.render_bounding_box(color, camera)

    def render(self, camera):
        for obj in self.items:
            obj.render(camera)


class MapMeshFactory(MeshFactory):
    """ A MeshFactory that is geospatially referenced. """

    def __init__(self, extent, shader, plugin=None, initial_zoom=10):
        super().__init__()
        self.shader = shader
        self.plugin = plugin
        self.extent = extent
        self._zoom = None
        self.tiles = []
        self._ul = None
        self._br = None
        self.zoom = initial_zoom

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        if zoom != self._zoom:
            self._zoom = zoom
            self.tiles = self.extent.tiles(self.zoom)
            self._ul = self.tiles[0]
            self._br = self.tiles[-1]

            # Destroy these meshes
            self.dispose()

            # Now build new meshes
            self.build()

    @property
    def mercator_bounds(self):
        ul_bounds = mercantile.xy_bounds(self._ul)
        br_bounds = mercantile.xy_bounds(self._br)
        return mercantile.Bbox(ul_bounds.left, br_bounds.bottom, br_bounds.right, ul_bounds.top)

    @property
    def geographic_bounds(self):
        ul_bounds = mercantile.bounds(self._ul)
        br_bounds = mercantile.bounds(self._br)
        return mercantile.LngLatBbox(ul_bounds.west, br_bounds.south, br_bounds.east, ul_bounds.north)
