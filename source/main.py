import platform

import matplotlib

if platform.uname().system == 'Windows':
    matplotlib.use('AGG')

from vistas.ui.app import App

app = App.get()
app.MainLoop()
