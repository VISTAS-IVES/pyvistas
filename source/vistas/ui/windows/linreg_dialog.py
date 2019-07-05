import wx

import numpy as np
import numpy.ma as ma

import sklearn as sk
import sklearn.linear_model as sklm
import statsmodels.api as sm

import matplotlib as mpl
mpl.use('WXAgg')
import matplotlib.backends.backend_wxagg as wxagg

#TO DRAW RECTANGLE
from matplotlib.patches import Rectangle

from vistas.ui.project import Project
from vistas.core.timeline import Timeline
from vistas.ui.utils import get_main_window
from vistas.ui.events import EVT_TIMELINE_CHANGED

class LinRegDialog(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title='Linear Regression', size=(800,800))
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.sizer)
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(top_sizer, 0)
        ctl_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(ctl_sizer, 0)

        #sizer for zoom controls
        zoom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        #sizer for the right side of the window
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        #GLOBAL VARIABLES

        #mouse initial positon
        self.mouse_x = 0
        self.mouse_y = 0

        #mouse drag distance
        self.mouse_x_diff = 0
        self.mouse_y_diff = 0

        #0 is off, 1 allows user to drag a box
        self.zoom_mode = 0

        #False if mouse began out of bounds
        self.mouse_continue = True

        #Saves the current bounds of graph
        self.x_hi = 0
        self.x_lo = 0
        self.y_hi = 0
        self.y_lo = 0

        #True if the zoom box should be drawn
        self.draw = False

        #User will be unable to draw a box if zoomed in past this value
        self.zoom_disable_value = 20

        #Variables title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Variables:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=20)

        #Get choices for independent and dependent variables
        self.data = Project.get().all_data
        data_choices = [n.data.data_name for n in self.data]

        #INDEPENDENT VARIABLE
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Independent variable(s):'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)

        self.iv_chooser = wx.ListBox(self.panel, choices=data_choices, style=wx.LB_EXTENDED)
        ctl_sizer.Add(self.iv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)

        #DEPENDENT VARIABLE
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Dependent variable:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)

        self.dv_chooser = wx.Choice(self.panel, choices=['-'] + data_choices)
        ctl_sizer.Add(self.dv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)

        #PLOT TYPE
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Plot type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)

        self.plot_type = wx.RadioBox(self.panel, choices=['scatterplot', 'heatmap'])
        ctl_sizer.Add(self.plot_type, flag=wx.LEFT|wx.RIGHT, border=10)

        #AXIS TYPE
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Axis type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)

        self.axis_type = wx.RadioBox(self.panel, choices=['Fit All', 'Adaptive', 'Zoom'])
        ctl_sizer.Add(self.axis_type, flag=wx.LEFT|wx.RIGHT, border=10)

        self.Bind(wx.EVT_RADIOBOX, self.doPlot)

        #Zoom button for dragging a box
        self.zoom_box = wx.Button(self.panel, label="Box")
        zoom_sizer.Add(self.zoom_box, flag=wx.TOP | wx.BOTTOM | wx.LEFT, border=10)

        self.zoom_box.Bind(wx.EVT_BUTTON, self.zoom_mode_change)

        #ZOOM SLIDER
        self.zoom = wx.Slider(self.panel, value = 0, minValue = 0, maxValue = 49, size = (500,-1), style = wx.SL_HORIZONTAL)
        zoom_sizer.Add(self.zoom, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border = 10)

        self.zoom.Bind(wx.EVT_SCROLL, self.disableZoom)
        self.zoom.Bind(wx.EVT_SCROLL, self.doPlot)

        #Graph canvas
        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)

        #Position canvas and zoom controls
        right_sizer.Add(self.canvas, 1, wx.EXPAND)
        right_sizer.Add(zoom_sizer, wx.EXPAND, border = 10)
        top_sizer.Add(right_sizer)

        #EVENTS
        self.Bind(wx.EVT_LISTBOX, self.doPlot)
        self.Bind(wx.EVT_CHOICE, self.doPlot)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        #Move along with timeline
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.doPlot)

        #Mouse events on graph (Matplotlib events)
        self.fig.canvas.mpl_connect('button_press_event', self.mouse_click)
        self.fig.canvas.mpl_connect('button_release_event', self.mouse_up)
        self.fig.canvas.mpl_connect('motion_notify_event', self.mouse_move)

        #Open in the center of VISTAS main window
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    #Disable the button that allows user to draw a zoom box
    def disableZoom(self, event):
        if self.zoom.GetValue() > self.zoom_disable_value:
            self.zoom_box.Disable()
        else:
            self.zoom_box.Enable()
        event.Skip()

    #Check to see if coordinates are outside the graph
    def checkNone(self, event):
        if event.xdata == None:
            return False
        if event.ydata == None:
            return False
        return True

    #MOUSE METHODS MATPLOTLIB

    def mouse_move(self, event):
        ms = wx.GetMouseState()
        if ms.leftIsDown:
            if self.checkNone(event) & self.mouse_continue:
                self.mouse_x_diff = event.xdata - self.mouse_x
                self.mouse_y_diff = event.ydata - self.mouse_y
                # if self.zoom_mode == 0:
                #     self.doPlot(event)
            self.doPlot(event)
        else:
            self.mouse_x_diff = 0
            self.mouse_y_diff = 0

    def mouse_click(self, event):
        if self.checkNone(event):
            self.mouse_x = event.xdata
            self.mouse_y = event.ydata
            self.mouse_x_diff = 0
            self.mouse_y_diff = 0
            self.mouse_continue = True
        else:
            self.mouse_continue = False

    def mouse_up(self, event):
        if self.checkNone(event) & self.mouse_continue:
            self.mouse_x_diff = event.xdata - self.mouse_x
            self.mouse_y_diff = event.ydata - self.mouse_y
        self.draw = False
        self.doPlot(event)

    #Allows the user to draw a box to zoom
    def zoom_mode_change(self, event):
        self.zoom_mode = 1
        self.draw = True

    #PLOTTTING GRAPH

    def getData(self, dname, data):
        try:
            node = data[[n.data.data_name for n in data].index(dname)]
        except ValueError:
            return None
        variable = node.data.variables[0]
        stats = node.data.variable_stats(variable)
        date = Timeline.app().current
        thisdata = node.data.get_data(variable, date=date)
        return {'name': dname, 'data': thisdata, 'min': stats.min_value, 'max': stats.max_value}


    def plotLinReg(self, iv=None, dv=None):
        try:
          self.fig.delaxes(self.ax)
        except:
          pass

        # stack data and synchronize masks
        my_data = ma.array([d['data'] for d in dv + iv])
        my_data.mask = np.where(ma.sum(my_data.mask, axis=0), True, False)
        my_data = np.array([d.compressed() for d in my_data])

        dv_data = my_data[0]
        # dv_data = dv_data.reshape(dv_data.shape + (1,))
        iv_data = my_data[1:].transpose()

        # ols = sklm.LinearRegression()
        # ols.fit(iv_data, dv_data)
        ols = sm.OLS(dv_data, sm.add_constant(iv_data))
        result = ols.fit()

        if len(iv) == 1: # plot iff we have a single independent variable
            self.ax = self.fig.add_subplot(111)
            self.ax.set_xlabel(iv[0]['name'])
            self.ax.set_ylabel(dv[0]['name'])
            axis_type = self.axis_type.GetString(self.axis_type.GetSelection())

            square = Rectangle((0, 0), 1, 1, alpha = 0.3)
            self.ax.add_patch(square)

            #Graph variables
            x_min = iv[0]['min']
            x_max = iv[0]['max']
            y_min = dv[0]['min']
            y_max = dv[0]['max']

            if axis_type == 'Fit All':
                self.ax.set_xlim(x_min, x_max)
                self.ax.set_ylim(y_min, y_max)
            elif axis_type == 'Zoom':
                #Drawing a zoom box
                if self.draw:
                    # calculate center of drawn box
                    center_x = self.mouse_x + (self.mouse_x_diff / 2)
                    center_y = self.mouse_y + (self.mouse_y_diff / 2)

                    # The current bounds
                    x_length_current = self.x_hi - self.x_lo
                    y_length_current = self.y_hi - self.y_lo

                    x_length = (x_max - x_min)
                    y_length = (y_max - y_min)

                    x_percentage = self.mouse_x_diff / x_length
                    y_percentage = self.mouse_y_diff / y_length

                    #Figure out if the width or height is largest of the user's rectangle
                    if abs(x_percentage) >= abs(y_percentage):
                        x_box = (x_length_current * abs(x_percentage)) / 2
                        y_box = (y_length_current * abs(x_percentage)) / 2
                    else:
                        x_box = (x_length_current * abs(y_percentage)) / 2
                        y_box = (y_length_current * abs(y_percentage)) / 2

                    x_lo = center_x - x_box

                    y_lo = center_y - y_box

                    #Draw a square
                    square.set_width(x_box * 2)
                    square.set_height(y_box * 2)
                    square.set_xy((x_lo, y_lo))
                    self.ax.figure.canvas.draw()

                    #Keep current bounds
                    self.ax.set_xlim(self.x_lo, self.x_hi)
                    self.ax.set_ylim(self.y_lo, self.y_hi)
                else:
                    #Slows down shifting for the user
                    shift_amt = -2 #Sign is flipped or dragging will move opposite of what is expected

                    #size of graph
                    x_length = (x_max - x_min)
                    y_length = (y_max - y_min)
                    x_ticks = (x_length) / 100
                    y_ticks = (y_length) / 100

                    #If not zooming into a drawn box
                    if self.zoom_mode == 0:

                        shift_x = self.mouse_x_diff / shift_amt
                        shift_y = self.mouse_y_diff / shift_amt

                        zoom_amt_x = self.zoom.GetValue() * x_ticks
                        zoom_amt_y = self.zoom.GetValue() * y_ticks

                        x_lo = self.x_lo + shift_x
                        x_hi = x_lo + (x_length - 2*zoom_amt_x)

                        y_lo = self.y_lo + shift_y
                        y_hi = y_lo + (y_length - 2*zoom_amt_y)

                    else:

                        #calculate center of drawn box
                        center_x = self.mouse_x + (self.mouse_x_diff/2)
                        center_y = self.mouse_y + (self.mouse_y_diff/2)

                        #The current bounds
                        x_length_current = self.x_hi - self.x_lo
                        y_length_current = self.y_hi - self.y_lo

                        x_percentage = self.mouse_x_diff / x_length
                        y_percentage = self.mouse_y_diff / y_length

                        #Graph will zoom into a square of whatever side was longer of user's drawn rectangle
                        if abs(x_percentage) >= abs(y_percentage):
                            zoom_value = (abs(x_length-abs(self.mouse_x_diff))/2)/x_ticks #FIX
                            x_box = (x_length_current * abs(x_percentage))/2
                            y_box = (y_length_current * abs(x_percentage))/2
                        else:
                            zoom_value = (abs(y_length-abs(self.mouse_y_diff))/2)/y_ticks
                            x_box = (x_length_current * abs(y_percentage))/2
                            y_box = (y_length_current * abs(y_percentage))/2
                        self.zoom.SetValue(round(zoom_value))

                        zoom_amt_x = self.zoom.GetValue() * x_ticks
                        zoom_amt_y = self.zoom.GetValue() * y_ticks

                        x_lo = center_x - x_box
                        x_hi = x_lo + (x_length - 2*zoom_amt_x)

                        y_lo = center_y - y_box
                        y_hi = y_lo + (y_length - 2*zoom_amt_y)

                        self.zoom_mode = 0

                        if self.zoom.GetValue() > self.zoom_disable_value:
                            self.zoom_box.Disable()
                        else:
                            self.zoom_box.Enable()

                    #CHECK OUT OF BOUNDS

                    #X axis
                    if x_lo < x_min:
                        x_lo = x_min
                        x_hi = x_max - (2*zoom_amt_x)
                    if x_hi > x_max:
                        x_hi = x_max
                        x_lo = x_min + (2*zoom_amt_x)

                    #Y axis
                    if y_lo < y_min:
                        y_lo = y_min
                        y_hi = y_max - (2*zoom_amt_y)
                    if y_hi > y_max:
                        y_hi = y_max
                        y_lo = y_min + (2*zoom_amt_y)

                    #SET BOUNDS
                    self.ax.set_xlim(x_lo, x_hi)
                    self.ax.set_ylim(y_lo, y_hi)

                    #Record bounds for later use
                    self.x_lo = x_lo
                    self.x_hi = x_hi
                    self.y_lo = y_lo
                    self.y_hi = y_hi

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
            else: # heatmap
                bins = 200
                heatmap, iv_edges, dv_edges = np.histogram2d(iv_plot_data, dv_plot_data, bins=bins)
                x_min, x_max = iv_edges[0], iv_edges[-1]
                y_min, y_max = dv_edges[0], dv_edges[-1]
                self.ax.imshow(np.log(heatmap.transpose() + 1),
                  extent=[x_min, x_max, y_min, y_max], cmap='Blues', origin='lower', aspect='auto')
            # plot regression line
            extent = [ma.min(iv_plot_data), ma.max(iv_plot_data)]
            # self.ax.plot(extent, [ols.intercept_[0] + ols.coef_[0] * x for x in extent], 'r--')
            intercept, slope = result.params[0:2]
            self.ax.plot(extent, [intercept + slope * x for x in extent], 'r--')
            self.fig.tight_layout()
            self.canvas.draw()

        # show stats in grids
        try:
          self.grid.Destroy()
          self.cgrid.Destroy()
        except:
          pass

        self.grid = wx.grid.Grid(self.panel, -1)
        self.grid.CreateGrid(2, 2)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        grid_data = [['No. of observations', int(result.nobs)],
            ['r-squared', round(result.rsquared, 3)]]
        for r in range(2):
            for c in range(2):
                self.grid.SetCellValue(r, c, str(grid_data[r][c]))
                self.grid.SetReadOnly(r, c)
        self.grid.AutoSize()
        self.sizer.Add(self.grid, 2, flag=wx.ALL, border=10)
       
        self.cgrid = wx.grid.Grid(self.panel, -1)
        nvars = len(iv)
        col_labels = ['variable', 'coeff', 'std err', 't', 'P>|t|', '[.025', '0.975]']
        row_labels = ['const'] + [v['name'] for v in iv]
        self.cgrid.CreateGrid(len(row_labels), len(col_labels))
        self.cgrid.SetRowLabelSize(0) # hide row numbers
        conf_int = result.conf_int()
        grid_data = [[row_labels[i],
          result.params[i], result.bse[i], result.tvalues[i], result.pvalues[i],
          conf_int[i][0], conf_int[i][1]]
          for i in range(nvars+1)]

        for i,l in enumerate(col_labels):
            if i > 0:
                self.cgrid.SetColFormatFloat(i, 6, 3)
            self.cgrid.SetColLabelValue(i, l)
        for r in range(1 + nvars):
            for c in range(len(col_labels)):
                self.cgrid.SetCellValue(r, c, str(grid_data[r][c]))
                self.cgrid.SetReadOnly(r, c)
        self.cgrid.AutoSize()
        self.sizer.Add(self.cgrid, 2, flag=wx.BOTTOM|wx.LEFT, border=10)

        self.sizer.AddStretchSpacer()
        self.panel.Layout()



    def doPlot(self, event):
        try:
            iv_selections = [self.iv_chooser.GetString(s) for s in self.iv_chooser.GetSelections()]
            dv_selection = self.dv_chooser.GetString(self.dv_chooser.GetSelection())
            if dv_selection in iv_selections:
                iv_selections.remove(dv_selection)
            if len(iv_selections) > 0 and dv_selection != '-': # good to go
                data = {}
                for v, sel in zip(['iv', 'dv'], [iv_selections, [dv_selection]]):
                    dd = []
                    for dname in sel:
                        try:
                            thisdata = self.getData(dname, self.data)
                            if thisdata is not None:
                                dd.append(thisdata)
                        except Exception as ex:
                            print(ex)
                    data[v] = dd
                if len(data['iv']) >= 1 and len(data['dv']) >= 1:
                    self.plotLinReg(**data)
        finally:
            event.Skip() # pass to next handler

    def onClose(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
