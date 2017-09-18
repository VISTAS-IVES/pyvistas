import numpy
from OpenGL.GL import *

from vistas.core.graphics.shader import ShaderProgram
from vistas.core.graphics.texture import Texture
from vistas.core.paths import get_builtin_shader


class TerrainShaderProgram(ShaderProgram):
    """ Most basic terrain shading program. """
    def __init__(self):
        super().__init__()
        self.height_factor = 1.0

    def pre_render(self, camera):
        super().pre_render(camera)
        self.uniform1f("heightFactor", self.height_factor)


class TerrainColorShaderProgram(TerrainShaderProgram):
    """
    Applies data-based color effects onto a TerrainColorGeometry. Can render rasterized features as a texture overlay.
    """

    def __init__(self):
        super().__init__()

        self.attach_shader(get_builtin_shader('terrain_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(get_builtin_shader('terrain_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

        tw, th = 512, 512
        img_data = (numpy.ones((tw, th, 3)).astype(numpy.uint8) * 255).ravel()
        self.boundary_texture = Texture(data=img_data, width=tw, height=tw)

        self.has_color = False
        self.has_boundaries = False
        self.hide_no_data = False
        self.per_vertex_color = True
        self.per_vertex_lighting = False

        self.is_filtered = False
        self.filter_min = self.filter_max = 0

        self.nodata_value = 0.0
        self.min_value = 0.0
        self.max_value = 0.0
        self.min_color = [0, 0, 0, 1]
        self.max_color = [1, 0, 0, 1]
        self.nodata_color = [.5, .5, .5, 1]
        self.boundary_color = [0, 0, 0, 1]

    def pre_render(self, camera):
        super().pre_render(camera)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.boundary_texture.texture)
        self.uniform1i("boundaryTexture", 0)

        self.uniform1i("hideNoData", self.hide_no_data)
        self.uniform1i("perVertexColor", self.per_vertex_color)
        self.uniform1i("perVertexLighting", self.per_vertex_lighting)
        self.uniform1i("hasColor", self.has_color)
        self.uniform1i("hasBoundaries", self.has_boundaries)

        self.uniform1i("isFiltered", self.is_filtered)
        self.uniform1f("filterMin", self.filter_min)
        self.uniform1f("filterMax", self.filter_max)

        self.uniform1f("noDataValue", self.nodata_value)
        self.uniform1f("minValue", self.min_value)
        self.uniform1f("maxValue", self.max_value)
        self.uniform4fv("minColor", 1, self.min_color)
        self.uniform4fv("maxColor", 1, self.max_color)
        self.uniform4fv("noDataColor", 1, self.nodata_color)
        self.uniform4fv("boundaryColor", 1, self.boundary_color)

    def post_render(self, camera):
        glBindTexture(GL_TEXTURE_2D, 0)
        super().post_render(camera)


class TerrainTileShaderProgram(TerrainShaderProgram):
    """ Terrain shading program for TerrainTileGeometry. """

    def __init__(self):
        super().__init__()
        self.attach_shader(get_builtin_shader('tile_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(get_builtin_shader('tile_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()
