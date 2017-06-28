import os

from vistas.core.utils import get_platform

MACOS_FONT_PATHS = [
    '/Library/Fonts/',
    '/System/Library/Fonts/',
    '~/Library/Fonts/'
]


def get_font_path(font):
    """ Returns the full path to a font file given the name """

    if get_platform() == 'windows':
        return font

    for path in (os.path.expanduser(x) for x in MACOS_FONT_PATHS):
        match = find_exact_font(font, path)
        if match is not None:
            return match

    return font


def find_exact_font(font, path):
    """ Returns the font in a given directory, or None if the font is not found """

    for name in os.listdir(path):
        if font.lower() == name.lower():
            return os.path.join(path, name)
