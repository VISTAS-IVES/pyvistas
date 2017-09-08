from vistas.core.graphics.geometry import Geometry



class BoxLineGeometry(Geometry):

    def __init__(self):
        super().__init__(5, 5, has_color_array=True, mode=Geometry.LINE_STRIP)