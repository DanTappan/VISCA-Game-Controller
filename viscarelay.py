#
# Code to handle Relaying VISCA packets to the camera
#
#
import socket
import threading
import struct
import time

class ViscaRelay:
    def ptz_set(self, ptz: str, ptz_port:int):
        """ Set a new ptz destination """
        try:
            ptz_address = socket.gethostbyname(ptz)
            self.ptz_sockaddr = (ptz_address, ptz_port)
        except socket.gaierror:
            pass

    def relaythread(self):
        """ Loop:
            - receive packet
            - if packet camera sockaddr then it's from the camera -> Forward back to the last sockaddr
              seen from the controller
            - otherwise, forward to the current sockaddr for the camera
        """
        global last_relay

        s = self.socket
        self.recv_sockaddr = None

        while True:
            time.sleep(0.001)
            try:
                buffer, address = s.recvfrom(1024)
                if address == self.ptz_sockaddr:
                    # Packet is a response from the camera
                    dst_sockaddr = self.recv_sockaddr
                    # We don't clear the sockaddr here because it is possible to get multiple packets in response
                    # eg: CMD-> ACK, REPLY
                else:
                    # Packet is a (probably) from a controller. Save address for later reply
                    self.recv_sockaddr = address
                    # forward packet to the camera
                    dst_sockaddr = self.ptz_sockaddr

                if dst_sockaddr is not None:
                    s.sendto(buffer, dst_sockaddr)
            except ConnectionResetError:
                pass

            # Loop forever

    def __init__(self, rcv_port: int):
        """ Init:
            - create and bind socket for input.
            - create send sockaddr for sending to camera
            - create task to perform relay
            - packets to be relayed from controller will be from a random socket
            - response packets from camera will be from the camera's address and port
            - forward packets back to controller
        """
        self.rcv_port = rcv_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        address = ("", rcv_port)
        self.socket.bind(address)
        self.recv_sockaddr = None
        self.ptz_sockaddr = None
        self.thread = threading.Thread(target=self.relaythread)
        self.thread.daemon = True
        self.thread.start()
