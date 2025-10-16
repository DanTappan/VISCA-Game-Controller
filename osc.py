#
# OSC Interface for VISCA-Game-Controller
# Task which receives OSC messages and turns them into control
# messages
#
from typing import Optional
import PySimpleGUI as Sg
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
OSC_Port = 9999

window : Optional[Sg.Window]  = None

def camera_handler(_address, *args):
    """ Dispatcher handler for setcam command """

    try:
        cam_num = int(args[0])
        window.write_event_value('OSC_SET_CAMERA', cam_num)

    except ValueError:
        print(f"OSC Set Camera: bad arguments {args}")

def osc_task(t):
    """
    Thread to run
    """
    t.server.serve_forever()


class OSCTask:
    def __init__(self, win : Sg.Window):
        global window

        window = win
        self.dispatcher = Dispatcher()
        self.dispatcher.map("/setcam", camera_handler)
        self.server = BlockingOSCUDPServer(('',
                                            OSC_Port),
                                           dispatcher=self.dispatcher)
        self.thread = win.start_thread(lambda: osc_task(self))
        pass

    def shutdown(self):
        self.server.shutdown()
        pass
