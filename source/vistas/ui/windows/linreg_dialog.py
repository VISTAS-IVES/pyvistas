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

        y_sizer = wx.BoxSizer(wx.HORIZONTAL)
        x_sizer = wx.BoxSizer(wx.VERTICAL)

        right_sizer = wx.BoxSizer(wx.VERTICAL)

        zoom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.zoom_amt = 0;

        self.mouse_x = 0;
        self.mouse_y = 0;

        self.mouse_x_diff = 0;
        self.mouse_y_diff = 0;

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
        self.axis_type = wx.RadioBox(self.panel, choices=['Fit All', 'Adaptive', 'Fixed', 'Zoom'])
        #Position radiobox
        ctl_sizer.Add(self.axis_type, flag=wx.LEFT|wx.RIGHT, border=10)
        #Radio button clicked event
        self.Bind(wx.EVT_RADIOBOX, self.doPlot)

        self.zoom_in = wx.Button(self.panel, label="Zoom In")
        zoom_sizer.Add(self.zoom_in, flag=wx.LEFT, border=10)

        self.zoom_out = wx.Button(self.panel, label="Zoom Out")
        zoom_sizer.Add(self.zoom_out, flag=wx.LEFT|wx.RIGHT, border=10)

        ctl_sizer.Add(zoom_sizer, flag=wx.TOP|wx.BOTTOM, border=10)

        self.zoom_in.Bind(wx.EVT_BUTTON, self.doPlot)
        self.zoom_out.Bind(wx.EVT_BUTTON, self.doPlot)

        self.zoom_in.Bind(wx.EVT_BUTTON, self.zooming_in)
        self.zoom_out.Bind(wx.EVT_BUTTON, self.zooming_out)

        #Adjust Axis
        #Create sliders for y axis
        self.y_min = wx.Slider(self.panel, value = 100, minValue = 0, maxValue = 100, style = wx.SL_VERTICAL)
        y_sizer.Add(self.y_min, flag=wx.LEFT|wx.EXPAND, border = 10)

        self.y_max = wx.Slider(self.panel, value=0, minValue=0, maxValue=100, style=wx.SL_VERTICAL)
        y_sizer.Add(self.y_max, flag=wx.EXPAND, border=0)

        self.x_min = wx.Slider(self.panel, value=0, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        x_sizer.Add(self.x_min, flag=wx.LEFT|wx.EXPAND, border=55)

        self.x_max = wx.Slider(self.panel, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
        x_sizer.Add(self.x_max, flag=wx.LEFT|wx.EXPAND, border=55)

        #SLIDER EVENTS - One to keep sliders from passing each other and another to draw the plot
        self.y_min.Bind(wx.EVT_SCROLL, self.y_min_change)
        self.y_min.Bind(wx.EVT_SCROLL, self.doPlot)
        self.y_max.Bind(wx.EVT_SCROLL, self.y_max_change)
        self.y_max.Bind(wx.EVT_SCROLL, self.doPlot)
        self.x_min.Bind(wx.EVT_SCROLL, self.x_min_change)
        self.x_min.Bind(wx.EVT_SCROLL, self.doPlot)
        self.x_max.Bind(wx.EVT_SCROLL, self.x_max_change)
        self.x_max.Bind(wx.EVT_SCROLL, self.doPlot)

        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)
        #top_sizer.Add(self.canvas, 1, wx.EXPAND)
        y_sizer.Add(self.canvas, 1, wx.EXPAND)
        right_sizer.Add(y_sizer)
        right_sizer.Add(x_sizer, flag=wx.EXPAND, border=10)
        top_sizer.Add(right_sizer)

        #List box event
        self.Bind(wx.EVT_LISTBOX, self.doPlot)
        #Dropdown menu event
        self.Bind(wx.EVT_CHOICE, self.doPlot)
        #Close window
        self.Bind(wx.EVT_CLOSE, self.onClose)
        #Move along with timeline
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.doPlot)

        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.mouse_click)
        self.canvas.Bind(wx.EVT_LEFT_UP, self.mouse_up)
        self.canvas.Bind(wx.EVT_MOTION, self.mouse_move)

        #Open in the center of VISTAS main window
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    def mouse_move(self, event):
        ms = wx.GetMouseState()
        if ms.leftIsDown:
            mouse_pos = event.GetPosition()
            self.mouse_x_diff = mouse_pos.x - self.mouse_x
            self.mouse_y_diff = mouse_pos.y - self.mouse_y
            print(self.mouse_x_diff, self.mouse_y_diff)

    def mouse_click(self, event):
        mouse_pos = event.GetPosition()
        self.mouse_x = mouse_pos.x;
        self.mouse_y = mouse_pos.y;
        #print("Up:", mouse_pos.x, mouse_pos.y)

    def mouse_up(self, event):
        mouse_pos = event.GetPosition()
        self.mouse_x_diff = mouse_pos.x - self.mouse_x
        self.mouse_y_diff = mouse_pos.y - self.mouse_y
        print("Total:", self.mouse_x_diff, self.mouse_y_diff)

    def zooming_in(self, event):
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type=='Zoom':
            if self.zoom_amt<3:
                self.zoom_amt+=1
                event.Skip()
                self.doPlot
        #print(self.zoom_amt)

    def zooming_out(self, event):
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type == 'Zoom':
            if self.zoom_amt > 0:
                self.zoom_amt -= 1
                event.Skip()
                self.doPlot
        #print(self.zoom_amt)

    def y_min_change(self, event):
        if self.y_min.GetValue() <= self.y_max.GetValue():
            self.y_max.SetValue(self.y_min.GetValue()-1)
        if self.y_min.GetValue() == 0:
            self.y_min.SetValue(1)

    def y_max_change(self, event):
        if self.y_max.GetValue() >= self.y_min.GetValue():
            self.y_min.SetValue(self.y_max.GetValue()+1)
        if self.y_max.GetValue() == 100:
            self.y_max.SetValue(99)

    def x_min_change(self, event):
        if self.x_min.GetValue() >= self.x_max.GetValue():
            self.x_max.SetValue(self.x_min.GetValue()+1)
        if self.x_min.GetValue() == 100:
            self.x_min.SetValue(99)

    def x_max_change(self, event):
        if self.x_max.GetValue() <= self.x_min.GetValue():
            self.x_min.SetValue(self.x_max.GetValue()-1)
        if self.x_max.GetValue() == 0:
            self.x_max.SetValue(1)

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

            iv_ticks = (iv[0]['max'] - iv[0]['min']) / 100
            dv_ticks = (dv[0]['max'] - dv[0]['min']) / 100
            #AXIS TYPE FIXED
            if axis_type == 'Fit All':
                self.ax.set_xlim(iv[0]['min'], iv[0]['max'])
                self.ax.set_ylim(dv[0]['min'], dv[0]['max'])
            elif axis_type == 'Fixed':
                self.ax.set_xlim(iv[0]['min']+(self.x_min.GetValue()*iv_ticks), iv[0]['min']+(self.x_max.GetValue()*iv_ticks))
                self.ax.set_ylim(dv[0]['max']-(self.y_min.GetValue()*dv_ticks), dv[0]['max']-(self.y_max.GetValue()*dv_ticks))
            elif axis_type == 'Zoom':
                zoom_mult = 10
                self.ax.set_xlim(iv[0]['min'] + (self.zoom_amt * iv_ticks * zoom_mult),
                                 iv[0]['max'] - (self.zoom_amt * iv_ticks * zoom_mult))
                self.ax.set_ylim(dv[0]['min'] + (self.zoom_amt * dv_ticks * zoom_mult),
                                 dv[0]['max'] - (self.zoom_amt * dv_ticks * zoom_mult))
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
