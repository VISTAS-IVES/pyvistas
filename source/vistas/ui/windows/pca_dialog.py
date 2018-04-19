import wx

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
        super().__init__(parent, wx.ID_ANY, 'PCA', size=(800,600))
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddSpacer(5)
        self.panel.SetSizer(self.sizer)
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(top_sizer, 0)
        ctl_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(ctl_sizer, 0)
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Variables:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=20)

        self.data = Project.get().all_data
        data_choices = [n.data.data_name for n in self.data]

        self.chooser = wx.ListBox(self.panel, choices=data_choices, style=wx.LB_EXTENDED)
        ctl_sizer.Add(self.chooser, 0, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM, border=20)

        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Plot type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.plot_type = wx.RadioBox(self.panel, choices=['scatterplot', 'heatmap'])
        ctl_sizer.Add(self.plot_type, flag=wx.LEFT|wx.RIGHT, border=10)
        ctl_sizer.Add(wx.StaticText(self.panel, -1, 'Axis type:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=12)
        self.axis_type = wx.RadioBox(self.panel, choices=['fixed', 'adaptive'])
        ctl_sizer.Add(self.axis_type, flag=wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_RADIOBOX, self.doPlot)


        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)
        top_sizer.Add(self.canvas, 1, wx.EXPAND)
        self.Bind(wx.EVT_LISTBOX, self.doPlot)
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
        date = Timeline.app().current
        thisdata = node.data.get_data(node.data.variables[0], date=date)
        return thisdata

    def plotPCA(self, data=None):
        try:
          self.fig.delaxes(self.ax)
        except:
          pass

        # normalize and reorganize data
        n_vars = len(data)
        var_names = list(data)
        x_data = data.values() # guaranteed, per python docs, to be same order
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

        # plot first two components
        self.ax = self.fig.add_subplot(111)
        self.ax.grid()
        self.ax.set_xlabel('Component 1')
        self.ax.set_ylabel('Component 2')

        axis_type = self.axis_type.GetString(self.axis_type.GetSelection())
        if axis_type == 'fixed':
            self.ax.set_xlim(-3, 3)
            self.ax.set_ylim(-3, 3)

        plot_type = self.plot_type.GetString(self.plot_type.GetSelection())
        if plot_type == 'scatterplot':
            # adjust marker size and alpha based on # of points
            marker_size = mpl.rcParams['lines.markersize'] ** 2
            marker_size *= min(1, max(.12, 200 / len(tx_data[:,0])))
            alpha = min(1, max(.002, 500 / len(tx_data[:,0])))
            self.ax.scatter(tx_data[:,0], tx_data[:,1], s=marker_size, c='b', alpha=alpha)
        else: # heatmap
            bins = 200
            heatmap, x_edges, y_edges = np.histogram2d(tx_data[:,0], tx_data[:,1], bins=bins)
            x_min, x_max = x_edges[0], x_edges[-1]
            y_min, y_max = y_edges[0], y_edges[-1]
            self.ax.imshow(np.log(heatmap.transpose() + 1), extent=[x_min, x_max, y_min, y_max], cmap='Blues', origin='lower', aspect='auto')

        # plot axes
        color = ['g', 'c', 'm', 'k', 'y']
        for n in range(n_vars):
            adata = np.zeros([2, n_vars])
            adata[0, n] = ma.min(x_data[:, n])
            adata[1, n] = ma.max(x_data[:, n])
            xf = pca.transform(adata)
            self.ax.plot([xf[0,0], xf[0,1]], [xf[1,0], xf[1,1]], color[n % len(color)] + '-')
            self.ax.text(xf[0,0], xf[1,0], var_names[n], color=color[n % len(color)])
        self.fig.tight_layout()

        # show stats in grid
        try:
          self.grid.Destroy()
        except:
          pass
        self.grid = wx.grid.Grid(self.panel, -1)
        self.grid.CreateGrid(n_vars, n_vars+1) # extra column for explained variance
        grid_labels = ['Expl. var.'] + var_names
        grid_data = np.concatenate(
          (np.expand_dims(pca.explained_variance_ratio_, axis=1), pca.components_),
          axis=1)
        # Should we try to set cell width?
        # cell_width = max([wx.ScreenDC().GetTextExtent(v)[0] for v in grid_labels])
        for v in range(len(grid_labels)):
          self.grid.SetColLabelValue(v, grid_labels[v])
          # grid.SetColSize(v, cell_width+8)
          self.grid.SetColFormatFloat(v, 6, 3)
        vc = wx.ColourDatabase().Find('Light Blue')
        for row in range(n_vars):
          self.grid.SetCellBackgroundColour(row, 0, vc)
          for col in range(len(grid_labels)):
            self.grid.SetCellValue(row, col, str(grid_data[row, col]))
            self.grid.SetReadOnly(row, col)
        self.grid.AutoSize()
        self.sizer.Add(self.grid, 2, flag=wx.EXPAND|wx.ALL, border=10)
        self.panel.Layout()

    def doPlot(self, event):
        try: # because we want to insure that we can pass to next handler
            selections = self.chooser.GetSelections()
            if len(selections) >= 2:
                v_data = {}
                for sel in selections:
                    dname = self.chooser.GetString(sel)
                    try:
                        thisdata = self.getData(dname, self.data)
                        if thisdata is not None:
                            v_data[dname] = thisdata
                    except Exception as ex:
                        print(ex)
                if len(v_data.keys()) >= 2:
                    plot = self.plotPCA(data=v_data)
        finally:
            event.Skip() # pass to next handler

    def onClose(self, event):
        get_main_window().Unbind(EVT_TIMELINE_CHANGED)
        self.Destroy()
