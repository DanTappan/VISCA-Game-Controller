#
# Find paths to local files
from os import path

def file_path(f):
    return path.abspath(path.join(path.dirname(__file__), f))

def controller_icon():
    return file_path('VISCA-Game-Controller.png')

