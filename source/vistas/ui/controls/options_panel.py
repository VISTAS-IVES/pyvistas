from vistas.core.color import RGBColor
from vistas.core.plugins.option import Option, OptionGroup
from vistas.ui.events import PluginOptionEvent
from vistas.ui.controls.editable_slider import EditableSlider, EVT_SLIDER_CHANGE_EVENT
from vistas.ui.controls.file_chooser import FileChooserCtrl, EVT_FILE_VALUE_CHANGE

import wx


class OptionsPanel(wx.ScrolledWindow):
    def __init__(self, parent, id):
        super().__init__(parent, id)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetScrollRate(0, 1)
        self.plugin = None
        self._options = {}

    def AddOption(self, option: Option, parent_sizer):

        opt_type = option.option_type

        if opt_type == Option.SPACER:
            parent_sizer.AddSpacer(10)

        elif opt_type == Option.LABEL:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            parent_sizer.Add(label, 0, wx.BOTTOM, 5)

        elif opt_type == Option.TEXT:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            text = wx.TextCtrl(self, wx.ID_ANY, option.value)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            text.Bind(wx.EVT_TEXT, self.OnText)
            self._options[text] = option

            sizer.Add(label, 0, wx.RIGHT, 10)
            sizer.Add(text, 1)
            parent_sizer.Add(sizer, 0, wx.EXPAND | wx.BOTTOM, 5)

        elif opt_type in [Option.INT, Option.FLOAT]:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            text = wx.TextCtrl(self, wx.ID_ANY, str(option.value), style=wx.TE_RIGHT)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            text.Bind(wx.EVT_TEXT, self.OnText)
            self._options[text] = option

            text.SetSize(50, -1)
            sizer.Add(label, 0, wx.RIGHT, 10)
            sizer.Add(text, 1)
            parent_sizer.Add(sizer, 0, wx.BOTTOM, 5)

        elif opt_type == Option.COLOR:
            color = wx.ColourPickerCtrl(self, wx.ID_ANY, wx.Colour(*[x*255 for x in option.value.rgb.rgb_list]))
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            sizer = wx.BoxSizer(wx.HORIZONTAL)

            color.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnColor)
            self._options[color] = option

            sizer.Add(color, 0, wx.RIGHT, 10)
            sizer.Add(label)
            parent_sizer.Add(sizer, 0, wx.BOTTOM, 5)

        elif opt_type == Option.CHECKBOX:
            checkbox = wx.CheckBox(self, wx.ID_ANY, option.name)
            checkbox.SetValue(option.value)
            checkbox.Bind(wx.EVT_CHECKBOX, self.OnCheck)
            self._options[checkbox] = option
            parent_sizer.Add(checkbox, 0, wx.BOTTOM, 5)

        elif opt_type == Option.RADIOS:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            parent_sizer.Add(label)

            labels = option.labels
            for i in range(len(labels)):
                if i < 1:
                    radio = wx.RadioButton(self, wx.ID_ANY, labels[i], wx.DefaultPosition, wx.DefaultSize, wx.RB_GROUP,
                                           wx.DefaultValidator, str(i))
                else:
                    radio = wx.RadioButton(self, wx.ID_ANY, labels[i], wx.DefaultPosition, wx.DefaultSize, 0,
                                           wx.DefaultValidator, str(i))

                radio.SetValue(option.value == i)   # Todo: is this correct?

                self._options[radio] = option
                radio.Bind(wx.EVT_RADIOBUTTON, self.OnRadio)
                parent_sizer.Add(radio)

        elif opt_type == Option.CHOICE:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            choice = wx.Choice(self)
            sizer = wx.BoxSizer(wx.HORIZONTAL)

            for label_text in option.labels:
                choice.Append(label_text)

            if option.value is not None:
                choice.Select(option.value)
            else:
                choice.Select(0)

            choice.Bind(wx.EVT_CHOICE, self.OnChoice)
            self._options[choice] = option

            sizer.Add(label, 0, wx.RIGHT, 10)
            sizer.Add(choice, 1)
            parent_sizer.Add(sizer, 0, wx.EXPAND | wx.BOTTOM, 5)

        elif opt_type == Option.SLIDER:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            slider = EditableSlider(self, wx.ID_ANY, min_value=option.min_value, max_value=option.max_value,
                                    value=option.value)
            slider.Bind(EVT_SLIDER_CHANGE_EVENT, self.OnSlider)
            self._options[slider] = option

            parent_sizer.Add(label)
            parent_sizer.Add(slider, 0, wx.EXPAND | wx.BOTTOM, 5)

        elif opt_type == Option.FILE:
            label = wx.StaticText(self, wx.ID_ANY, option.name)
            file_chooser = FileChooserCtrl(self, wx.ID_ANY)
            if option.value is not None and len(option.value):
                file_chooser.file = option.value
            file_chooser.Bind(EVT_FILE_VALUE_CHANGE, self.OnFile)
            self._options[file_chooser] = option

            parent_sizer.Add(label)
            parent_sizer.Add(file_chooser, 0, wx.EXPAND | wx.BOTTOM, 5)

        parent_sizer.Layout()

    def AddOptionGroup(self, options, sizer: wx.BoxSizer):
        for item in options.items:
            if type(item) is Option:
                self.AddOption(item, sizer)
            else:
                orientation = wx.VERTICAL if item.layout == OptionGroup.VERTICAL else wx.HORIZONTAL
                if len(item.name):
                    static_box = wx.StaticBox(self, wx.ID_ANY, item.name)
                    child_sizer = wx.StaticBoxSizer(static_box, orientation)
                else:
                    child_sizer = wx.BoxSizer(orientation)
                self.AddOptionGroup(item, child_sizer)
                sizer.Add(child_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value: OptionGroup=None):
        self.sizer.Clear()
        if value is None or len(value.items) < 1:
            self.AddOption(Option(name="No Options"), self.sizer)
            self.plugin = None
        else:
            self.AddOptionGroup(value, self.sizer)

    def OnText(self, event):
        text = event.GetEventObject()
        if text in self._options:
            option = self._options[text]
            value = text.GetValue()
            try:
                if option.option_type == Option.INT:
                    value = int(value)
                if option.option_type == Option.FLOAT:
                    value = float(value)
            except ValueError:
                value = 0
            option.value = value
            option.option_updated()

    def OnColor(self, event):
        color = event.GetEventObject()
        if color in self._options:
            option = self._options[color]
            c = color.GetColour()
            option.value = RGBColor(*[x/255 for x in [c.red, c.green, c.blue]])
            option.option_updated()

    def OnCheck(self, event):
        checkbox = event.GetEventObject()
        if checkbox in self._options:
            option = self._options[checkbox]
            option.value = checkbox.GetValue()
            option.option_updated()

    def OnRadio(self, event):
        radio = event.GetEventObject()
        if radio in self._options:
            option = self._options[radio]
            option.value = radio.GetValue()
            option.option_updated()

    def OnChoice(self, event):
        choice = event.GetEventObject()
        if choice in self._options:
            option = self._options[choice]
            option.value = choice.GetSelection()
            option.option_updated()

    def OnSlider(self, event):
        slider = event.GetEventObject()
        if slider in self._options:
            option = self._options[slider]
            option.value = slider.value
            option.option_updated()

    def OnFile(self, event):
        file_chooser = event.GetEventObject()
        if file_chooser in self._options:
            option = self._options[file_chooser]
            option.value = event.path
            option.option_updated()

    def NewOptionAvailable(self, event: PluginOptionEvent):
        plugin = event.plugin
        if event.change is PluginOptionEvent.NEW_OPTIONS_AVAILABLE and plugin is not None and plugin == self.plugin:
            self.options = plugin.get_options()
            self.Layout()
