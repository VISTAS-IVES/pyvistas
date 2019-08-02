import wx
import vistas.ui.windows.zoom as zoom_file

import numpy as np
import numpy.ma as ma
import sklearn as sk
import sklearn.decomposition as skd

import matplotlib as mpl

mpl.use('WXAgg')
import matplotlib.backends.backend_wxagg as wxagg

from vistas.ui.project import Project
from vistas.core.timeline import Timeline
from vistas.ui.utils import get_main_window
from vistas.ui.events import EVT_TIMELINE_CHANGED


class PcaDialog(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title='PCA', size=(800, 800))

        self.zoom = zoom_file.Zoom()

        # Global variables
        self.reset_bounds = True  # True if bounds have been reset by changing variables
        self.update_graph = True  # True if graph needs to be updated
        self.update_table = True  # True if data tables need to be updated

        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddSpacer(5)
        self.panel.SetSizer(self.sizer)
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(top_sizer, 0)
        ctl_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(ctl_sizer, 0)

        zoom_sizer = wx.BoxSizer(wx.HORIZONTAL)  # Sizer for the zoom controls
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)  # Sizer for the right half of the window

        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Variables:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=20)

        self.data = Project.get().all_data
        data_choices = [n.data.data_name for n in self.data]

        self.chooser = wx.ListBox(self.panel, choices=data_choices, style=wx.LB_EXTENDED)
        ctl_sizer.Add(self.chooser, 0, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=20)

        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Plot type:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=12)
        self.plot_type = wx.RadioBox(self.panel, choices=['Scatterplot', 'Heatmap'])
        ctl_sizer.Add(self.plot_type, flag=wx.LEFT | wx.RIGHT, border=10)

        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Axis type:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=12)
        self.axis_type = wx.RadioBox(self.panel, choices=['Fixed', 'Adaptive', 'Zoom'])
        ctl_sizer.Add(self.axis_type, flag=wx.LEFT | wx.RIGHT, border=10)
        self.Bind(wx.EVT_RADIOBOX, self.on_axis_change)

        # Blank spacer
        #ctl_sizer.AddSpacer(320)

        # Zoom controls

        # Zoom button for dragging a box
        self.zoom_box = wx.Button(self.panel, label="Box")
        zoom_sizer.Add(self.zoom_box)

        self.zoom_box.Bind(wx.EVT_BUTTON, self.on_zoom_box_button)

        # Zoom slider
        self.zoom_slider = wx.Slider(self.panel, value=0, minValue=0, maxValue=49, size=(600, -1),
                                     style=wx.SL_HORIZONTAL)
        zoom_sizer.Add(self.zoom_slider, flag=wx.LEFT, border=10)

        self.zoom_slider.Bind(wx.EVT_SCROLL, self.on_zoom_scroll)

        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)

        self.right_sizer.Add(self.canvas, 1, wx.EXPAND)
        self.right_sizer.Add(zoom_sizer, flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
        top_sizer.Add(self.right_sizer)

        self.sizer.AddStretchSpacer()

        self.Bind(wx.EVT_LISTBOX, self.on_var_change)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.on_timeline_change)

        # Mouse events on graph (Matplotlib events)
        self.fig.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    def on_axis_change(self, event):
        """Update graph when user selects a new axis type"""
        self.update_graph = True
        self.zoom.zoom_box_drawing_disabled()
        self.do_plot(event)

    def on_timeline_change(self, event):
        """Update graph and tables when the timeline changes"""
        self.update_graph = True
        self.update_table = True
        self.do_plot(event)

    def on_var_change(self, event):
        """Reset the graph and tables when a new variable is chosen to plot"""
        self.reset_bounds = True
        self.update_graph = True
        self.update_table = True
        self.zoom.zoom_box_drawing_disabled()
        self.do_plot(event)

    def reset_graph(self, x_min, x_max, y_min, y_max):
        """Reset the zoom controls and graph bounds"""
        self.zoom_slider.SetValue(0)

        # Set bounds to fully zoomed out
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)

        if self.zoom.square in self.ax.get_children():
            self.zoom.square.remove()

        self.reset_bounds = False

        self.zoom.reset_zoom(x_min, x_max, y_min, y_max)

    def on_zoom_scroll(self, event):
        self.disable_zoom()
        self.zoom.zoom_box_drawing_disabled()
        self.do_plot(event)

    def disable_zoom(self):
        """Disable the button that allows user to draw a zoom box"""
        if self.zoom_slider.GetValue() > self.zoom.zoom_disable_value:
            self.zoom_box.Disable()
        else:
            self.zoom_box.Enable()

    def disable_zoom_check(self):
        """Enable zoom controls if axis type is set to Zoom"""
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type == 'Zoom':
            self.zoom_slider.Enable()
            self.disable_zoom()
        else:
            self.zoom_slider.Disable()
            self.zoom_box.Disable()

    def on_zoom_box_button(self, event):
        """Allow the user to draw a box on the graph"""
        self.zoom.zoom_box_drawing_enabled()

    # MOUSE METHODS MATPLOTLIB

    def on_mouse_move(self, event):
        """Get mouse position when moving"""
        ms = wx.GetMouseState()
        if ms.leftIsDown:
            self.zoom.set_mouse_diff(event.xdata, event.ydata)
            self.do_plot(event)
        else:
            self.zoom.set_mouse_diff_zero()

    def on_mouse_press(self, event):
        """Get mouse position when left clicking"""
        ms = wx.GetMouseState()
        if ms.leftIsDown:
            self.zoom.set_mouse_diff_zero()
            self.zoom.set_mouse_initial(event.xdata, event.ydata)

    def on_mouse_release(self, event):
        """Get mouse position when releasing a mouse press"""
        self.zoom.mouse_release(event.xdata, event.ydata)
        self.do_plot(event)

    # PLOTTING GRAPH

    def plot_zoom_graph(self, x_min, x_max, y_min, y_max):
        """Calculate the bounds of the graph when 'Zoom' axis type is selected"""

        # If variables have been changed, graph should be reset
        if self.reset_bounds:
            self.reset_graph(x_min, x_max, y_min, y_max)

        zoom_values = self.zoom.calculate_zoom(x_min, x_max, y_min, y_max, self.zoom_slider.GetValue())

        # Set zoom slider to given value
        self.zoom_slider.SetValue(zoom_values[5])
        self.disable_zoom()

        # Set bounds
        self.ax.set_xlim(zoom_values[0], zoom_values[1])
        self.ax.set_ylim(zoom_values[2], zoom_values[3])

        # If box should be drawn
        if zoom_values[4]:
            self.ax.add_patch(self.zoom.square)

    def get_data(self, dname, data):
        try:
            node = data[[n.data.data_name for n in data].index(dname)]
        except ValueError:
            return None
        date = Timeline.app().current
        thisdata = node.data.get_data(node.data.variables[0], date=date)
        return thisdata

    def plot_adjust(self, x1, x2, y1, y2):
        """Adjust the bounds of the current graph without redrawing it"""
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())

        if self.zoom.square in self.ax.get_children():
            self.zoom.square.remove()

        if axis_type == 'Zoom':
            self.plot_zoom_graph(x1, x2, y1, y2)

        self.ax.figure.canvas.draw()

    def plot_pca(self, data=None):
        # normalize and reorganize data
        n_vars = len(data)
        var_names = list(data)
        x_data = data.values()  # guaranteed, per python docs, to be same order
        x_data = [(d - np.mean(d)) / np.std(d) for d in x_data]
        # synchronize masks
        n_data = ma.array(x_data)
        if isinstance(n_data, ma.masked_array):
            mask = ma.sum(n_data.mask, axis=0)
            mask = np.where(mask, True, False)
            for d in x_data:
                d.mask = mask

        x_data = np.concatenate([np.expand_dims(d.compressed(), axis=0) for d in x_data])
        x_data = x_data.transpose()

        # calculate pca
        pca = skd.PCA()
        model = pca.fit(x_data)
        tx_data = pca.transform(x_data)

        self.create_graph(n_vars, pca, tx_data, var_names, x_data)

        if self.update_table:
            self.create_table(n_vars, pca, var_names)

    def create_graph(self, n_vars, pca, tx_data, var_names, x_data):
        try:
            self.fig.delaxes(self.ax)
        except AttributeError:
            pass

        # plot first two components
        self.ax = self.fig.add_subplot(111)
        self.ax.grid()
        self.ax.set_xlabel('Component 1')
        self.ax.set_ylabel('Component 2')

        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type == 'Fixed':
            self.ax.set_xlim(-3, 3)
            self.ax.set_ylim(-3, 3)
        elif axis_type == 'Zoom':
            self.plot_zoom_graph(-3, 3, -3, 3)

        self.zoom.set_bounds_absolute(-3, 3, -3, 3)

        plot_type = self.plot_type.GetString(self.plot_type.GetSelection())
        if plot_type == 'Scatterplot':
            # adjust marker size and alpha based on # of points
            marker_size = mpl.rcParams['lines.markersize'] ** 2
            marker_size *= min(1, max(.12, 200 / len(tx_data[:, 0])))
            alpha = min(1, max(.002, 500 / len(tx_data[:, 0])))
            self.ax.scatter(tx_data[:, 0], tx_data[:, 1], s=marker_size, c='b', alpha=alpha)
        else:  # heatmap
            bins = 200
            heatmap, x_edges, y_edges = np.histogram2d(tx_data[:, 0], tx_data[:, 1], bins=bins)
            x_min, x_max = x_edges[0], x_edges[-1]
            y_min, y_max = y_edges[0], y_edges[-1]
            self.ax.imshow(np.log(heatmap.transpose() + 1), extent=[x_min, x_max, y_min, y_max], cmap='Blues',
                           origin='lower', aspect='auto')

        # plot axes
        color = ['g', 'r', 'm', 'k', 'y']
        for n in range(n_vars):
            adata = np.zeros([2, n_vars])
            adata[0, n] = ma.min(x_data[:, n])
            adata[1, n] = ma.max(x_data[:, n])
            xf = pca.transform(adata)
            self.ax.plot([xf[0, 0], xf[0, 1]], [xf[1, 0], xf[1, 1]], color[n % len(color)] + '-')
            self.ax.text(xf[0, 0], xf[1, 0], var_names[n], color=color[n % len(color)])
        self.fig.tight_layout()

        self.panel.Layout()

    def create_table(self, n_vars, pca, var_names):
        self.panel.Freeze()

        # show stats in grid
        try:
            self.grid.Destroy()
        except AttributeError:
            pass

        self.grid = wx.grid.Grid(self.panel, -1)
        self.grid.CreateGrid(n_vars, n_vars + 1)  # extra column for explained variance
        grid_labels = ['Expl. var.'] + var_names
        grid_data = np.concatenate(
            (np.expand_dims(pca.explained_variance_ratio_, axis=1), pca.components_),
            axis=1)
        for v in range(len(grid_labels)):
            self.grid.SetColLabelValue(v, grid_labels[v])
            self.grid.SetColFormatFloat(v, 6, 3)
        vc = wx.ColourDatabase().Find('Light Blue')
        for row in range(n_vars):
            self.grid.SetCellBackgroundColour(row, 0, vc)
            for col in range(len(grid_labels)):
                self.grid.SetCellValue(row, col, str(grid_data[row, col]))
                self.grid.SetReadOnly(row, col)
        self.grid.AutoSize()

        grid_width = self.grid.GetRowLabelSize()
        grid_height = self.grid.GetColLabelSize()

        for i in range(self.grid.GetNumberCols()):
            grid_width += self.grid.GetColSize(i)

        for j in range(self.grid.GetNumberRows()):
            grid_height += self.grid.GetRowSize(j)

        if n_vars > 3:
            self.grid.SetMinSize((grid_width, grid_height+17))
        else:
            self.grid.SetMinSize((grid_width, grid_height))

        self.sizer.Add(self.grid, flag=wx.BOTTOM | wx.LEFT, border=10)
        self.panel.Layout()

        self.panel.Thaw()

        self.update_table = False

    def do_plot(self, event):
        self.disable_zoom_check()

        try:
            if self.zoom.square in self.ax.get_children():
                self.zoom.square.remove()
        except AttributeError:
            pass

        if self.update_graph:
            try:  # because we want to insure that we can pass to next handler
                selections = self.chooser.GetSelections()
                if len(selections) >= 2:
                    v_data = {}
                    for sel in selections:
                        dname = self.chooser.GetString(sel)
                        try:
                            thisdata = self.get_data(dname, self.data)
                            if thisdata is not None:
                                v_data[dname] = thisdata
                        except Exception as ex:
                            print(ex)
                    if len(v_data.keys()) >= 2:
                        self.plot_pca(data=v_data)
            finally:
                if isinstance(event, wx.Event):  # Check if wxPython event
                    event.Skip()  # pass to next handler
                self.update_graph = False
        else:
            self.plot_adjust(*self.zoom.get_bounds_absolute())

    def on_close(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
