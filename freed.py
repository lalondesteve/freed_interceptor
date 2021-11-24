
import socket
from multiprocessing import Pipe
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from time import sleep


# FreeD packet size = 29
# 0 = 0xD1 (delimiter)
# 1 = ID
# 2 - 25 = data 3 bytes * 8 params (pan,tilt,roll,x,y,z,zoom,focus)
# 26 + 27 = spare
# 28 = 0 pad / checksum
# zoom + focus = 1365 to 4095 int
# pan, tilt = -175...+175


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


class FreeDSender:
    def __init__(self, destinations, r_queue, interceptor=None):
        self.destinations = destinations
        self.queue = r_queue
        self.interceptor = interceptor
        if self.interceptor:
            print('interceptor: ', interceptor)
        self.threadpool = ThreadPoolExecutor(max_workers=len(self.destinations))
        self.sockets = []
        for d in self.destinations:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('', 0))
            s.connect(d)
            self.sockets.append(s)

    def send(self, run):
        with self.threadpool as executor:
            while run.is_set():
                data = self.queue.recv_bytes()
                if self.interceptor:
                    data = self.interceptor.position(data)
                try:
                    _ = {executor.submit(s.send, data): s for s in self.sockets}
                except Exception as e:
                    print(e)
                    break


class FreedInterceptor:
    def __init__(self, queue):
        self.queue = queue
        self.last_values = 0

    def position(self, freed_data):
        try:
            values = self.queue.pop()
        except IndexError:
            values = self.last_values
        self.last_values = values
        values = b'\xff\xee\x0f'
        return freed_data[:11] + values + freed_data[20:]


class RTTrPMPosition:
    def __init__(self):
        self.queue = deque(self.get_position())

    def get_position(self):
        return []

    def scale_position(self, pos):
        pos = int(pos * 64)
        return pos.to_bytes(3, 'big')
