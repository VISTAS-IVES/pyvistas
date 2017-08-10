import platform
import sys
import matplotlib

if platform.uname().system == 'Windows':
    matplotlib.use('AGG')

# Check for command line arguments
if len(sys.argv) > 1:
    from vistas.cli.main import cli
    cli()

# Main app
else:
    from vistas.ui.app import App
    app = App.get()
    app.MainLoop()
