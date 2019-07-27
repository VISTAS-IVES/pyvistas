import wx
import vistas.ui.windows.zoom as zoom_file

import numpy as np
import numpy.ma as ma

import sklearn as sk
import sklearn.linear_model as sklm
import statsmodels.api as sm

import matplotlib as mpl
mpl.use('WXAgg')
import matplotlib.backends.backend_wxagg as wxagg

from vistas.ui.project import Project
from vistas.core.timeline import Timeline
from vistas.ui.utils import get_main_window
from vistas.ui.events import EVT_TIMELINE_CHANGED


class LinRegDialog(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title='Linear Regression', size=(800, 800))

        self.zoom = zoom_file.Zoom()

        # Global variables
        self.reset_bounds = True  # True if bounds have been reset by changing variables
        self.update_graph = True  # True if graph needs to be updated
        self.update_table = True  # True if data tables need to be updated

        # Sizers
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)  # Main sizer
        self.panel.SetSizer(self.sizer)
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)  # Sizer to divide screen into left and right halves
        self.sizer.Add(top_sizer, 0)
        ctl_sizer = wx.BoxSizer(wx.VERTICAL)  # Sizer for the controls on left size of the screen
        top_sizer.Add(ctl_sizer, 0)
        zoom_sizer = wx.BoxSizer(wx.HORIZONTAL)  # Sizer for the zoom controls
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)  # Sizer for the right half of the window

        # Variables title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Variables:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=20)

        # Get choices for independent and dependent variables
        self.data = Project.get().all_data
        data_choices = [n.data.data_name for n in self.data]

        # Independent variable
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Independent variable(s):'), flag=wx.TOP | wx.LEFT | wx.RIGHT,
                      border=12)

        self.iv_chooser = wx.ListBox(self.panel, choices=data_choices, style=wx.LB_EXTENDED)
        ctl_sizer.Add(self.iv_chooser, flag=wx.LEFT | wx.RIGHT, border=12)

        # Dependent variable
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Dependent variable:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=12)

        self.dv_chooser = wx.Choice(self.panel, choices=['-'] + data_choices)
        ctl_sizer.Add(self.dv_chooser, flag=wx.LEFT | wx.RIGHT, border=12)

        # Plot type
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Plot type:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=12)

        self.plot_type = wx.RadioBox(self.panel, choices=['scatterplot', 'heatmap'])
        ctl_sizer.Add(self.plot_type, flag=wx.LEFT | wx.RIGHT, border=10)

        # Axis type
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Axis type:'), flag=wx.TOP | wx.LEFT | wx.RIGHT, border=12)

        self.axis_type = wx.RadioBox(self.panel, choices=['Fit All', 'Adaptive', 'Zoom'])
        ctl_sizer.Add(self.axis_type, flag=wx.LEFT | wx.RIGHT, border=10)

        self.Bind(wx.EVT_RADIOBOX, self.on_axis_change)

        # Blank spacer
        ctl_sizer.AddSpacer(220)

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

        # Graph canvas
        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)

        self.right_sizer.Add(self.canvas, 1, wx.EXPAND)
        self.right_sizer.Add(zoom_sizer, flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
        top_sizer.Add(self.right_sizer)

        # Events

        self.Bind(wx.EVT_LISTBOX, self.on_var_change)
        self.Bind(wx.EVT_CHOICE, self.on_var_change)

        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Move along with timeline
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.on_timeline_change)

        # Mouse events on graph (Matplotlib events)
        self.fig.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # Open in the center of VISTAS main window
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    def on_axis_change(self, event):
        """Update graph when user selects a new axis type"""
        self.update_graph = True
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
        variable = node.data.variables[0]
        stats = node.data.variable_stats(variable)
        date = Timeline.app().current
        thisdata = node.data.get_data(variable, date=date)
        return {'name': dname, 'data': thisdata, 'min': stats.min_value, 'max': stats.max_value}

    def plot_adjust(self, x1, x2, y1, y2):
        """Adjust the bounds of the current graph without redrawing it"""
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())

        if self.zoom.square in self.ax.get_children():
            self.zoom.square.remove()

        if axis_type == 'Zoom':
            self.plot_zoom_graph(x1, x2, y1, y2)

        self.ax.figure.canvas.draw()

    def plot_lin_reg(self, iv=None, dv=None):
        # stack data and synchronize masks
        my_data = ma.array([d['data'] for d in dv + iv])
        my_data.mask = np.where(ma.sum(my_data.mask, axis=0), True, False)
        my_data = np.array([d.compressed() for d in my_data])

        dv_data = my_data[0]
        iv_data = my_data[1:].transpose()

        ols = sm.OLS(dv_data, sm.add_constant(iv_data))
        result = ols.fit()

        self.create_graph(iv, dv, my_data, result)

        # Only draw tables if variables have been changed
        if self.update_table:
            self.create_table(iv, result)

    def create_graph(self, iv=None, dv=None, my_data=None, result=None):
        try:
            self.fig.delaxes(self.ax)
        except AttributeError:
            pass

        if len(iv) == 1:  # plot iff we have a single independent variable
            self.ax = self.fig.add_subplot(111)
            self.ax.set_xlabel(iv[0]['name'])
            self.ax.set_ylabel(dv[0]['name'])
            axis_type = self.axis_type.GetString(self.axis_type.GetSelection())

            # Type of axis
            if axis_type == 'Fit All':
                self.ax.set_xlim(iv[0]['min'], iv[0]['max'])
                self.ax.set_ylim(dv[0]['min'], dv[0]['max'])
            elif axis_type == 'Zoom':
                self.plot_zoom_graph(iv[0]['min'], iv[0]['max'], dv[0]['min'], dv[0]['max'])

            self.zoom.set_bounds_absolute(iv[0]['min'], iv[0]['max'], dv[0]['min'], dv[0]['max'])

            self.ax.grid()

            dv_plot_data = my_data[0]
            iv_plot_data = my_data[1]

            plot_type = self.plot_type.GetString(self.plot_type.GetSelection())
            if plot_type == 'scatterplot':
                # adjust marker size and alpha based on how many points we're plotting
                marker_size = mpl.rcParams['lines.markersize'] ** 2
                marker_size *= min(1, max(.12, 200 / len(iv_plot_data)))
                alpha = min(1, max(.002, 500 / len(iv_plot_data)))
                self.ax.scatter(iv_plot_data, dv_plot_data, s=marker_size, alpha=alpha)
            else:  # heatmap
                bins = 200
                heatmap, iv_edges, dv_edges = np.histogram2d(iv_plot_data, dv_plot_data, bins=bins)
                x_min, x_max = iv_edges[0], iv_edges[-1]
                y_min, y_max = dv_edges[0], dv_edges[-1]
                self.ax.imshow(np.log(heatmap.transpose() + 1),
                               extent=[x_min, x_max, y_min, y_max], cmap='Blues', origin='lower', aspect='auto')

            # plot regression line
            extent = [ma.min(iv_plot_data), ma.max(iv_plot_data)]
            intercept, slope = result.params[0:2]
            self.ax.plot(extent, [intercept + slope * x for x in extent], 'r--')
            self.fig.tight_layout()
            self.canvas.draw()

    def create_table(self, iv=None, result=None):
        self.panel.Freeze()

        # show stats in grids
        try:
            self.grid.Destroy()
            self.cgrid.Destroy()
        except AttributeError:
            pass

        # Grid 1
        self.grid = wx.grid.Grid(self.panel, -1)
        self.grid.CreateGrid(2, 2)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        grid_data = [['No. of observations', int(result.nobs)], ['r-squared', round(result.rsquared, 3)]]
        for r in range(2):
            for c in range(2):
                self.grid.SetCellValue(r, c, str(grid_data[r][c]))
                self.grid.SetReadOnly(r, c)
        self.grid.AutoSize()

        self.sizer.AddStretchSpacer(1)
        self.sizer.Add(self.grid, 2, flag=wx.ALL, border=10)

        # Grid 2
        self.cgrid = wx.grid.Grid(self.panel, -1)
        nvars = len(iv)
        col_labels = ['variable', 'coeff', 'std err', 't', 'P>|t|', '[.025', '0.975]']
        row_labels = ['const'] + [v['name'] for v in iv]
        self.cgrid.CreateGrid(len(row_labels), len(col_labels))
        self.cgrid.SetRowLabelSize(0)  # hide row numbers
        conf_int = result.conf_int()
        grid_data = [[row_labels[i], result.params[i], result.bse[i], result.tvalues[i], result.pvalues[i],
                      conf_int[i][0], conf_int[i][1]] for i in range(nvars+1)]

        for i, l in enumerate(col_labels):
            if i > 0:
                self.cgrid.SetColFormatFloat(i, 6, 3)
            self.cgrid.SetColLabelValue(i, l)
        for r in range(1 + nvars):
            for c in range(len(col_labels)):
                self.cgrid.SetCellValue(r, c, str(grid_data[r][c]))
                self.cgrid.SetReadOnly(r, c)
        self.cgrid.AutoSize()

        self.sizer.Add(self.cgrid, 2, flag=wx.BOTTOM | wx.LEFT, border=10)

        self.panel.Layout()
        self.panel.Thaw()

        self.update_table = False

    def do_plot(self, event):
        # Check if zoom controls should be disabled
        self.disable_zoom_check()

        try:
            if self.zoom.square in self.ax.get_children():
                self.zoom.square.remove()
        except AttributeError:
            pass

        if self.update_graph:
            try:
                iv_selections = [self.iv_chooser.GetString(s) for s in self.iv_chooser.GetSelections()]
                dv_selection = self.dv_chooser.GetString(self.dv_chooser.GetSelection())
                if dv_selection in iv_selections:
                    iv_selections.remove(dv_selection)
                if len(iv_selections) > 0 and dv_selection != '-':  # good to go
                    data = {}
                    for v, sel in zip(['iv', 'dv'], [iv_selections, [dv_selection]]):
                        dd = []
                        for dname in sel:
                            try:
                                thisdata = self.get_data(dname, self.data)
                                if thisdata is not None:
                                    dd.append(thisdata)
                            except Exception as ex:
                                print(ex)
                        data[v] = dd
                    if len(data['iv']) >= 1 and len(data['dv']) >= 1:
                        self.plot_lin_reg(**data)
            finally:
                if isinstance(event, wx.Event):  # Check if wxPython event
                    event.Skip()  # pass to next handler
                self.update_graph = False
        else:
            self.plot_adjust(*self.zoom.get_bounds_absolute())

    def on_close(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
