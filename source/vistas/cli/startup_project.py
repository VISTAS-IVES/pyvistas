import click
from vistas.cli import cli
from vistas.ui.app import App
import os


@cli.command(short_help='Start VISTAS with a predefined project loaded.')
@click.argument('project', type=click.Path(exists=True))
def startup_project(project):
    source_dir = os.path.abspath(__file__)
    for _ in range(3):  # Move working directory up 3 directories to allow App to detect builtin plugins
        source_dir = os.path.dirname(source_dir)
    os.chdir(source_dir)
    App.startup_project = project
    App.get().MainLoop()
