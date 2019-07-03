import wx

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

        #total amount dragged
        self.shift_x = 0
        self.shift_y = 0

        #0 is off, 1 allows user to drag a box
        self.zoom_mode = 0

        #saves current bounds for use in calculating zoom
        self.x_upper = 0
        self.x_lower = 0
        self.y_upper = 0
        self.y_lower = 0

        #If outside border
        self.x_border = 66
        self.y_border = 58
        self.ignore_mouse = False

        #Variables title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Variables:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=20)

        #Get choices for independent and dependent variables
        self.data = Project.get().all_data
        data_choices = [n.data.data_name for n in self.data]

        #INDEPENDENT VARIABLE
        #Create text title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Independent variable(s):'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        #Create listbox
        self.iv_chooser = wx.ListBox(self.panel, choices=data_choices, style=wx.LB_EXTENDED)
        #Position listbox
        ctl_sizer.Add(self.iv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)

        #DEPENDENT VARIABLE
        #Create text title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Dependent variable:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        #Create dropdown selection
        self.dv_chooser = wx.Choice(self.panel, choices=['-'] + data_choices)
        #Position the dropdown menu
        ctl_sizer.Add(self.dv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)

        #PLOT TYPE
        #Create text title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Plot type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        #Create radio buttons
        self.plot_type = wx.RadioBox(self.panel, choices=['scatterplot', 'heatmap'])
        #Position radiobox
        ctl_sizer.Add(self.plot_type, flag=wx.LEFT|wx.RIGHT, border=10)

        #AXIS TYPE
        #Create text title
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Axis type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        #Create radio buttons
        self.axis_type = wx.RadioBox(self.panel, choices=['Fit All', 'Adaptive', 'Zoom'])
        #Position radiobox
        ctl_sizer.Add(self.axis_type, flag=wx.LEFT|wx.RIGHT, border=10)
        #Radio button clicked event
        self.Bind(wx.EVT_RADIOBOX, self.doPlot)

        #Zoom button for dragging a box
        self.zoom_box = wx.Button(self.panel, label="Box")
        zoom_sizer.Add(self.zoom_box, flag=wx.TOP | wx.BOTTOM | wx.LEFT, border=10)

        self.zoom_box.Bind(wx.EVT_BUTTON, self.zoom_mode_change)

        #ZOOM SLIDER
        self.zoom = wx.Slider(self.panel, value = 0, minValue = 0, maxValue = 49, size = (500,-1), style = wx.SL_HORIZONTAL)
        zoom_sizer.Add(self.zoom, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border = 10)

        self.zoom.Bind(wx.EVT_SCROLL, self.doPlot)

        #Graph canvas
        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)

        right_sizer.Add(self.canvas, 1, wx.EXPAND)
        right_sizer.Add(zoom_sizer, wx.EXPAND, border = 10)
        top_sizer.Add(right_sizer)

        #List box event
        self.Bind(wx.EVT_LISTBOX, self.doPlot)
        #Dropdown menu event
        self.Bind(wx.EVT_CHOICE, self.doPlot)
        #Close window
        self.Bind(wx.EVT_CLOSE, self.onClose)
        #Move along with timeline
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.doPlot)

        #Mouse events on graph
        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.mouse_click)
        self.canvas.Bind(wx.EVT_LEFT_UP, self.mouse_up)
        self.canvas.Bind(wx.EVT_MOTION, self.mouse_move)

        #self.canvas.Bind(wx.EVT_LEFT_DOWN, self.doPlot)
        #self.canvas.Bind(wx.EVT_LEFT_UP, self.doPlot)
        #self.canvas.Bind(wx.EVT_MOTION, self.doPlot)

        #Open in the center of VISTAS main window
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    #MOUSE METHODS

    def mouse_move(self, event):
        if self.ignore_mouse == False:
            ms = wx.GetMouseState()
            if ms.leftIsDown:
                mouse_pos = event.GetPosition()
                self.mouse_x_diff = mouse_pos.x - self.mouse_x
                self.mouse_y_diff = mouse_pos.y - self.mouse_y
                if self.zoom_mode == 0:
                    self.doPlot(event)
            else:
                self.mouse_x_diff = 0
                self.mouse_y_diff = 0

    def mouse_click(self, event):
        mouse_pos = event.GetPosition()
        if mouse_pos.x < self.x_border:
            self.ignore_mouse = True
        elif mouse_pos.y > (self.canvas.get_width_height()[1] - self.y_border):
            self.ignore_mouse = True
        else:
            self.ignore_mouse = False
            self.mouse_x = mouse_pos.x
            self.mouse_y = mouse_pos.y
        self.mouse_x_diff = 0
        self.mouse_y_diff = 0

    def mouse_up(self, event):
        if self.ignore_mouse == False:
            mouse_pos = event.GetPosition()
            self.mouse_x_diff = mouse_pos.x - self.mouse_x
            self.mouse_y_diff = mouse_pos.y - self.mouse_y
            self.doPlot(event)
            if self.zoom_mode == 1:
                self.zoom_mode = 0

    #ZOOM METHOD - Allows the user to drag a box

    def zoom_mode_change(self, event):
        self.zoom_mode = 1

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

            #Graph variables
            x_min = iv[0]['min']
            x_max = iv[0]['max']
            y_min = dv[0]['min']
            y_max = dv[0]['max']

            #For use with percentages
            x_ticks = (x_max - x_min) / 100
            y_ticks = (y_max - y_min) / 100

            if axis_type == 'Fit All':
                self.ax.set_xlim(x_min, x_max)
                self.ax.set_ylim(y_min, y_max)
            elif axis_type == 'Zoom':
                #Slows down shifting for the user
                shift_amt = 4

                #Size of graph area (approximately)
                canvas_width = self.canvas.get_width_height()[0]-self.x_border
                canvas_height = self.canvas.get_width_height()[1]-self.y_border

                #Percentage of the screen traveled across
                shift_current_x = -100 * ((self.mouse_x_diff * 100) / (canvas_width * 100))
                shift_current_y = 100 * ((self.mouse_y_diff * 100) / (canvas_height * 100)) #SIGN IS FLIPPED

                #print("shift current", shift_current_x,shift_current_y)

                if self.zoom_mode == 0:
                    #Add current drag to previous user drags
                    self.shift_x += shift_current_x
                    self.shift_y += shift_current_y

                    #Total drag distance divided by the shift amount to slow down movement
                    shift_total_x = self.shift_x * x_ticks / shift_amt
                    shift_total_y = self.shift_y * y_ticks / shift_amt

                else:
                    #calculate center of drawn box
                    center_x_nonpercent = ((self.mouse_x + (self.mouse_x_diff/2)) - self.x_border) - (canvas_width/2)
                    center_y_nonpercent = (canvas_height/2) - (self.mouse_y + (self.mouse_y_diff/2))

                    #center in the form of a percentage of canvas size
                    center_x = 100 * ((center_x_nonpercent * 100) / (canvas_width/2 * 100))
                    center_y = 100 * ((center_y_nonpercent * 100) / (canvas_height/2 * 100))

                    #print("center",center_x,center_y)

                    #Divide the current bounds
                    x_ticks_current = (self.x_upper - self.x_lower)/100
                    y_ticks_current = (self.y_upper - self.y_lower)/100

                    #print("ticks",x_ticks_current*100,y_ticks_current*100)

                    #Set the zoom value based on the largest size of the box
                    if abs(shift_current_x) >= abs(shift_current_y):
                        length = abs(shift_current_x) * x_ticks_current
                        zoom_value = ((((x_max-x_min)-length)/2)/x_ticks)
                        self.zoom.SetValue(round(zoom_value))
                    else:
                        length = abs(shift_current_y) * y_ticks_current
                        zoom_value = ((((y_max - y_min) - length) / 2) / y_ticks)
                        self.zoom.SetValue(round(zoom_value))

                    #The current amount the screen is shifted
                    shift_total_x_old = self.shift_x * x_ticks / shift_amt
                    shift_total_y_old = self.shift_y * y_ticks / shift_amt

                    #The shift needed to center the graph on the center of the box
                    shift_x_new = center_x * x_ticks_current# + x_min
                    shift_y_new = center_y * y_ticks_current# + y_min

                    #print("shift new", shift_x_new, shift_y_new)

                    #The final shift amount
                    shift_total_x = shift_total_x_old + shift_x_new
                    shift_total_y = shift_total_y_old + shift_y_new

                #X AXIS CALCULATIONS
                zoom_amt_x = self.zoom.GetValue() * x_ticks

                x_lo = (x_min + zoom_amt_x) + shift_total_x
                x_hi = (x_max - zoom_amt_x) + shift_total_x

                if x_lo < x_min:
                    x_lo = x_min
                    x_hi = x_max - (2*zoom_amt_x)
                    self.shift_x = self.zoom.GetValue() * shift_amt * -1
                if x_hi > x_max:
                    x_hi = x_max
                    x_lo = x_min + (2*zoom_amt_x)
                    self.shift_x = self.zoom.GetValue() * shift_amt# * -1

                # if outside bounds, need to reset to this
                # shift_total_x = zoom_amt_x
                # self.shift_x*x_ticks*(1/shift_amt) = self.zoom.GetValue() * x_ticks
                # self.shift_x/shift_amt = self.zoom.GetValue()
                # self.shift_x = self.zoom.GetValue() * shift_amt

                #Y AXIS CALCULATIONS
                zoom_amt_y = self.zoom.GetValue() * y_ticks

                # y_lo = y_min + zoom_amt_y - shift_total_y
                # y_hi = y_max - zoom_amt_y - shift_total_y
                y_lo = (y_min + zoom_amt_y) + shift_total_y
                y_hi = (y_max - zoom_amt_y) + shift_total_y

                if y_lo < y_min:
                    y_lo = y_min
                    y_hi = y_max - (2*zoom_amt_y)
                    self.shift_y = self.zoom.GetValue() * shift_amt * -1
                if y_hi > y_max:
                    y_hi = y_max
                    y_lo = y_min + (2*zoom_amt_y)
                    self.shift_y = self.zoom.GetValue() * shift_amt# * -1

                #SET BOUNDS
                self.ax.set_xlim(x_lo, x_hi)
                self.ax.set_ylim(y_lo, y_hi)

                self.x_upper = x_hi
                self.x_lower = x_lo
                self.y_upper = y_hi
                self.y_lower = y_lo

                #print("SHIFT",self.shift_x,self.shift_y)

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
