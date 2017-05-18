from vistas.ui.events import PluginOptionEvent
from vistas.ui.utils import get_main_window

import wx
import sys


class Option:

    NONE = 'none'
    SPACER = 'spacer'
    LABEL = 'label'
    TEXT = 'text'
    INT = 'int'
    FLOAT = 'float'
    COLOR = 'color'
    CHECKBOX = 'checkbox'
    RADIOS = 'radios'
    CHOICE = 'choice'
    SLIDER = 'slider'
    FILE = 'file'

    TYPES = (NONE, SPACER, LABEL, TEXT, INT, FLOAT, COLOR,
             CHECKBOX, RADIOS, CHOICE, SLIDER, FILE)

    def __init__(
        self, plugin=None, option_type=NONE, name=None, default_value=None, min_value=None, max_value=None, step=None
    ):
        if option_type not in self.TYPES:
            raise ValueError("{} is not a valid Option type".format(option_type))
        self.plugin = plugin
        self.option_type = option_type
        self.name = name
        self._value = default_value
        self.default = default_value
        self.min_value = sys.float_info[3] if min_value is None else min_value
        self.max_value = sys.float_info[0] if max_value is None else max_value
        self.step = step
        self.labels = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        if self.option_type in [self.INT, self.FLOAT, self.SLIDER]:
            if self._value < self.min_value:
                self._value = self.min_value
            elif self._value > self.max_value:
                self._value = self.max_value

    def option_updated(self):
        get_main_window().AddPendingEvent(PluginOptionEvent(plugin=self.plugin, option=self,
                                                            change=PluginOptionEvent.OPTION_CHANGED))


class OptionGroup:

    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'

    def __init__(self, name='', layout=VERTICAL):
        self.name = name
        self.layout = layout
        self.items = []

    @property
    def flat_list(self) -> [Option]:
        options = []
        for item in self.items:
            if type(item) is Option:
                options.append(item)
            else:
                child_options = item.flat_list
                for child in child_options:
                    options.append(child)
        return options
