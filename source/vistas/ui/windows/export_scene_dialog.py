from vistas.core.export import ExportItem
from vistas.ui.controls.gl_canvas import GLCanvas
from vistas.core.utils import get_platform

import wx
from wx.glcanvas import WX_GL_RGBA, WX_GL_DOUBLEBUFFER, WX_GL_DEPTH_SIZE, WX_GL_CORE_PROFILE


class ExportSceneDialog(wx.Dialog):

    def __init__(self, parent, id, item: ExportItem):
        super().__init__(parent, id, "", style=wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CLIP_CHILDREN | wx.CAPTION)

        if item.item_type != ExportItem.SCENE:
            raise ValueError("item_type is not ExportItem.SCENE")

        self.scene_item = item

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # GLCanvas setup
        attrib_list = [WX_GL_RGBA, WX_GL_DOUBLEBUFFER, WX_GL_DEPTH_SIZE, 16]
        if get_platform() == 'macos':
            attrib_list += [WX_GL_CORE_PROFILE]

        self.gl_canvas = GLCanvas(self, wx.ID_ANY, self.scene_item.camera, attrib_list=attrib_list)
        self.gl_canvas.Refresh()
        self.gl_canvas.SetSize(wx.Size(*self.scene_item.size))
        sizer.Add(self.gl_canvas, 1, wx.EXPAND)

        self.SetSize(self.gl_canvas.GetSize())
        self.CenterOnParent()
        self.SetTitle(title="Scene Configurator {}".format(self.scene_item.camera.scene.name))
        self.Bind(wx.EVT_CLOSE, self.OnExportSceneClose)

    def OnExportSceneClose(self, event: wx.CloseEvent):
        export_canvas = self.GetParent()
        self.scene_item.refresh_cache()
        export_canvas.RefreshItemCache(self.scene_item)
        export_canvas.Refresh()
        self.Destroy()
