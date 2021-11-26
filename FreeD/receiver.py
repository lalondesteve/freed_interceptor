import socket
from multiprocessing import Pipe


class FreeDReceiver:
    def __init__(self, port):
        self.port = port
        self.buf = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))
        self.pipe, self.queue = Pipe()

    def receive(self, run):
        while run.is_set():
            data = self.sock.recv(65535)
            self.pipe.send_bytes(data)
        self.sock.close()