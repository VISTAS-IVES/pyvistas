import sys
import wx.lib.newevent

PluginOptionChangedEvent, EVT_PLUGIN_OPTION_CHANGED = wx.lib.newevent.NewEvent()


class Option:

    NONE = 'none'
    SPACER = 'spacer'
    LABEL = 'label'
    TEXT = 'text'
    INT = 'int'
    FLOAT = 'float'
    COLOR = 'color'
    CHECKBOX = 'checkbox'
    RADIO = 'radio'
    CHOICE = 'choice'
    SLIDER = 'slider'
    FILE = 'file'

    TYPES = (NONE, SPACER, LABEL, TEXT, INT, FLOAT, COLOR,
             CHECKBOX, RADIO, CHOICE, SLIDER, FILE)

    def __init__(
        self, plugin=None, option_type=None, name=None, default_value=None, min_value=None, max_value=None, step=None
    ):
        if option_type not in self.TYPES:
            raise ValueError("{} is not a valid Option type".format(option_type))
        self.plugin = plugin
        self.option_type = option_type
        self.name = name
        self._value = default_value
        self.default = default_value
        self.min_value = sys.float_info.min if min_value is None else min_value
        self.max_value = sys.float_info.max if max_value is None else max_value
        self.step = step
        self._labels = []

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
        wx.PostEvent(self, PluginOptionChangedEvent(self, plugin=self.plugin, option=self))


class OptionGroup:

    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'

    def __init__(self, layout=VERTICAL, name=''):
        self.layout = layout
        self.name = name
        self.items = []     # list of OptionGroupItems

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
