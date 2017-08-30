import mercantile
from vistas.core.graphics.factory import MeshFactory, MeshFactoryWorker
from vistas.core.graphics.feature.geometry import FeatureGeometry
from vistas.core.graphics.feature.shader import FeatureShaderProgram
from vistas.core.task import Task
from vistas.ui.utils import post_redisplay


class FeatureFactoryWorker(MeshFactoryWorker):

    task_name = "Rendering Features"

    def work(self):

        if self.factory.needs_vertices:
            self.task.status = Task.RUNNING
            self.task.name = 'Generating meshes'
            verts, indices, normals = self.factory.generate_meshes(self.task)
            self.sync_with_main(self.factory.add_features_to_scene, (verts, indices, normals), block=True)
            self.factory.needs_vertices = False

        if self.factory.needs_color and not self.task.should_stop:
            self.task.status = Task.RUNNING
            self.task.name = 'Coloring meshes'
            colors = self.factory.generate_colors(self.task)
            self.sync_with_main(self.factory.color_features, (colors, None), block=True)
            self.factory.needs_color = False

        self.sync_with_main(post_redisplay)
        self.task.status = Task.COMPLETE




class FeatureFactory(MeshFactory):
    """ An MeshFactory for handling feature collection rendering """

    worker_class = FeatureFactoryWorker


    def __init__(self, plugin, zoom=10):
        self.renderable = None
        self.plugin = plugin
        self.extent = plugin.extent

        self._ul = None
        self._br = None
        self.bounding_box = None
        self._zoom = None
        self.meters_per_px = None
        self.zoom = zoom    # update bounds

        self._color_func = None
        self._render_thread = None

        self._cache = self.plugin.path.replace('.shp', '.ttt')
        self._npz_path = self._cache + '.npz'

        self.needs_vertices = True
        self.needs_color = True

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        self._zoom = zoom
        self.needs_vertices = True
        tiles = list(self.extent.tiles(self.zoom))
        self._ul = tiles[0]
        self._br = tiles[-1]

        self.meters_per_px = meters_per_px(self.zoom)

        self.bounding_box = BoundingBox(
            0, 0, -10,
            (self._br.x - self._ul.x + 1) * TILE_SIZE, (self._br.y - self._ul.y + 1) * TILE_SIZE, 10
        )
        if self.renderable:
            self.renderable.bounding_box = self.bounding_box
            self.renderable.width = (self._br.x - self._ul.x + 1) * TILE_SIZE

    def render(self, scene):
        """ Renders the feature collection into a given scene. """
        if self._render_thread is not None:
            self._render_thread.task.status = Task.SHOULD_STOP
            self._render_thread = None
        self._render_thread = FeatureCollectionRenderThread(self, scene)
        self._render_thread.start()

    def add_features_to_scene(self, vertices, indices, normals, scene):
        """ Render callback to add the the feature collection's renderable to the specified scene. """

        if self.renderable is None:
            self.renderable = FeatureRenderable(vertices, indices, self._ul, self._br)
            scene.add_object(self.renderable)

        # Allocate buffers for this mesh
        mesh = self.renderable.mesh
        vert_buf = mesh.acquire_vertex_array()
        vert_buf[:] = vertices.ravel()
        mesh.release_vertex_array()

        index_buf = mesh.acquire_index_array()
        index_buf[:] = indices.ravel()
        mesh.release_index_array()

        norm_buf = mesh.acquire_normal_array()
        norm_buf[:] = normals.ravel()
        mesh.release_normal_array()

        self.renderable.bounding_box = self.bounding_box

    def color_features(self, colors, _=None):
        """ Coloring callback to set the colors of the feature collection. """

        if self.renderable is not None:
            color_buf = self.renderable.mesh.acquire_color_array()
            flat = colors.ravel()
            if flat.size == color_buf.size:
                color_buf[:] = flat
            self.renderable.mesh.release_color_array()

    @property
    def mercator_bounds(self):
        """ The zxy tile (mercator) bounds of the feature collection. """

        ul_bounds = mercantile.xy_bounds(self._ul)
        br_bounds = mercantile.xy_bounds(self._br)
        return mercantile.Bbox(ul_bounds.left, br_bounds.bottom, br_bounds.right, ul_bounds.top)

    @property
    def geographic_bounds(self):
        """ The geographic bounds of the underlying tiles of the feature collection. """

        ul_bounds = mercantile.bounds(self._ul)
        br_bounds = mercantile.bounds(self._br)
        return mercantile.LngLatBbox(ul_bounds.west, br_bounds.south, br_bounds.east, ul_bounds.north)

    def generate_meshes(self, task=None, use_cache=True):
        """ Generates polygon mesh vertices for a feature collection """

        mercator = pyproj.Proj(init='EPSG:3857')
        mbounds = self.mercator_bounds

        # Check if a cache for this collection exists
        if use_cache and os.path.exists(self._npz_path):
            if task:
                task.name = 'Loading meshes from cache'
                task.status = task.INDETERMINATE

            nfile = numpy.load(self._npz_path)
            verts = nfile['verts']

        # Build it out
        else:
            task.progress = 0
            task.target = self.plugin.get_num_features()

            project = partial(pyproj.transform, self.extent.projection, mercator)   # Our projection method

            tris = []
            offsets = []
            offset = 0
            for i, feature in enumerate(self.plugin.get_features()):
                shape = transform(project, geometry.shape(feature['geometry']))
                if task:
                    task.inc_progress()

                if isinstance(shape, geometry.Polygon):
                    polys = [list(shape.exterior.coords)[:-1]]
                elif isinstance(shape, geometry.MultiPolygon):
                    polys = [list(p.exterior.coords)[:-1] for p in shape]
                else:
                    raise ValueError("Can't render non polygons!")

                for p in polys:
                    triangulation = triangle.triangulate(dict(vertices=numpy.array(p)))
                    t = triangulation.get('vertices')[triangulation.get('triangles')].reshape(-1, 2)
                    offset += t.size
                    tris.append(t)

                offsets.append(offset)

            triangles = numpy.concatenate(tris)
            offsets = numpy.array(offsets)

            # Make room for elevation info
            xs = triangles[:, 0]
            ys = triangles[:, 1]
            verts = numpy.dstack((xs, numpy.zeros_like(xs), ys))[0]
            verts = verts.astype(numpy.float32)

            # cache the vertices
            if use_cache:
                numpy.savez(self._cache, verts=verts, offsets=offsets)

        # Translate vertices to scene coordinates
        # Scale vertices according to current mercator_bounds
        verts[:, 0] = (verts[:, 0] - mbounds.left) / (mbounds.right - mbounds.left)
        verts[:, 2] = (1 - (verts[:, 2] - mbounds.bottom) / (mbounds.top - mbounds.bottom))

        # Get data DEM to sample elevation from.
        e = ElevationService()
        dem = e.create_data_dem(self.extent, self.zoom, merge=True)
        dheight, dwidth = dem.shape

        # Index into current DEM and assign heights
        us = numpy.floor(verts[:, 0] * dwidth).astype(int)
        vs = numpy.floor(verts[:, 2] * dheight).astype(int)
        verts[:, 1] = dem[vs, us].ravel() / self.meters_per_px

        # Scale vertices based on tile size
        verts[:, 0] *= (self._br.x - self._ul.x + 1) * TILE_SIZE
        verts[:, 2] *= (self._br.y - self._ul.y + 1) * TILE_SIZE

        # Vertex indices are assumed to be unique
        indices = numpy.arange(verts.shape[0])

        normal_dem = e.create_data_dem(self.extent, self.zoom, merge=True, src=e.AWS_NORMALS)
        normals = normal_dem[vs, us].ravel()

        return verts, indices, normals

    @staticmethod
    def _default_color_function(feature, data):
        """
        Base color function for coloring features.
        :param feature: The feature to color
        :param data: Persistent data throughout the life of a single render
        :return: The RGBColor to color the feature
        """
        return RGBColor(0.5, 0.5, 0.5)

    def set_color_function(self, func):
        self._color_func = func

    def generate_colors(self, task=None):
        """ Generates a color buffer for the feature collection """

        # Color indices are stored in the cache
        offsets = numpy.load(self._npz_path)['offsets']
        color_func = self._color_func
        if not color_func:
            color_func = self._default_color_function
        colors = []

        if task:
            task.progress = 0
            task.target = self.plugin.get_num_features()

        # We use a mutable data structure that is limited to this thread's scope and can be mutated
        # based on color_func's scope. This allows multiple color threads to occur without locking.
        mutable_color_data = {}
        for i, feature in enumerate(self.plugin.get_features()):
            if i == 0:
                left = 0
            else:
                left = offsets[i - 1]
            right = offsets[i]

            if task:
                if task.should_stop:
                    break
                task.inc_progress()

            num_vertices = (right - left) // 2
            color = numpy.array(color_func(feature, mutable_color_data).rgb.rgb_list, dtype=numpy.float32)
            for v in range(num_vertices):
                colors.append(color)
        colors = numpy.stack(colors)

        return colors


