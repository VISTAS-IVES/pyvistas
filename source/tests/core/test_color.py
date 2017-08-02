from numpy import isclose

from vistas.core.color import RGBColor, HSVColor, interpolate_color


def test_rgb_to_hsv():
    rgb_color = RGBColor(.2, .4, .8)
    hsv_color = rgb_color.as_hsv()

    assert isclose(hsv_color.hsv_list, (220, .75, .8)).all()


def test_hsv_to_rgb():
    hsv_color = HSVColor(220, .75, .8)
    rgb_color = hsv_color.as_rgb()

    assert isclose(rgb_color.rgb_list, (.2, .4, .8)).all()


def test_interpolate_color():
    min_color = RGBColor(1, 0, 0)
    max_color = RGBColor(0, 0, 1)
    value_range = (0, 100)

    assert isclose(interpolate_color(value_range, min_color, max_color, 0).hsv.hsv_list, (0, 1, 1)).all()
    assert isclose(interpolate_color(value_range, min_color, max_color, 100).hsv.hsv_list, (240, 1, 1)).all()
    assert isclose(interpolate_color(value_range, min_color, max_color, -1).hsv.hsv_list, (0, 1, 1)).all()
    assert isclose(interpolate_color(value_range, min_color, max_color, 101).hsv.hsv_list, (240, 1, 1)).all()
    assert isclose(interpolate_color(value_range, min_color, max_color, 50).hsv.hsv_list, (120, 1, 1)).all()
