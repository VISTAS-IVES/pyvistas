import os
from PIL import Image

from vistas.core.graphics.overlay import BasicOverlayButton
from vistas.core.paths import get_resources_directory


class ExpandButton(BasicOverlayButton):
    """ Expand/collapse button for the right panel """

    def __init__(self):
        self._expanded = False
        self.image = Image.open(os.path.join(get_resources_directory(), 'images', 'expand_button.png'))

        super().__init__(self.image.transpose(Image.FLIP_LEFT_RIGHT), (0, 20))

    @property
    def expanded(self):
        return self._expanded

    @expanded.setter
    def expanded(self, expanded):
        self._expanded = expanded
        self.default_image = self.image if not expanded else self.image.transpose(Image.FLIP_LEFT_RIGHT)
