

import wx


class DraggableValue(wx.Window):

	def __init__(self, parent, id, value, per_px):
		super.__init__(parent, id)

		self.value = value
		self.per_px = per_px

		# Todo: implement