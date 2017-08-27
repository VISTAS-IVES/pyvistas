from unittest.mock import patch

import numpy
from PIL import Image

from tests.fixtures import generic_app
from vistas.core.graphics import texture

generic_app # Make the fixture import look used to IDEs


@patch('{}.glGenTextures'.format(texture.__name__))
@patch('{}.glBindTexture'.format(texture.__name__))
@patch('{}.glTexParameteri'.format(texture.__name__))
@patch('{}.glDeleteTextures'.format(texture.__name__))
def test_texture_with_data(m1, m2, m3, m4, generic_app):
    def test_callback():
        data = numpy.arange(300)

        with patch('{}.glTexImage2D'.format(texture.__name__)) as m:
            t = texture.Texture(data, 10, 10)
            assert m.called
            assert m.call_args[0][-1] is data
            assert m.call_args[0][3:5] == (10, 10)

    generic_app(test_callback)


@patch('{}.glGenTextures'.format(texture.__name__))
@patch('{}.glBindTexture'.format(texture.__name__))
@patch('{}.glTexParameteri'.format(texture.__name__))
@patch('{}.glDeleteTextures'.format(texture.__name__))
def test_texture_with_image(m1, m2, m3, m4, generic_app):
    def test_callback():
        im = Image.new('RGB', (10, 10), (0, 0, 0, 0))

        with patch('{}.glTexImage2D'.format(texture.__name__)) as m:
            t = texture.Texture(im)
            assert m.called
            assert (m.call_args[0][-1].ravel() == numpy.zeros(300)).all()
            assert m.call_args[0][3:5] == (10, 10)

    generic_app(test_callback)
