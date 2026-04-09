#
# Find paths to files
import os

local_app_data = os.getenv('LOCALAPPDATA')
app_data = os.getenv('APPDATA')

def localappdata_path(f : str) -> str:
    return os.path.abspath(os.path.join(local_app_data, "VISCA Game Controller", f))

def appdata_path(f : str) -> str:
    return os.path.abspath(os.path.join(app_data, "VISCA Game Controller", f))

def file_path(f : str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), f))

def search_path(f : str) -> str:
    for file in [localappdata_path(f), appdata_path(f), file_path(f)]:
        if os.access(file, os.R_OK):
            return file
    return None

def controller_icon():
    return file_path('VISCA-Game-Controller.png')

