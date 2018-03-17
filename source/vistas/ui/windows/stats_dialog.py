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
        self.panel = wx.Panel(self)
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.ctl_box = wx.BoxSizer(wx.VERTICAL)
        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Independent variable(s):'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.data = Project.get().all_data
        self.iv_chooser = wx.Choice(self.panel, choices=['-'] + [n.data.data_name for n in self.data])
        self.ctl_box.Add(self.iv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)
        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Dependent variable'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.dv_chooser = wx.Choice(self.panel, choices=['-'] + [n.data.data_name for n in self.data])
        self.ctl_box.Add(self.dv_chooser, flag=wx.LEFT|wx.RIGHT, border=12)
        # self.plot_box = wx.RadioBox(self.panel, choices=['scatterplot', 'heatmap', 'no plot'])
        # self.ctl_box.Add(self.plot_box, flag=wx.LEFT|wx.RIGHT, border=12)
        # btn_box = wx.BoxSizer(wx.HORIZONTAL)
        # plot_button = wx.Button(self.panel, wx.ID_OK, label='Plot')
        # plot_button.Bind(wx.EVT_BUTTON, self.onPlotButton)
        # btn_box.Add(plot_button, flag=wx.ALL, border=15)
        # dismiss_button = wx.Button(self.panel, wx.ID_OK, label='Dismiss')
        # dismiss_button.Bind(wx.EVT_BUTTON, self.onClose)
        # btn_box.Add(dismiss_button, flag=wx.ALL, border=15)
        # self.ctl_box.Add(btn_box)
        self.Bind(wx.EVT_CHOICE, self.onPlotButton)
        box.Add(self.ctl_box)

        self.dsp_box = wx.BoxSizer(wx.VERTICAL)
        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)
        self.dsp_box.Add(self.canvas, 1, wx.GROW)
        box.Add(self.dsp_box)
        self.panel.SetSizer(box)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        get_main_window().Bind(EVT_TIMELINE_CHANGED, self.onPlotButton)
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    def getData(self, dname, data):
        for node in data:
          if node.data.data_name == dname:
            date = None
            if node.data.time_info.timestamps:
              time_index = Timeline.app().current_index
              date = node.data.time_info.timestamps[time_index]
              thisdata = node.data.get_data(node.data.variables[0], date=date)
              thisdata = ma.where(thisdata == node.data._nodata_value, ma.masked, thisdata)
            return {'name': dname, 'data': thisdata}
        return None

    def plotLinReg(self, iv_data=None, dv_data=None):
        try:
          self.fig.delaxes(self.ax)
        except:
          pass
        self.ax = self.fig.add_subplot(111)
        self.ax.grid()
        self.ax.set_xlabel(iv_data['name'])
        self.ax.set_ylabel(dv_data['name'])
    
        iv_datax = iv_data['data']
        dv_datax = dv_data['data']
        
        # synchronize masks
        mask = np.logical_or(ma.array(iv_datax).mask, ma.array(dv_datax).mask)
        iv_datax = ma.array(iv_datax, mask=mask).compressed()
        dv_datax = ma.array(dv_datax, mask=mask).compressed()
    
        # adjust marker size and alpha based on how many points we're plotting
        marker_size = mpl.rcParams['lines.markersize'] ** 2
        marker_size *= min(1, max(.12, 200 / len(iv_datax)))
        alpha = min(1, max(.002, 500 / len(iv_datax)))
        self.ax.scatter(iv_datax, dv_datax, s=marker_size, alpha=alpha)
    
        # calculate regression
        ols = lm.LinearRegression()
        ols.fit(iv_datax.reshape(-1,1), dv_datax.reshape(-1,1))
        r2 = ols.score(iv_datax.reshape(-1,1), dv_datax.reshape(-1,1))
    
        # predict some values to get slope and intercept
        res = ols.predict(np.array([0,1]).reshape(-1,1))
        intercept = res[0][0]
        slope = res[1][0] - intercept
    
        extent = [ma.min(iv_datax), ma.max(iv_datax)]
        self.ax.plot(extent, [intercept + slope * x for x in extent], 'r--')
        self.canvas.draw()

        try:
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

    def onPlotButton(self, event):
        iv = self.iv_chooser.GetString(self.iv_chooser.GetSelection())
        dv = self.dv_chooser.GetString(self.dv_chooser.GetSelection())
        if iv == '-' or dv == '-' or iv == dv:
            return
        try:
            iv_data = self.getData(iv, self.data)
            dv_data = self.getData(dv, self.data)
            if iv_data and dv_data:
                self.plotLinReg(iv_data=iv_data, dv_data=dv_data)
        except:
            pass
        event.Skip() # pass to next handler

    def onClose(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
