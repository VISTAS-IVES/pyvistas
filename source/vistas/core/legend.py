from PIL import Image, ImageDraw, ImageFont

from vistas.core.color import Color, interpolate_color
from vistas.core.fonts import get_font_path


class Legend:
    """ Base legend class. Provides functions for rendering legends as PIL.Image objects. """

    MIDPOINT_PADDING = 3

    @staticmethod
    def _compute_font(labels, width):

        fontsize = 1
        font = ImageFont.truetype(get_font_path("arial.ttf"), fontsize)
        max_label = max(labels, key=len)
        while font.getsize(max_label)[0] < width:
            fontsize += 1
            font = ImageFont.truetype(get_font_path("arial.ttf"), fontsize)

        y_offset = font.getsize(max_label)[1]

        return font, y_offset

    @staticmethod
    def stretched(width, height, low_value, high_value, low_color: Color, high_color: Color):

        pad = Legend.MIDPOINT_PADDING
        top = str(high_value)
        bottom = str(low_value)

        # Determine sig figs
        sig_figs = min(len(top.split('.')[-1]), len(bottom.split('.')[-1]))
        mid = str(round(low_value + (high_value - low_value) / 2.0, sig_figs))

        result = Image.new("RGBA", (width, height))
        midpoint = width / 4

        draw = ImageDraw.Draw(result)

        for y in range(height):
            color = tuple(
                [int(255 * x) for x in interpolate_color((0, height), low_color, high_color, height - y).rgb.rgba_list]
            )
            draw.line((0, y, midpoint, y), fill=color)

        font, text_offset = Legend._compute_font([top, mid, bottom], midpoint * 2)

        draw.text((pad + midpoint, 0), top, font=font)
        draw.text((pad + midpoint, height / 2 - text_offset), mid, font=font)
        draw.text((pad + midpoint, height - text_offset * 2), bottom, font=font)

        return result

    @staticmethod
    def categorical(width, height, categories):

        result = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(result)
        midpoint = width // 4

        if categories:
            line_height = height // len(categories)
            y_offset = 0
            font, text_offset = Legend._compute_font([x[1] for x in categories], midpoint * 2)

            for color, label in categories:
                c = tuple([int(255 * x) for x in color.rgb.rgba_list])
                draw.rectangle([0, y_offset, midpoint, y_offset + line_height], fill=c)
                draw.text((midpoint, y_offset + text_offset), label, font=font)
                y_offset += line_height

        return result

    def get_color(self, value):
        """ Returns the color associated with the given legend. Implemented by subclasses """

        raise NotImplementedError


class StretchedLegend(Legend):

    def __init__(self, low_value, high_value, low_color, high_color):
        self.low_value = low_value
        self.high_value = high_value
        self.low_color = low_color
        self.high_color = high_color

    def render(self, width, height):
        return self.stretched(width, height, self.low_value, self.high_value, self.low_color, self.high_color)

    def get_color(self, value):
        """ Returns the color between low and high """

        return interpolate_color((self.low_value, self.high_value), self.low_color, self.high_color, value)


class CategoricalLegend(Legend):

    def __init__(self, categories):
        self.categories = categories

    def render(self, width, height):
        return self.categorical(width, height, self.categories)

    def get_color(self, value):     # value should be a label/string in this case

        for color, label in self.categories:
            if label == value:
                return color

        return None
