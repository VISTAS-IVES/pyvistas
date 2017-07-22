import random
from io import BytesIO

import numpy
import wx
from PIL import Image
from matplotlib import pyplot

from vistas.core.color import RGBColor
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin2D, VisualizationUpdateEvent
from vistas.core.timeline import Timeline
from vistas.ui.app import App
from vistas.ui.utils import post_newoptions_available


class GraphVisualization(VisualizationPlugin2D):
    id = 'barchart_visualization_plugin'
    name = 'Barchart Visualization'
    description = 'Plots barcharts of values from a grid'
    author = 'Conservation Biology Institute'
    version = '1.0'

    def __init__(self):
        super().__init__()
        self.data = None

        self.attribute_option = Option(self, Option.CHOICE, 'Attribute', 0)
        self.labels_option = Option(self, Option.CHECKBOX, 'Show Labels', True)
        self.bg_color_option = Option(self, Option.COLOR, 'Background Color', RGBColor(0, 0, 0))
        self.label_color_option = Option(self, Option.COLOR, 'Label Color', RGBColor(1, 1, 1))
        self.num_categories = Option(self, Option.INT, 'Number of Categories', 2)
        self.categories_group = OptionGroup('Categories')

        self.global_options = OptionGroup('Options')
        self.global_options.items = [
            self.attribute_option, self.labels_option, self.bg_color_option, self.label_color_option
        ]

    def get_options(self):
        options = OptionGroup()
        options.items.append(self.global_options)
        options.items.append(Option(self, Option.SPACER))
        options.items.append(self.num_categories)

        num_categories = self.num_categories.value
        current_categories = int(len(self.categories_group.flat_list) / 3)

        # move random past current colors
        random.seed(100)
        for i in range(current_categories):
            RGBColor.random()

        if num_categories > current_categories:
            for i in range(num_categories - current_categories):
                self.categories_group.items.append(Option(self, Option.INT, 'Value', 0))
                self.categories_group.items.append(Option(self, Option.TEXT, 'Label', ''))
                self.categories_group.items.append(Option(self, Option.COLOR, 'Color', RGBColor.random()))
                self.categories_group.items.append(Option(self, Option.SPACER))
        elif num_categories < current_categories:
            current_options = self.categories_group.flat_list
            self.categories_group = OptionGroup('Categories')
            self.categories_group.items = current_options[:num_categories*4]

        random.seed()

        options.items.append(self.categories_group)
        return options

    def update_option(self, option=None):
        if option.plugin is not self:
            return

        if option.name == 'Number of Categories':
            post_newoptions_available(self)

        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))

    @property
    def can_visualize(self):
        return self.data is not None

    @property
    def visualization_name(self):
        return 'Barchart Visualization' if self.data is None else 'Barchart of {}'.format(self.data.data_name)

    @property
    def data_roles(self):
        return [
            (DataPlugin.RASTER, 'Data')
        ]

    def set_data(self, data: DataPlugin, role):
        self.data = data
        self.attribute_option.labels = self.data.variables if self.data else []
        self.attribute_option.value = 0
        post_newoptions_available(self)
        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))

    def get_data(self, role):
        return self.data

    def fig_to_pil(self, fig):
        f = BytesIO()
        fig.savefig(f, format='png', facecolor=fig.get_facecolor())

        f.seek(0)
        return Image.open(f, 'r')

    def render(self, width, height):
        if self.data is None:
            return

        grid = self.data.get_data(self.attribute_option.selected, Timeline.app().current)

        background_color = self.bg_color_option.value.rgb.rgb_list
        label_color = self.label_color_option.value.rgb.rgb_list
        show_labels = self.labels_option.value
        num_categories = self.num_categories.value
        categories = self.categories_group.flat_list

        unique_values = dict(zip(*numpy.unique(grid, return_counts=True)))  # dictionary of unique values to count
        values = list()
        colors = list()
        labels = list()

        for i in range(num_categories):
            try:
                value, label, color, _ = [opt.value for opt in categories[i*4:i*4+4]]
            except:
                continue    # Bail on this index, the viz is probably updating

            if label == '':
                label = value

            if value in unique_values:
                values.append(unique_values[value])
            else:
                values.append(0)

            colors.append(color.rgb.rgb_list)
            labels.append(label)

        indices = numpy.arange(len(values))
        values = tuple(values)
        labels = tuple(labels)

        fig = pyplot.figure(
            figsize=(width / 100, height / 100), dpi=100, tight_layout=True,
            facecolor=self.bg_color_option.value.rgb.rgb_list
        )

        try:
            ax = fig.add_subplot(1, 1, 1, facecolor=background_color)
            ax.margins(1 / width, 1 / height)

            bars = ax.bar(indices, values, label='Men', color='r')

            for b in indices:
                bars[b].set_color(colors[b])            # Set unique colors here

            # add some text for labels, title and axes ticks
            ax.set_xticks(indices)
            ax.set_xticklabels(tuple(labels))           # labels go here
            ax.get_xaxis().set_visible(show_labels)

            ax.tick_params(color=label_color)
            for spine in ('left', 'bottom'):
                ax.spines[spine].set_color(label_color)

            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_color(label_color)

            # attach a text label within each bar displaying the count
            for i, rect in enumerate(bars):
                count = rect.get_height()
                bar_label_color = (0, 0, 0) if sum([x * 255 for x in colors[i]]) > 384 else (1, 1, 1)
                ax.text(rect.get_x() + rect.get_width() / 2., 0.5 * count, '%d' % int(count), ha='center', va='bottom',
                        color=bar_label_color)

            return self.fig_to_pil(fig).resize((width, height))

        finally:
            pyplot.close(fig)

    def timeline_changed(self):
        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))
