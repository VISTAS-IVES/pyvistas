from io import BytesIO

import wx
import numpy
from PIL import Image
from matplotlib import pyplot

from vistas.core.color import RGBColor
from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.option import Option, OptionGroup
from vistas.core.plugins.visualization import VisualizationPlugin2D, VisualizationUpdateEvent
from vistas.core.timeline import Timeline
from vistas.ui.app import App


class GraphVisualization(VisualizationPlugin2D):
    id = 'barchart_visualization_plugin'
    name = 'Barchart Visualization'
    description = 'Plots barcharts of values from a grid'
    author = 'Conservation Biology Institute'

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

        if num_categories > current_categories:
            for i in range(num_categories - current_categories):
                self.categories_group.items.append(Option(self, Option.INT, 'Value', 0))
                self.categories_group.items.append(Option(self, Option.COLOR, 'Color', RGBColor.random()))
                self.categories_group.items.append(Option(self, Option.TEXT, 'Label', ''))
                self.categories_group.items.append(Option(self, Option.SPACER))
        elif num_categories < current_categories:
            current_options = self.categories_group.flat_list
            self.categories_group = OptionGroup('Categories')
            self.categories_group.items = current_options[:num_categories*4]

        options.items.append(self.categories_group)
        return options

    def update_option(self, option=None):
        if option.plugin is not self:
            return

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
        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))

    def get_data(self, role):
        return self.data

    def fig_to_pil(self, fig):
        f = BytesIO()
        fig.savefig(f, format='png', facecolor=fig.get_facecolor())

        f.seek(0)
        return Image.open(f, 'r')

    def render(self, width, height):
        #if self.data is None:
        #    return

        background_color = self.bg_color_option.value.rgb.rgb_list
        label_color = self.label_color_option.value.rgb.rgb_list
        show_labels = self.labels_option.value

        N = 5
        men_means = (20, 35, 30, 35, 27)
        men_std = (2, 3, 4, 1, 2)

        ind = numpy.arange(N)  # the x locations for the groups
        w = 0.35  # the width of the bars

        fig = pyplot.figure(
            figsize=(width / 100, height / 100), dpi=100, tight_layout=True,
            facecolor=self.bg_color_option.value.rgb.rgb_list
        )

        try:
            ax = fig.add_subplot(1, 1, 1, facecolor=background_color)
            ax.margins(1 / width, w / height)

            bars = ax.bar(ind, men_means, w, label='Men', color='r', yerr=men_std)

            for b in ind:
                bars[b].set_color(RGBColor.random().rgb_list)     # Set unique colors here

            # add some text for labels, title and axes ticks
            ax.set_xticks(ind + w / 2)
            ax.set_xticklabels(('G1', 'G2', 'G3', 'G4', 'G5'))      # labels go here

            if show_labels:
                legend = ax.legend(loc='best', facecolor=background_color)
                legend.get_frame().set_alpha(.6)
                for text in legend.get_texts():
                    text.set_color(label_color)

            ax.tick_params(color=label_color)
            for spine in ('left', 'bottom'):
                ax.spines[spine].set_color(label_color)

            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_color(label_color)


            def autolabel(rects):
                """
                Attach a text label above each bar displaying its height
                """
                for rect in rects:
                    height = rect.get_height()
                    ax.text(rect.get_x() + rect.get_width() / 2., 1.05 * height,
                            '%d' % int(height),
                            ha='center', va='bottom')

            #autolabel(rects1)
            #autolabel(rects2)

            return self.fig_to_pil(fig).resize((width, height))

        finally:
            pyplot.close(fig)

    def timeline_changed(self):
        wx.PostEvent(App.get().app_controller.main_window, VisualizationUpdateEvent(plugin=self))
