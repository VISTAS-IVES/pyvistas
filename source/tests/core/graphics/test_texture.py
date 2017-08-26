from unittest.mock import patch

import numpy
from PIL import Image

from tests.fixtures import vistas_app
from vistas.core.graphics import texture

vistas_app # Make the fixture import look used to IDEs


def test_texture_with_data(vistas_app):
    def test_callback():
        data = numpy.arange(300)

        with patch('{}.glTexImage2D'.format(texture.__name__)) as m:
            t = texture.Texture(data, 10, 10)
            assert m.called
            assert m.call_args[0][-1] is data
            assert m.call_args[0][3:5] == (10, 10)

    vistas_app(test_callback)


def test_texture_with_image(vistas_app):
    def test_callback():
        im = Image.new('RGB', (10, 10), (0, 0, 0, 0))

        with patch('{}.glTexImage2D'.format(texture.__name__)) as m:
            t = texture.Texture(im)
            assert m.called
            assert (m.call_args[0][-1].ravel() == numpy.zeros(300)).all()
            assert m.call_args[0][3:5] == (10, 10)

    vistas_app(test_callback)
