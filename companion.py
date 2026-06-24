#
# Interface to BitFocus Companion to trigger actions, like camera switching, based
# on Joystick/Controller controls
#
# For now we assume that:
# - Companion is running on the local machine - 127.0.0.1
# - The UDP API is configured on the default port (16759)
#
import socket
import time

class Companion:
    def __init__(self, host='127.0.0.1', port:int=16759):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.host = host

    def startup(self, host=None):
        # Set a custom variable at startup to trigger load of camera names etc
        value = time.time()
        buffer = f'CUSTOM-VARIABLE VISCAControllerRestart SET-VALUE {value}'
        if host is None:
            host = self.host
        address = (host, self.port)
        try:
            self.socket.sendto(buffer.encode('utf-8'), address)
        except OSError:
            print("companion send failed")

    def pushbutton(self,  page:int, row:int, column:int, host=None):
        buffer = f"LOCATION {page}/{row}/{column} PRESS"
        if host is None:
            host = self.host
        address = (host, self.port)
        try:
            self.socket.sendto(buffer.encode('utf-8'), address)
        except OSError:
            print("companion send failed")

    def t_bar(self, value, host=None):
        """ Set a value for a t-bar custom variable """
        buffer = f'CUSTOM-VARIABLE tbar_value SET-VALUE {value}'
        if host is None:
            host = self.host
        address = (host, self.port)
        try:
            self.socket.sendto(buffer.encode('utf-8'), address)
        except OSError:
            print("companion send failed")




