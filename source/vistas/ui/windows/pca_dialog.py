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


class PcaDialog(wx.Dialog):
    def __init__(self, parent=None):
        super().__init__(parent, size=(800,600))
        self.parent = parent
        self.panel = wx.Panel(self)
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.ctl_box = wx.BoxSizer(wx.VERTICAL)
        self.ctl_box.Add(wx.StaticText(self.panel, -1, 'Variables:'), flag=wx.TOP|wx.LEFT|wx.RIGHT, border=20)
        self.data = Project.get().all_data
        self.chooser = wx.ListBox(self.panel, choices=[n.data.data_name for n in self.data],
          style=wx.LB_EXTENDED)
        self.ctl_box.Add(self.chooser, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM, border=20)

        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        plot_button = wx.Button(self.panel, wx.ID_OK, label='Plot')
        plot_button.Bind(wx.EVT_BUTTON, self.onPlotButton)
        btn_box.Add(plot_button, flag=wx.ALL, border=15)
        dismiss_button = wx.Button(self.panel, wx.ID_OK, label='Dismiss')
        dismiss_button.Bind(wx.EVT_BUTTON, self.onClose)
        btn_box.Add(dismiss_button, flag=wx.ALL, border=15)
        self.ctl_box.Add(btn_box)
        box.Add(self.ctl_box)

        self.dsp_box = wx.BoxSizer(wx.VERTICAL)
        self.fig = mpl.figure.Figure()
        self.canvas = wxagg.FigureCanvasWxAgg(self.panel, -1, self.fig)
        self.dsp_box.Add(self.canvas, 1, wx.GROW)
        box.Add(self.dsp_box)
        self.panel.SetSizer(box)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.CenterOnParent()
        self.panel.Layout()
        self.Show()

    def getData(self, chooser, data):
        ret = {}
        if len(chooser.GetSelections()) < 2:
            wx.MessageDialog(self.panel, 'PCA requires at least two', 'Not enough variables', wx.OK).ShowModal()
            return
        for sel in chooser.GetSelections():
            data_name = chooser.GetString(sel)
            for node in data:
                if node.data.data_name == data_name:
                  print(node, node.data)
                  print(node.data.variables)
                  date = None
                  if node.data.time_info.timestamps:
                      time_index = Timeline.app().current_index
                      date = node.data.time_info.timestamps[time_index]
                  ret[data_name] = node.data.get_data(node.data.variables[0], date=date)
                  break
        return ret

    def plotPCA(self, data=None):
        try:
          self.fig.delaxes(self.ax)
        except:
          pass
        self.ax = self.fig.add_subplot(111)
        self.ax.grid()

        # normalize and reorganize data
        n_vars = len(data)
        var_names = list(data)
        print(var_names)
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
        print('x_data.shape = ', x_data.shape)

        # calculate pca
        pca = skd.PCA()
        model = pca.fit(x_data)
        tx_data = pca.transform(x_data)
        # plot first two components
        self.ax.set_xlabel('Component 1')
        self.ax.set_ylabel('Component 2')
        # adjust marker size and alpha based on how many points we're plotting
        marker_size = mpl.rcParams['lines.markersize'] ** 2
        marker_size *= min(1, max(.12, 200 / len(tx_data[:,0])))
        alpha = min(1, max(.002, 500 / len(tx_data[:,0])))
        self.ax.scatter(tx_data[:,0], tx_data[:,1], s=marker_size, c='b', alpha=alpha)

        # plot axes
        color = ['g', 'c', 'm', 'k', 'y']
        for n in range(n_vars):
            adata = np.zeros([2, n_vars])
            adata[0, n] = ma.min(x_data[:, n])
            adata[1, n] = ma.max(x_data[:, n])
            xf = pca.transform(adata)
            self.ax.plot([xf[0,0], xf[0,1]], [xf[1,0], xf[1,1]], color[n % len(color)] + '-')
            self.ax.text(xf[0,0], xf[1,0], var_names[n], color=color[n % len(color)])

        # show stats in grid
        try:
          self.grid.Destroy()
        except:
          pass
        self.grid = wx.grid.Grid(self, -1)
        self.grid.CreateGrid(n_vars, n_vars+1) # extra column for explained variance
        grid_labels = ['Expl. var.'] + var_names
        grid_data = np.concatenate(
          (np.expand_dims(pca.explained_variance_ratio_, axis=1), pca.components_),
          axis=1)
        # cell_width = max([wx.ScreenDC().GetTextExtent(v)[0] for v in grid_labels])
        # cell_width = min(cell_width, 100)
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
        # might need a sizer here just to make it easy to delete
        self.dsp_box.Add(self.grid, flag=wx.ALL, border=10)
        self.panel.Layout()

    def onPlotButton(self, event): # only event we've got is a plot-button push
        v_data = self.getData(self.chooser, self.data)
        if v_data:
            plot = self.plotPCA(data=v_data)

    def onClose(self, event):
        self.Destroy()
