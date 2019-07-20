import wx

import numpy as np
import numpy.ma as ma

import sklearn as sk
import sklearn.linear_model as sklm
import statsmodels.api as sm

import matplotlib as mpl
mpl.use('WXAgg')
import matplotlib.backends.backend_wxagg as wxagg

from matplotlib.patches import Rectangle

from vistas.ui.project import Project
from vistas.core.timeline import Timeline
from vistas.ui.utils import get_main_window
from vistas.ui.events import EVT_TIMELINE_CHANGED


class LinRegDialog(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title='Linear Regression', size=(800, 800))

        # Global variables
        self.zoom_box_enabled = False  # User can draw a box if True
        self.mouse_in_bounds = True  # False if mouse was out of bounds
        self.draw_zoom_box = False  # True if the zoom box should be drawn
        self.reset_bounds = True  # True if bounds have been reset by changing variables
        self.update_graph = True  # True if graph needs to be updated
        self.update_table = True  # True if data tables need to be updated
        self.zoom_disable_value = 48  # User will be unable to draw a box if zoomed in past this value

        # Mouse initial position
        self.mouse_x = 0
        self.mouse_y = 0

        # Mouse drag distance
        self.mouse_x_diff = 0
        self.mouse_y_diff = 0

        # Current bounds of the graph
        self.x_hi = 0
        self.x_lo = 0
        self.y_hi = 0
        self.y_lo = 0

        # Center of the viewport
        self.center_x = 0
        self.center_y = 0

        # Absolute bounds of the graph
        self.x_lo_absolute = 0
        self.x_hi_absolute = 0
        self.y_lo_absolute = 0
        self.y_hi_absolute = 0

        # Square for user drawn box
        self.square = Rectangle((0, 0), 1, 1, alpha=0.3, color='red')

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
        self.zoom = wx.Slider(self.panel, value=0, minValue=0, maxValue=49, size=(600, -1),
                              style=wx.SL_HORIZONTAL)
        zoom_sizer.Add(self.zoom, flag=wx.LEFT, border=10)

        self.zoom.Bind(wx.EVT_SCROLL, self.on_zoom_scroll)

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
        self.zoom.SetValue(0)
        self.zoom_box_enabled = False

        # Set bounds to fully zoomed out
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)

        # Save bound variables
        self.x_lo = x_min
        self.x_hi = x_max
        self.y_lo = y_min
        self.y_hi = y_max

        # Calculate center point
        self.center_x = x_min + (x_max - x_min) / 2
        self.center_y = y_min + (y_max - y_min) / 2

        if self.square in self.ax.get_children():
            self.square.remove()

        self.reset_bounds = False

    def on_zoom_scroll(self, event):
        self.disable_zoom
        self.do_plot(event)

    def disable_zoom(self):
        """Disable the button that allows user to draw a zoom box"""
        if self.zoom.GetValue() > self.zoom_disable_value:
            self.zoom_box.Disable()
        else:
            self.zoom_box.Enable()

    def disable_zoom_check(self):
        """Enable zoom controls if axis type is set to Zoom"""
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type == 'Zoom':
            self.zoom.Enable()
            self.disable_zoom()
        else:
            self.zoom.Disable()
            self.zoom_box.Disable()

    def check_none(self, event):
        """Check if mouse coordinates are outside of the graph bounds"""
        if event.xdata is None:
            return False
        if event.ydata is None:
            return False
        return True

    def on_zoom_box_button(self, event):
        """Allow the user to draw a box on the graph"""
        self.zoom_box_enabled = True
        self.draw_zoom_box = True

    # MOUSE METHODS MATPLOTLIB

    def on_mouse_move(self, event):
        """Get mouse position when moving"""
        ms = wx.GetMouseState()
        if ms.leftIsDown:
            if self.check_none(event) and self.mouse_in_bounds:
                self.mouse_x_diff = event.xdata - self.mouse_x
                self.mouse_y_diff = event.ydata - self.mouse_y
            self.do_plot(event)
        else:
            self.mouse_x_diff = 0
            self.mouse_y_diff = 0

    def on_mouse_press(self, event):
        """Get mouse position when left clicking"""
        ms = wx.GetMouseState()
        if ms.leftIsDown:
            if self.check_none(event):
                self.mouse_x = event.xdata
                self.mouse_y = event.ydata
                self.mouse_x_diff = 0
                self.mouse_y_diff = 0
                self.mouse_in_bounds = True
            else:
                self.mouse_in_bounds = False

    def on_mouse_release(self, event):
        """Get mouse position when releasing a mouse press"""
        if self.check_none(event) and self.mouse_in_bounds:
            self.mouse_x_diff = event.xdata - self.mouse_x
            self.mouse_y_diff = event.ydata - self.mouse_y
        elif self.check_none(event):
            self.mouse_in_bounds = False
        self.draw_zoom_box = False
        self.do_plot(event)

    # PLOTTING GRAPH

    def plot_zoom_graph(self, x_min, x_max, y_min, y_max):
        """Calculate the bounds of the graph when 'Zoom' axis type is selected"""

        # If variables have been changed, graph should be reset
        if self.reset_bounds:
            self.reset_graph(x_min, x_max, y_min, y_max)

        # Current boundaries will be kept
        keep_bounds = True

        # Size of boundaries
        x_length = (x_max - x_min)
        y_length = (y_max - y_min)

        # Divide sides for percentages
        x_ticks = x_length / 100
        y_ticks = y_length / 100

        # Set initial values
        x_lo = self.x_lo
        x_hi = self.x_hi
        y_lo = self.y_lo
        y_hi = self.y_hi
        zoom_amt_x = 0
        zoom_amt_y = 0

        # User drawn box to zoom in to
        if self.zoom_box_enabled:

            # The length of the zoomed in bounds
            x_length_current = abs(self.x_hi - self.x_lo)
            y_length_current = abs(self.y_hi - self.y_lo)

            # Percentage of the total bounds covered
            x_percentage = self.mouse_x_diff / x_length_current
            y_percentage = self.mouse_y_diff / y_length_current

            # Figure out if the width or height is largest of the user's rectangle
            if abs(x_percentage) >= abs(y_percentage):
                zoom_value = ((x_length - abs(self.mouse_x_diff)) / 2) / x_ticks
                x_box = (x_length_current * abs(x_percentage)) / 2
                y_box = (y_length_current * abs(x_percentage)) / 2
            else:
                zoom_value = ((y_length - abs(self.mouse_y_diff)) / 2) / y_ticks
                x_box = (x_length_current * abs(y_percentage)) / 2
                y_box = (y_length_current * abs(y_percentage)) / 2

            # Drawing a box on the graph
            if self.draw_zoom_box:
                self.ax.add_patch(self.square)

                # Set length of box sides
                self.square.set_width(x_box * 2)
                self.square.set_height(y_box * 2)

                # Draw corner of box depending on which direction the user is dragging
                if (x_percentage >= 0) and (y_percentage >= 0):
                    self.square.set_xy((self.mouse_x, self.mouse_y))
                elif (x_percentage <= 0) and (y_percentage >= 0):
                    self.square.set_xy((self.mouse_x - (x_box * 2), self.mouse_y))
                elif (x_percentage <= 0) and (y_percentage <= 0):
                    self.square.set_xy((self.mouse_x - (x_box * 2), self.mouse_y - (y_box * 2)))
                else:
                    self.square.set_xy((self.mouse_x, self.mouse_y - (y_box * 2)))

                self.ax.figure.canvas.draw()

            # Zooming into a drawn box
            elif zoom_value < 50 and self.mouse_in_bounds:

                self.zoom.SetValue(round(zoom_value))

                if (x_percentage >= 0) and (y_percentage >= 0):
                    x_lo = self.mouse_x
                    y_lo = self.mouse_y
                elif (x_percentage <= 0) and (y_percentage >= 0):
                    x_lo = self.mouse_x - (x_box * 2)
                    y_lo = self.mouse_y
                elif (x_percentage <= 0) and (y_percentage <= 0):
                    x_lo = self.mouse_x - (x_box * 2)
                    y_lo = self.mouse_y - (y_box * 2)
                else:
                    x_lo = self.mouse_x
                    y_lo = self.mouse_y - (y_box * 2)

                zoom_amt_x = self.zoom.GetValue() * x_ticks
                zoom_amt_y = self.zoom.GetValue() * y_ticks

                x_hi = x_lo + (x_length - 2 * zoom_amt_x)

                y_hi = y_lo + (y_length - 2 * zoom_amt_y)

                self.center_x = x_lo + (x_length / 2 - zoom_amt_x)
                self.center_y = y_lo + (y_length / 2 - zoom_amt_y)

                if self.zoom.GetValue() > self.zoom_disable_value:
                    self.zoom_box.Disable()
                else:
                    self.zoom_box.Enable()

                keep_bounds = False

            self.zoom_box_enabled = self.draw_zoom_box

        else:
            # Slows down shifting for the user
            shift_amt = -1.5  # Sign is flipped or dragging will move opposite of what is expected

            # Distance user dragged across screen to shift viewport
            shift_x = self.mouse_x_diff / shift_amt
            shift_y = self.mouse_y_diff / shift_amt

            # Amount to zoom in by based on the value of the slider
            zoom_amt_x = self.zoom.GetValue() * x_ticks
            zoom_amt_y = self.zoom.GetValue() * y_ticks

            # Shift the center by the amount user dragged
            self.center_x += shift_x
            self.center_y += shift_y

            # Calculate bounds based on center and zoom amount

            x_lo = self.center_x - (x_length / 2 - zoom_amt_x)
            x_hi = self.center_x + (x_length / 2 - zoom_amt_x)

            y_lo = self.center_y - (y_length / 2 - zoom_amt_y)
            y_hi = self.center_y + (y_length / 2 - zoom_amt_y)

            keep_bounds = False

        if keep_bounds:
            # Keep current bounds
            self.ax.set_xlim(self.x_lo, self.x_hi)
            self.ax.set_ylim(self.y_lo, self.y_hi)
        else:
            # Check if new bounds are within absolute bounds

            # X axis
            if x_lo < x_min:
                x_lo = x_min
                x_hi = x_max - (2 * zoom_amt_x)
                self.center_x = x_min + (x_length / 2 - zoom_amt_x)
            if x_hi > x_max:
                x_hi = x_max
                x_lo = x_min + (2 * zoom_amt_x)
                self.center_x = x_max - (x_length / 2 - zoom_amt_x)

            # Y axis
            if y_lo < y_min:
                y_lo = y_min
                y_hi = y_max - (2 * zoom_amt_y)
                self.center_y = y_min + (y_length / 2 - zoom_amt_y)
            if y_hi > y_max:
                y_hi = y_max
                y_lo = y_min + (2 * zoom_amt_y)
                self.center_y = y_max - (y_length / 2 - zoom_amt_y)

            # Set new bounds
            self.ax.set_xlim(x_lo, x_hi)
            self.ax.set_ylim(y_lo, y_hi)

            # Record bounds for later use
            self.x_lo = x_lo
            self.x_hi = x_hi
            self.y_lo = y_lo
            self.y_hi = y_hi

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

        if self.square in self.ax.get_children():
            self.square.remove()

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

            self.x_lo_absolute = iv[0]['min']
            self.x_hi_absolute = iv[0]['max']
            self.y_lo_absolute = dv[0]['min']
            self.y_hi_absolute = dv[0]['max']

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
            if self.square in self.ax.get_children():
                self.square.remove()
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
            self.plot_adjust(self.x_lo_absolute, self.x_hi_absolute, self.y_lo_absolute, self.y_hi_absolute)

    def on_close(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
