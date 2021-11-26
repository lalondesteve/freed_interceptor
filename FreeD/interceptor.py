
class FreeDInterceptor:
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