from io import BytesIO

import wx
from PIL import Image
from datetime import datetime
from matplotlib import pyplot, dates

from vistas.core.color import RGBColor
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin2D, VisualizationUpdateEvent
from vistas.core.timeline import Timeline
from vistas.ui.app import App


class GraphVisualization(VisualizationPlugin2D):
    id = 'graph_visualization_plugin'
    name = 'Graph Visualization'
    description = 'Plots data on a 2D graph'
    author = 'Conservation Biology Institute'

    def __init__(self):
        super().__init__()

        self.data = []
        self.option_groups = []

        self.global_options = OptionGroup()
        self.labels_option = Option(self, Option.CHECKBOX, 'Show Labels', True)
        self.x_units_option = Option(self, Option.CHECKBOX, 'X-Axis Units', True)
        self.y_units_option = Option(self, Option.CHECKBOX, 'Y-Axis Units', True)
        self.cursor_option = Option(self, Option.CHECKBOX, 'Show Timeline Cursor', True)

        self.bg_color_option = Option(self, Option.COLOR, 'Background Color', RGBColor(0, 0, 0))
        self.label_color_option = Option(self, Option.COLOR, 'Label Color', RGBColor(1, 1, 1))

        self.global_options.items = [
            self.labels_option, self.x_units_option, self.y_units_option, self.cursor_option,
            Option(self, Option.SPACER), self.bg_color_option, self.label_color_option
        ]

    def get_group_option(self, plugin, option_name):

        for group in self.option_groups:
            if group.name == plugin.data_name:
                for option in group.flat_list:
                    if option.name == option_name:
                        return option

        return None

    def get_options(self):
        options = OptionGroup()
        options.items.append(self.global_options)

        for group in self.option_groups:
            options.items.append(group)

        return options

    def _update_options(self):

        if len(self.data) < len(self.option_groups):

            # We removed a data plugin, figure out which one
            while len(self.data) < len(self.option_groups):

                group = None
                for g in self.option_groups:
                    found = False
                    for p in self.data:
                        if p.data_name == g.name:
                            found = True
                            break
                    if not found:
                        group = g
                        break

                self.option_groups.remove(group)

        elif len(self.data) > len(self.option_groups):

            # We added data, figure out which one
            while len(self.data) > len(self.option_groups):

                plugin = None

                for p in self.data:
                    found = False
                    for group in self.option_groups:
                        if group.name == p.data_name:
                            found = True
                            break

                    if not found:
                        plugin = p
                        break

                label = plugin.data_name
                group = OptionGroup(label)
                attr_option = Option(self, Option.CHOICE, 'Variable', 0)
                attr_option.labels = plugin.variables
                color_option = Option(self, Option.COLOR, 'Color', RGBColor(0, 0, 1))
                group.items = [attr_option, color_option]
                self.option_groups.append(group)

    @property
    def can_visualize(self):
        return len(self.data) > 0

    @property
    def visualization_name(self):
        return 'Graph Visualization' if len(self.data) == 0 else 'Graph of {}'.format(self.data[0].data_name)

    @property
    def data_roles(self):
        return [
            (DataPlugin.ARRAY, 'Data')
        ]

    def role_supports_multiple_inputs(self, role):
        if role == 0:
            return True
        return False

    def role_size(self, role):
        return len(self.data)

    def set_data(self, data: DataPlugin, role):

        if data is None:
            self.data = []
        else:
            self.data.append(data)

        self._update_options()

        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))

    def remove_subdata(self, role, subrole):

        if subrole < len(self.data):
            self.data.pop(subrole)

        self._update_options()

        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))

    def get_data(self, role):
        return self.data[0] if len(self.data) > 0 else None

    def get_multiple_data(self, role):
        return self.data

    def fig_to_pil(self, fig):
        f = BytesIO()
        fig.savefig(f, format='png', facecolor=fig.get_facecolor())

        f.seek(0)
        return Image.open(f, 'r')

    def render(self, width, height):
        if self.data is None:
            return

        show_labels = self.labels_option.value
        show_cursor = self.cursor_option.value
        background_color = self.bg_color_option.value.rgb.rgb_list
        label_color = self.label_color_option.value.rgb.rgb_list

        fig = pyplot.figure(
            figsize=(width / 100, height / 100), dpi=100, tight_layout=True,
            facecolor=self.bg_color_option.value.rgb.rgb_list
        )

        try:
            ax = fig.add_subplot(1, 1, 1, facecolor=background_color)
            ax.margins(1 / width, 1 / height)

            for data_plugin in self.data:

                data_color = self.get_group_option(data_plugin, 'Color').value.rgb.rgb_list
                data_variable = data_plugin.variables[self.get_group_option(data_plugin, 'Variable').value]

                data = (data_plugin.get_data(data_variable),)
                if data_plugin.time_info.is_temporal:
                    data = ([(x - datetime(1, 1, 1)).days for x in data_plugin.time_info.timestamps],) + data
                    ax.xaxis.set_major_formatter(dates.DateFormatter('%b %d, %Y'))

                ax.plot(*data, color=data_color, label=data_variable, linewidth=1)

            for spine in ('right', 'top'):
                ax.spines[spine].set_visible(False)

            if show_labels:
                legend = ax.legend(loc='best', facecolor=background_color)
                legend.get_frame().set_alpha(.6)

                for text in legend.get_texts():
                    text.set_color(label_color)

            if show_cursor and any([x.time_info.is_temporal for x in self.data]):
                current_time = Timeline.app().current
                color = (1, 1, 1) if self.bg_color_option.value.hsv.v < .5 else (0, 0, 0)
                ax.axvline(x=(current_time - datetime(1, 1, 1)).days, color=color)

            ax.tick_params(axis='both', color=label_color)

            for spine in ('left', 'bottom'):
                ax.spines[spine].set_color(label_color)

            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_color(label_color)

            return self.fig_to_pil(fig).resize((width, height))
        finally:
            pyplot.close(fig)

    def timeline_changed(self):
        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))
