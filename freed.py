
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
# checksum = 0x40 - sum(packet) &0xff


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
                # print('sent data: ', data)
                try:
                    _ = {executor.submit(s.send, data): s for s in self.sockets}
                except Exception as e:
                    print(e)
                    break
        [s.close() for s in self.sockets]


class FreedInterceptor:
    def __init__(self, queue):
        self.queue = queue
        self.last_values = b'\x00\x00\x00'*3

    def position(self, freed_data):
        try:
            values = self.queue.pop()
        except IndexError:
            values = self.last_values
        self.last_values = values
        data = freed_data[:11] + self.last_values + freed_data[20:]
        return self.freed_cs(data)

    @staticmethod
    def freed_cs(data):
        return data[:28] + ((0x40 - sum(data[:28]) & 0xff).to_bytes(1, 'big'))