import platform
import sys

import matplotlib

from vistas.ui.app import App

if platform.uname().system == 'Windows':
    matplotlib.use('AGG')

# Check for command line arguments
if len(sys.argv) > 1:
    from vistas.cli.main import cli
    cli()

# Main app
else:
    app = App.get()
    app.MainLoop()
