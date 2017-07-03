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

        self.data = None
        self.fig = None

        self.labels_option = Option(self, Option.CHECKBOX, 'Show Labels', True)
        self.x_units_option = Option(self, Option.CHECKBOX, 'X-Axis Units', True)
        self.y_units_option = Option(self, Option.CHECKBOX, 'Y-Axis Units', True)
        self.cursor_option = Option(self, Option.CHECKBOX, 'Show Timeline Cursor', True)

        self.bg_color_option = Option(self, Option.COLOR, 'Background Color', RGBColor(0, 0, 0))
        self.label_color_option = Option(self, Option.COLOR, 'Label Color', RGBColor(1, 1, 1))
        self.line_color_option = Option(self, Option.COLOR, 'Line Color', RGBColor(.2, .2, .9))

    def get_options(self):
        options = OptionGroup()
        options.items = [
            self.labels_option, self.x_units_option, self.y_units_option, self.cursor_option,
            Option(self, Option.SPACER), self.bg_color_option, self.label_color_option, self.line_color_option
        ]

        return options

    @property
    def can_visualize(self):
        return self.data is not None

    @property
    def visualization_name(self):
        return 'Graph Visualization' if self.data is None else 'Graph of {}'.format(self.data.data_name)

    @property
    def data_roles(self):
        return [
            (DataPlugin.ARRAY, 'Data')
        ]

    def set_data(self, data: DataPlugin, role):
        self.data = data

        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))

    def get_data(self, role):
        return self.data

    def fig_to_pil(self, fig):
        f = BytesIO()
        fig.savefig(f, format='png', facecolor=fig.get_facecolor())

        f.seek(0)
        return Image.open(f, 'r')

    def visualize(self, width, height, back_thread=True, handler=None):
        if self.fig:
            return

        self.fig = pyplot.figure(
            figsize=(width / 100, height / 100), dpi=100, tight_layout=True,
            facecolor=self.bg_color_option.value.rgb.rgb_list
        )

        return super().visualize(width, height, back_thread=back_thread, handler=handler)

    def render(self, width, height):
        if self.data is None:
            return

        show_labels = self.labels_option.value
        show_cursor = self.cursor_option.value
        background_color = self.bg_color_option.value.rgb.rgb_list
        label_color = self.label_color_option.value.rgb.rgb_list
        line_color = self.line_color_option.value.rgb.rgb_list

        ax = self.fig.add_subplot(1, 1, 1, facecolor=background_color)
        ax.margins(1 / width, 1 / height)

        data = (self.data.get_data(self.data.variables[0]),)
        if self.data.time_info.is_temporal:
            data = ([(x - datetime(1, 1, 1)).days for x in self.data.time_info.timestamps],) + data
            ax.xaxis.set_major_formatter(dates.DateFormatter('%b %d, %Y'))

        ax.plot(*data, color=line_color, label=self.data.variables[0], linewidth=1)

        for spine in ('right', 'top'):
            ax.spines[spine].set_visible(False)

        if show_labels:
            legend = ax.legend(loc='best', facecolor=background_color)
            legend.get_frame().set_alpha(.6)

            for text in legend.get_texts():
                text.set_color(label_color)

        if show_cursor and self.data.time_info.is_temporal:
            current_time = Timeline.app().current
            color = (1, 1, 1) if self.bg_color_option.value.hsv.v < .5 else (0, 0, 0)
            ax.axvline(x=(current_time - datetime(1, 1, 1)).days, color=color)

        ax.tick_params(axis='both', color=label_color)

        for spine in ('left', 'bottom'):
            ax.spines[spine].set_color(label_color)

        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_color(label_color)

        return self.fig_to_pil(self.fig).resize((width, height))

    def post_render(self):
        if self.fig:
            pyplot.close(self.fig)
            self.fig = None

    def timeline_changed(self):
        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))
