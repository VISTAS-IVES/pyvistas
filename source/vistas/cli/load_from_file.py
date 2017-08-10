import click
from vistas.cli import cli
from vistas.ui.app import App
import os


@cli.command(short_help='Start VISTAS with a predefined project loaded.')
@click.argument('project', type=click.Path(exists=True))
def load_from_file(project):
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # Todo - macOS equivalent?
    App.preload_save = project
    App.get().MainLoop()
