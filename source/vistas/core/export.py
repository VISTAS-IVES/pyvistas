from vistas.core.threading import Thread
from vistas.core.plugins.visualization import VisualizationPlugin
from vistas.core.graphics.camera import Camera
from vistas.core.task import Task
from vistas.core.timeline import Timeline
from vistas.core.encoders.interface import VideoEncoder
from vistas.ui.utils import post_message

from PIL import Image, ImageDraw, ImageFont


class ExportItem:

    SCENE = 'scene'
    LABEL = 'label'
    VISUALIZATION = 'visualization'
    TIMESTAMP = 'timestamp'
    LEGEND = 'legend'

    def __init__(
            self, item_type='scene', position=(-1, -1), size=(-1, -1), project_node_id=None, flythrough_node_id=None
    ):
        self.item_type = item_type
        self.position = position
        self.size = size
        self.project_node_id = project_node_id
        self.cache = None
        self.z_index = None

        self._viz_plugin = None
        self._camera = None

        self.flythrough = None
        self.use_flythrough_camera = False
        self.flythrough_node_id = flythrough_node_id

        self._font_size = 12
        self._time_format = '%Y-%m-%d'
        self._label = ''

    @property
    def viz_plugin(self) -> VisualizationPlugin:
        return self._viz_plugin

    @viz_plugin.setter
    def viz_plugin(self, viz_plugin: VisualizationPlugin):
        self._viz_plugin = viz_plugin

    @property
    def camera(self) -> Camera:
        return self._camera

    @camera.setter
    def camera(self, camera: Camera):
        self._camera = camera

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, font_size):
        self._font_size = font_size
        self.compute_bbox()

    @property
    def time_format(self) -> str:
        return self._time_format

    @time_format.setter
    def time_format(self, time_format):
        try:
            time = Timeline.app().current.strftime(time_format)  # Throws a ValueError if supplied format is invalid
            self._time_format = time_format
            self.compute_bbox()
        except ValueError:
            post_message("Invalid time specifier", 1)


    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label
        self.compute_bbox()

    def compute_bbox(self):
        font = ImageFont.load_default()
        if self.item_type == self.LABEL:
            self.size = font.getsize(self.label)
        elif self.item_type == self.TIMESTAMP:
            self.size = font.getsize(Timeline.app().current.strftime(self.time_format))

    def snapshot(self, force=False):
        if not force and self.cache.size == self.size:
            return self.cache
        else:
            self.refresh_cache()

        return self.cache

    def refresh_cache(self):

        snapshot = Image.new("RGBA", self.size)
        draw = ImageDraw.Draw(snapshot)

        if self.item_type == self.SCENE:
            if self.use_flythrough_camera:
                snapshot = self.flythrough.camera.render_to_bitmap(*self.size)
            else:
                snapshot = self.camera.render_to_bitmap(*self.size)
        elif self.item_type == self.LEGEND and self.viz_plugin is not None:
            snapshot = self.viz_plugin.get_legend(*self.size)
        elif self.item_type == self.VISUALIZATION and self.viz_plugin is not None:
            pass    # Todo - implement 2D visualizations
            # snapshot = self.viz_plugin.render(*self.size).as_bitmap()
        elif self.item_type == self.LABEL:
            draw.text((0, 0), self.label)
        elif self.item_type == self.TIMESTAMP:
            draw.text((0, 0), Timeline.app().current.strftime(self._time_format))

        self.cache = snapshot

    def draw(self, image):
        image.paste(self.cache, self.position)


class Exporter(Thread):

    def __init__(self, size=(740, 480)):
        super().__init__()
        self.items = []
        self.size = size

        self.video_fps = None
        self.animation_fps = None
        self.flythrough_fps = None

        self.video_frames = None
        self.animation_frames = None

        self.animation_start = None
        self.animation_end = None
        self.animation_step = None

        self.is_temporal = False

        self.encoder = None
        self.path = None
        self.task = None

    def recalculate_z_order(self):
        for i, item in enumerate(self.items):
            item.z_index = i

    def fit_to_items(self):
        width, height, left, top = 0, 0, *self.size
        for item in self.items:
            left = min(left, item.position[0])
            top = min(top, item.position[1])

        for item in self.items:
            old_pos = item.position
            item.position = (old_pos[0] - left, old_pos[1] - top)
            width = max(width, item.position[0] + item.size[0])
            height = max(height, item.position[1] + item.size[1])

        self.size = (width, height)

    def add_item(self, item: ExportItem):
        self.items.append(item)
        item.z_index = len(self.items) - 1

    def remove_item(self, item: ExportItem):
        if item in self.items:
            self.items.remove(item)
        self.recalculate_z_order()

    def send_to_front(self, item: ExportItem):
        self.items.append(self.items.pop(self.items.index(item)))
        self.recalculate_z_order()

    def send_to_back(self, item: ExportItem):
        self.items.insert(0, self.items.pop(self.items.index(item)))
        self.recalculate_z_order()

    def update_z_order(self):
        self.items.sort(key=lambda x: x.z_index)
        self.recalculate_z_order()

    def export_current_frame(self):
        result = Image.new("RGBA", self.size)
        for item in self.items:
            item.refresh_cache()
            item.draw(result)
        return result

    def export_frames(self, encoder: VideoEncoder, path):

        self.task = Task("Exporting Frames", "Exporting frames...")
        self.encoder = encoder
        self.path = path

        self.start()

        return self.task

    def refresh_item_caches(self):
        for item in self.items:
            item.refresh_cache()

    def run(self):

        self.task.target = self.video_frames-1
        self.encoder.fps = self.video_fps
        self.task.progress = 0
        self.task.status = Task.RUNNING
        timeline = Timeline.app()
        timeline.current = self.animation_start
        self.encoder(self.path, *self.size)

        pass # Todo - finish implementing

        self.encoder.finalize()
        self.task.status = Task.COMPLETE
