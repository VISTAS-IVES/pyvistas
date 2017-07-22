import random


class Color:
    @property
    def rgb(self):
        if isinstance(self, RGBColor):
            return self
        else:
            return self.as_rgb()

    @property
    def hsv(self):
        if isinstance(self, HSVColor):
            return self
        else:
            return self.as_hsv()

    @classmethod
    def random(cls):
        return cls(random.random(), random.random(), random.random())


class RGBColor(Color):
    def __init__(self, r, g, b, a=1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def as_hsv(self):
        max_rgb = max(self.r, self.g, self.b)
        min_rgb = min(self.r, self.g, self.b)

        # Hue
        if max_rgb == min_rgb:
            h = 0
        elif max_rgb == self.r:
            h = round(60 * ((self.g - self.b) / (max_rgb - min_rgb)) + 360) % 360
        elif max_rgb == self.g:
            h = round(60 * ((self.b - self.r) / (max_rgb - min_rgb))) + 120
        else:
            h = round(60 * ((self.r - self.g) / (max_rgb - min_rgb))) + 240

        # Saturation
        if max_rgb == 0:
            s = 0
        else:
            s = (max_rgb - min_rgb) / max_rgb

        # Value
        v = max_rgb

        return HSVColor(int(h), s, v, self.a)

    @property
    def rgb_list(self):
        return self.r, self.g, self.b

    @property
    def rgba_list(self):
        return self.rgb_list + (self.a,)


class HSVColor(Color):
    def __init__(self, h, s, v, a=1):
        self.h = h
        self.s = s
        self.v = v
        self.a = a

    def as_rgb(self):
        hi = int(self.h / 60) % 6
        f = self.h / 60 - int(self.h / 60)
        p = self.v * (1 - self.s)
        q = self.v * (1 - f * self.s)
        t = self.v * (1 - (1 - f) * self.s)

        if hi == 0:
            r = self.v
            g = t
            b = p
        elif hi == 1:
            r = q
            g = self.v
            b = p
        elif hi == 2:
            r = p
            g = self.v
            b = t
        elif hi == 3:
            r = p
            g = q
            b = self.v
        elif hi == 4:
            r = t
            g = p
            b = self.v
        elif hi == 5:
            r = self.v
            g = p
            b = q
        else:
            r = 0
            g = 0
            b = 0

        return RGBColor(r, g, b, self.a)

    @property
    def hsv_list(self):
        return self.h, self.s, self.v

    @property
    def hsva_list(self):
        return self.hsv_list + (self.a,)


def interpolate_color(range, min_color: Color, max_color: Color, t):
    """ Linearly interpolate in the HSV color space """

    if t < range[0]:
        return min_color
    elif t >= range[1]:
        return max_color

    min_hsv = min_color.hsv
    max_hsv = max_color.hsv

    pct = (t - range[0]) / (range[1] - range[0])
    h = round(abs(min_hsv.h + (max_hsv.h - min_hsv.h) * pct))
    s = abs(min_hsv.s + (max_hsv.s - min_hsv.s) * pct)
    v = abs(min_hsv.v + (max_hsv.v - min_hsv.v) * pct)
    a = round(abs(min_color.a + (max_color.a - min_color.a) * pct))

    return HSVColor(h, s, v, a)
