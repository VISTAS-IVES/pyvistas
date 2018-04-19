import wx

import numpy as np
import numpy.ma as ma
import sklearn as sk
import sklearn.linear_model as lm

import matplotlib as mpl
mpl.use('WXAgg')
import matplotlib.backends.backend_wxagg as wxagg

from vistas.ui.project import Project
from vistas.core.timeline import Timeline
from vistas.ui.utils import get_main_window
from vistas.ui.events import EVT_TIMELINE_CHANGED

class StatsDialog(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, size=(800,600))
        self.parent = parent
        self.data = Project.get().all_data
        data_choices = ['-'] + [n.data.data_name for n in self.data]

        self.panel = wx.Panel(self)
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.ctl_box = wx.BoxSizer(wx.VERTICAL)

        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Independent variable(s):'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.iv_chooser = wx.Choice(self.panel, choices=data_choices)
        self.ctl_box.Add(self.iv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)

        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Dependent variable'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.dv_chooser = wx.Choice(self.panel, choices=data_choices)
        self.ctl_box.Add(self.dv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)

        self.Bind(wx.EVT_CHOICE, self.doPlot)

        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Plot type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.plot_type = wx.RadioBox(self.panel, choices=['scatterplot', 'heatmap'])
        self.ctl_box.Add(self.plot_type, flag=wx.LEFT|wx.RIGHT, border=10)
        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Axis type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.axis_type = wx.RadioBox(self.panel, choices=['fixed', 'adaptive'])
        self.ctl_box.Add(self.axis_type, flag=wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_RADIOBOX, self.doPlot)
        box.Add(self.ctl_box)

        self.dsp_box = wx.BoxSizer(wx.VERTICAL)
        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)
        self.dsp_box.Add(self.canvas, 1, wx.GROW)
        box.Add(self.dsp_box)
        self.panel.SetSizer(box)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.doPlot)
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    def getData(self, dname, data):
        try:
            node = data[[n.data.data_name for n in data].index(dname)]
        except ValueError:
            return None
        variable = node.data.variables[0]
        stats = node.data.variable_stats(variable)
        date = Timeline.app().current
        thisdata = node.data.get_data(variable, date=date)
        return [stats.min_value, stats.max_value, thisdata]

    def plotLinReg(self, iv=None, dv=None):
        try:
          self.fig.delaxes(self.ax)
        except:
          pass
        self.ax = self.fig.add_subplot(111)
        self.ax.grid()
        self.ax.set_xlabel(iv[0])
        self.ax.set_ylabel(dv[0])
        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type == 'fixed':
            self.ax.set_xlim(iv[1], iv[2])
            self.ax.set_ylim(dv[1], dv[2])
    
        iv_data = iv[3]
        dv_data = dv[3]
        
        # synchronize masks
        mask = np.logical_or(ma.array(iv_data).mask, ma.array(dv_data).mask)
        iv_data = ma.array(iv_data, mask=mask).compressed()
        dv_data = ma.array(dv_data, mask=mask).compressed()

        plot_type = self.plot_type.GetString(self.plot_type.GetSelection())
        if plot_type == 'scatterplot':
            # adjust marker size and alpha based on how many points we're plotting
            marker_size = mpl.rcParams['lines.markersize'] ** 2
            marker_size *= min(1, max(.12, 200 / len(iv_data)))
            alpha = min(1, max(.002, 500 / len(iv_data)))
            self.ax.scatter(iv_data, dv_data, s=marker_size, alpha=alpha)
        else: # heatmap
            bins = 200
            heatmap, iv_edges, dv_edges = np.histogram2d(iv_data, dv_data, bins=bins)
            x_min, x_max = iv_edges[0], iv_edges[-1]
            y_min, y_max = dv_edges[0], dv_edges[-1]
            self.ax.imshow(np.log(heatmap.transpose() + 1), extent=[x_min, x_max, y_min, y_max], cmap='Blues', origin='lower', aspect='auto')

    
        # calculate regression
        ols = lm.LinearRegression()
        ols.fit(iv_data.reshape(-1,1), dv_data.reshape(-1,1))
        r2 = ols.score(iv_data.reshape(-1,1), dv_data.reshape(-1,1))
    
        # predict values to get slope and intercept
        res = ols.predict(np.array([0,1]).reshape(-1,1))
        intercept = res[0][0]
        slope = res[1][0] - intercept
    
        extent = [ma.min(iv_data), ma.max(iv_data)]
        self.ax.plot(extent, [intercept + slope * x for x in extent], 'r--')
        self.fig.tight_layout()
        self.canvas.draw()

        try: # because we don't know whether there's a grid to replace
          for f in self.stats:
            f.Destroy()
          self.dsp_box.Remove(self.stats_box)
        except:
          pass
        self.stats = []
        self.stats_box = wx.BoxSizer(wx.VERTICAL)
        self.dsp_box.Add(self.stats_box)
        self.stats_box.AddSpacer(20)
        self.stats.append(wx.StaticText(self, -1, 'r^2 = {:.4f}'.format(r2)))
        self.stats_box.Add(self.stats[-1], flag=wx.LEFT, border=10)
        self.stats.append(wx.StaticText(self, -1, 'slope = {:.4f}'.format(slope)))
        self.stats_box.Add(self.stats[-1], flag=wx.LEFT, border=10)
        self.stats.append(wx.StaticText(self, -1, 'y-intercept = {:.4f}'.format(intercept)))
        self.stats_box.Add(self.stats[-1], flag=wx.LEFT|wx.BOTTOM, border=10)
        self.panel.Layout()

    def doPlot(self, event):
        try:
            iv = self.iv_chooser.GetString(self.iv_chooser.GetSelection())
            dv = self.dv_chooser.GetString(self.dv_chooser.GetSelection())
            if iv != '-' and dv != '-' and iv != dv:
                try:
                    iv_data = self.getData(iv, self.data)
                    dv_data = self.getData(dv, self.data)
                    if iv_data is not None and dv_data is not None:
                        self.plotLinReg(iv=[iv]+iv_data, dv=[dv]+dv_data)
                except Exception as ex:
                    print(ex)
        finally:
            event.Skip() # pass to next handler

    def onClose(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
