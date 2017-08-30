from vistas.core.bounds import union_bboxs
from vistas.core.graphics.bounding_box import BoundingBoxHelper
from vistas.core.graphics.objects import Object3D
from vistas.core.task import Task
from vistas.core.threading import Thread


class MeshFactoryWorker(Thread):
    """ Interface for executing work from a Factory in a separate thread. """

    task_name = "Creating Meshes"
    task_description = task_name

    def __init__(self, factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.factory = factory
        self.task = Task(self.task_name, self.task_description)

    def work(self):
        """ The work that should be done by this worker thread. """

        raise NotImplementedError

    def run(self):
        self.task.status = Task.RUNNING
        self.init_event_loop()
        self.work()
        self.task.status = Task.COMPLETE


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
