from ctypes import c_uint, c_void_p

import numpy
from OpenGL.GL import *
from pyrr import Vector3
from pyrr.vector3 import generate_vertex_normals

from vistas.core.bounds import BoundingBox
from vistas.core.graphics.utils import map_buffer


class Geometry:
    """ Base geometry class for 3D objects. Provides ability to specify vertex, normal, and color array buffers. """

    POINTS = GL_POINTS
    LINE_STRIP = GL_LINE_STRIP
    LINES = GL_LINES
    TRIANGLE_STRIP = GL_TRIANGLE_STRIP
    TRIANGLE_FAN = GL_TRIANGLE_FAN
    TRIANGLES = GL_TRIANGLES
    QUAD_STRIP = GL_QUAD_STRIP
    QUADS = GL_QUADS
    POLYGON = GL_POLYGON

    def __init__(
            self, num_indices=0, num_vertices=0, has_normal_array=False, has_color_array=False,
            has_texture_coords=False, use_rgba=False, mode=TRIANGLE_STRIP
    ):
        self.bounding_box = None
        self.num_indices = num_indices
        self.num_vertices = num_vertices

        self.mode = mode
        self.has_index_array = num_indices > 0
        self.has_vertex_array = num_vertices > 0
        self.has_normal_array = has_normal_array
        self.has_color_array = has_color_array
        self.has_texture_coords = has_texture_coords
        self.use_rgba = use_rgba

        self.vertex_array_object = glGenVertexArrays(1)

        # Client-side copy of vertex and uv data for quick access. Properties handle necessary updates to GPU buffers
        self._indices = None
        self._vertices = None
        self._normals = None
        self._texcoords = None
        self._colors = None

        glBindVertexArray(self.vertex_array_object)

        if self.has_index_array:
            self.index_buffer = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, num_indices * sizeof(c_uint), None, GL_DYNAMIC_DRAW)

        if self.has_vertex_array:
            self.vertex_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vertex_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * 3 * sizeof(GLfloat), None, GL_DYNAMIC_DRAW)

        if self.has_normal_array:
            self.normal_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.normal_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * 3 * sizeof(GLfloat), None, GL_DYNAMIC_DRAW)

        if self.has_color_array:
            size = 4 if self.use_rgba else 3

            self.color_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.color_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * size * sizeof(GLfloat), None, GL_DYNAMIC_DRAW)

        if self.has_texture_coords:
            self.texcoords_buffer = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.texcoords_buffer)
            glBufferData(GL_ARRAY_BUFFER, num_vertices * 2 * sizeof(GLfloat), None, GL_STATIC_DRAW)

        # Inform OpenGL where each of the VBOs are located in a given shader program.
        if self.has_vertex_array:
            glBindBuffer(GL_ARRAY_BUFFER, self.vertex_buffer)  # location 0 = 'position'
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * 3, None)

        if self.has_normal_array:
            glBindBuffer(GL_ARRAY_BUFFER, self.normal_buffer)  # location 1 = 'normal'
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * 3, None)

        if self.has_texture_coords:
            glBindBuffer(GL_ARRAY_BUFFER, self.texcoords_buffer)   # location 2 = 'uv', i.e. texcoords
            glEnableVertexAttribArray(2)
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * 2, None)

        if self.has_color_array:
            size = 4 if self.use_rgba else 3

            glBindBuffer(GL_ARRAY_BUFFER, self.color_buffer)   # location 3 = 'color'
            glEnableVertexAttribArray(3)
            glVertexAttribPointer(3, size, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * size, None)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    @property
    def indices(self):
        if self._indices is None and self.has_index_array:
            index_buf = self.acquire_index_array(GL_READ_ONLY)
            self._indices = index_buf[:]
            self.release_index_array()
        return self._indices

    @indices.setter
    def indices(self, indices):
        self._indices = indices.ravel()
        index_buf = self.acquire_index_array()
        index_buf[:] = self._indices
        self.release_index_array()

    @property
    def vertices(self):
        if self._vertices is None and self.has_vertex_array:
            vert_buf = self.acquire_vertex_array(GL_READ_ONLY)
            self._vertices = vert_buf[:]
            self.release_vertex_array()
        return self._vertices

    @vertices.setter
    def vertices(self, verts):
        self._vertices = verts.ravel()
        vert_buf = self.acquire_vertex_array()
        vert_buf[:] = self._vertices
        self.release_vertex_array()

    @property
    def normals(self):
        if self._normals is None and self.has_normal_array:
            norm_buf = self.acquire_normal_array(GL_READ_ONLY)
            self._normals = norm_buf[:]
            self.release_normal_array()
        return self._normals

    @normals.setter
    def normals(self, norms):
        self._normals = norms.ravel()
        norm_buf = self.acquire_normal_array()
        norm_buf[:] = self._normals
        self.release_normal_array()

    @property
    def texcoords(self):
        if self._texcoords is None and self.has_texture_coords:
            uvs = self.acquire_texcoords_array(GL_READ_ONLY)
            self._texcoords = uvs[:]
            self.release_texcoords_array()
        return self._texcoords

    @texcoords.setter
    def texcoords(self, texcoords):
        self._texcoords = texcoords.ravel()
        uvs = self.acquire_texcoords_array()
        uvs[:] = self._texcoords
        self.release_texcoords_array()

    @property
    def colors(self):
        if self._colors is None and self.has_color_array:
            colors = self.acquire_color_array(GL_READ_ONLY)
            self._colors = colors[:]
            self.release_color_array()
        return self._colors

    @colors.setter
    def colors(self, colors):
        self._colors = colors.ravel()
        color_buf = self.acquire_color_array()
        color_buf[:] = self._colors
        self.release_color_array()

    def compute_bounding_box(self):
        """ Compute the BoundingBox for this geometry directly from the vertex data. """

        vertices = self.vertices.reshape(-1, 3)
        xs = vertices[:, 0]
        ys = vertices[:, 1]
        zs = vertices[:, 2]

        x_min = float(xs.min())
        x_max = float(xs.max())
        y_min = float(ys.min())
        y_max = float(ys.max())
        z_min = float(zs.min())
        z_max = float(zs.max())

        self.bounding_box = BoundingBox(x_min, y_min, z_min, x_max, y_max, z_max)

    def compute_normals(self):
        """ Compute vertex normals for a geometry. """

        if self.has_normal_array:
            self.normals = generate_vertex_normals(self.vertices.reshape(-1, 3), self.indices.reshape(-1, 3))

    def dispose(self):
        """ Delete this object's vertex buffers. This object should not be used for rendering for now one. """

        if self.has_index_array:
            glDeleteBuffers(1, [self.index_buffer])

        if self.has_vertex_array:
            glDeleteBuffers(1, [self.vertex_buffer])

        if self.has_normal_array:
            glDeleteBuffers(1, [self.normal_buffer])

        if self.has_color_array:
            glDeleteBuffers(1, [self.color_buffer])

        if self.has_texture_coords:
            glDeleteBuffers(1, [self.texcoords_buffer])

        glDeleteVertexArrays(1, [self.vertex_array_object])

    def acquire_index_array(self, access=GL_WRITE_ONLY):
        """ Note: Mesh.release_index_array() must be called once the buffer is no longer needed """

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        return map_buffer(GL_ELEMENT_ARRAY_BUFFER, numpy.uint32, access, self.num_indices * sizeof(c_uint))

    def acquire_vertex_array(self, access=GL_WRITE_ONLY):
        """ Note: Mesh.release_vertex_array() must be called once the buffer is no longer needed """

        glBindBuffer(GL_ARRAY_BUFFER, self.vertex_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, access, self.num_vertices * 3 * sizeof(GLfloat))

    def acquire_normal_array(self, access=GL_WRITE_ONLY):
        """ Note: Mesh.release_normal_array() must be called once the buffer is no longer needed """

        glBindBuffer(GL_ARRAY_BUFFER, self.normal_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, access, self.num_vertices * 3 * sizeof(GLfloat))

    def acquire_color_array(self, access=GL_WRITE_ONLY):
        """ Note: Mesh.release_color_array() must be called once the buffer is no longer needed """

        size = 4 if self.use_rgba else 3

        glBindBuffer(GL_ARRAY_BUFFER, self.color_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, access, self.num_vertices * size * sizeof(GLfloat))

    def acquire_texcoords_array(self, access=GL_WRITE_ONLY):
        glBindBuffer(GL_ARRAY_BUFFER, self.texcoords_buffer)
        return map_buffer(GL_ARRAY_BUFFER, numpy.float32, access, self.num_vertices * 2 * sizeof(GLfloat))

    def release_index_array(self):
        glUnmapBuffer(GL_ELEMENT_ARRAY_BUFFER)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def release_normal_array(self):
        glUnmapBuffer(GL_ARRAY_BUFFER)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def release_color_array(self):
        self.release_normal_array()

    def release_vertex_array(self):
        self.release_normal_array()

    def release_texcoords_array(self):
        self.release_normal_array()


class InstancedGeometry(Geometry):
    """
    A type of Geometry that uses an instanced vertex buffer to generate many copies of similiar geometry efficiently.
    For example, a Mesh whose geometry is an InstancedGeometry can use a ShaderProgram to determine offsets and other
    per-instance attributes for generating large amounts of similar geometry that have slight differences. A classic
    example is rendering large amounts of grass. Grass can have different sizes, tilts and rotations, but the base
    geometry is the exact same.
    """

    DEFAULT_LOCATION = 4    # layout(location = DEFAULT_LOCATION) in <type> <name>;

    def __init__(self, max_instances=0, instance_buffer_spec=None, *args, **kwargs):
        """
        Constructor
        :param max_instances: The maximum number of instances to draw on screen. If this is changed, a new
        InstancedGeometry should be created instead of changing the max_instances for the existing object.
        :param instance_buffer_spec: An integer or list of integers specifying the instance buffer size(s) for . Often
        times, there is a need to define lots of data per instance, but vertex attributes are limited to a max of 4 floats
        per vertex attribute. If this is the case, specifying the vertex buffer sizes (i.e. [2, 1, 3]) allows for this
        geometry class to define customized memory layout within the instance buffer, decoupling the memory layout logic
        from the shader program logic. The shader program only needs to know which buffer to access data from.
        Layout locations start at position 4 (i.e. layout(location = 4)) and increment by 1
        (e.x. if instance_buffer_spec=[2, 2]), then there will be buffers at location 4 and location 5 of size vec2.
        :param args: Arguments passed to Geometry.
        :param kwargs: Keyword arguments passed to Geometry.
        """

        super().__init__(*args, **kwargs)

        # Can be used in shader to inform each instance that it's position needs to shift by some uniform amount
        self.vertex_offsets = Vector3([0., 0., 0.])
        self.vertex_scalars = Vector3([1., 1., 1.])

        # We can often have a lot of instance data being passed. We can spread this data across multiple buffers
        if instance_buffer_spec is None:
            instance_buffer_spec = [3]
        elif isinstance(instance_buffer_spec, int):
            instance_buffer_spec = [instance_buffer_spec]

        assert all(0 < x <= 4 for x in instance_buffer_spec)    # OpenGL vertex attribute limit

        self.instance_buffer_spec = instance_buffer_spec
        self.instance_buffer_size = sum(self.instance_buffer_spec)
        self._instance_data = None
        self.max_instances = self.num_instances = max_instances

        glBindVertexArray(self.vertex_array_object)
        self.instance_buffer = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, self.instance_buffer)
        glBufferData(
            GL_ARRAY_BUFFER, self.max_instances * sizeof(GLfloat) * self.instance_buffer_size, None, GL_STATIC_DRAW
        )

        offset = 0
        for i, size in enumerate(self.instance_buffer_spec):
            loc = self.DEFAULT_LOCATION + i
            # Setup location for shaders
            glEnableVertexAttribArray(loc)    # location in <loc> <size> <name>
            glVertexAttribPointer(
                loc, size, GL_FLOAT, GL_FALSE, sizeof(GLfloat) * self.instance_buffer_size, c_void_p(offset)
            )

            # Inform OpenGL instance_buffer is an instanced buffer and should divide buffer data to each instance
            glVertexAttribDivisor(loc, 1)
            offset += size * sizeof(GLfloat)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def dispose(self):
        super().dispose()
        glDeleteBuffers(1, [self.instance_buffer])

    def acquire_instance_array(self, access=GL_WRITE_ONLY):
        glBindBuffer(GL_ARRAY_BUFFER, self.instance_buffer)
        return map_buffer(
            GL_ARRAY_BUFFER, numpy.float32, access, self.max_instances * self.instance_buffer_size * sizeof(GLfloat)
        )

    def release_instance_array(self):
        glUnmapBuffer(GL_ARRAY_BUFFER)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    @property
    def instance_data(self):
        if self._instance_data is None:
            instance_buf = self.acquire_instance_array(GL_READ_ONLY)
            self._instance_data = instance_buf[:]
            self.release_instance_array()
        return self._instance_data

    @instance_data.setter
    def instance_data(self, data):
        self._instance_data = data.ravel()
        instance_buf = self.acquire_instance_array()
        instance_buf[:] = self._instance_data
        self.release_instance_array()
