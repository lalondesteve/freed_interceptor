import socket
from concurrent.futures import ThreadPoolExecutor


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
