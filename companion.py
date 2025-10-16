#
# Interface to BitFocus Companion to trigger actions, like camera switching, based
# on Joystick/Controller controls
#
# For now we assume that:
# - Companion is running on the local machine - 127.0.0.1
# - The UDP API is configured on the default port (16759)
#
import socket

class Companion:
    def __init__(self,  port:int=16759):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port


    def pushbutton(self,  page:int, row:int, column:int, host='127.0.0.1'):
        buffer = f"LOCATION {page}/{row}/{column} PRESS"
        address = (host, self.port)
        try:
            self.socket.sendto(buffer.encode('utf-8'), address)
        except OSError:
            print("companion send failed")



