#
# OSC Interface for VISCA-Game-Controller
# Task which receives OSC messages and turns them into control
# messages
#
from typing import Optional
import threading
import PySimpleGUI as Sg
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from win_print import win_print
#from time import sleep

# Phil Rose: allow OSC /setcam to use camera names as well as numbers.
from config import cam_names, g_num_cams

OSC_Port = 9999

window : Optional[Sg.Window]  = None

def camera_handler(_address, *args):
    """ Dispatcher handler for setcam command """
    global window

    if len(args) == 0:
        win_print("OSC Set Camera: missing argument")
        return

    try:
        cam_num = int(args[0])
 
    except ValueError:
        # Phil Mod: allow /setcam "Lathe" or /setcam "Front"
        requested_name = str(args[0]).strip().lower()
        cam_num = None

        for i in range(g_num_cams):
            if cam_names[i].strip().lower() == requested_name:
                cam_num = i + 1
                break

        if cam_num is None:
            win_print(f"OSC Set Camera: unknown camera name '{args[0]}'")
            return

    window.write_event_value('OSC_SET_CAMERA', cam_num)

def camera_name_handler(_address, *args):
    """ Dispatcher handler for setcamname command
        arg1: camera number (str)
        arg2: camera name (str)
        """
    global window

    if len(args) < 2:
        win_print("OSC Set Camera Name: missing argument")
        return

    try:
        cam_num = int(args[0])
        if cam_num < 0 or cam_num > g_num_cams:
            cam_num = None
    except ValueError:
        cam_num = None

    if cam_num is None:
        win_print("OSC Set Camera Name: invalid camera number")
        return

    cam_name = args[1].replace('"', '') # in case the string came over with double quotes

    win_print(f"Set Camera {cam_num} Name: {cam_name}")
    window.write_event_value('OSC_SET_CAMERA_NAME', (cam_num, cam_name))

def clear_camera_handler(_address):
    """ Disable gamepad PTZ control when no camera is active. """
    global window
    window.write_event_value('OSC_CLEAR_CAMERA', None)


def osc_task(t):
    """
    Thread to run
    """
    t.server.serve_forever()


class OSCTask:
    def osc_task(self):
        """
        Thread to run
        """
        self.server.timeout = .5
        self.server.serve_forever()

    def __init__(self, win : Sg.Window):
        global window

        window = win

        self.dispatcher = Dispatcher()
        self.dispatcher.map("/setcam", camera_handler)
        self.dispatcher.map("/clearcam", clear_camera_handler)
        self.dispatcher.map("/setcamname", camera_name_handler)
        self.server = BlockingOSCUDPServer(('127.0.0.1',
                                            OSC_Port),
                                           dispatcher=self.dispatcher)
        self.thread = threading.Thread(target=self.osc_task)
        self.thread.daemon = True
        self.thread.start()

    def shutdown(self):
        self.server.shutdown()
        self.thread.join()
