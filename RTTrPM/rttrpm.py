import struct
try:
    from RTTrPM import rttrp
except:
    import rttrp
import socket
from collections import deque
from time import time

# TODO: Make this a class, this is a mess
# TODO: Filter by trackable name

class RTTrPMReceiver:
    def __init__(self, port, t_name=None, module_type='centroid'):
        # trackable name to filter later
        self.t_name = t_name
        self.module_type = module_type
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.queue = deque([], maxlen=1)
        self.trackable = self.t_data = None
        self.int_sig = ''
        self.flt_sig = ''

    def recv(self):
        try:
            data = self.sock.recv(65535)
        except Exception:
            pass
        else:
            if data:
                try:
                    self.trackable, self.t_data = self.get_trackable(data)
                except Exception as e:
                    print(e)
                    return
            if self.t_name and self.t_name != self.trackable['name']:
                return
            if not self.trackable['num_mods']:
                return
            modules = {}
            while self.t_data:
                module, self.t_data = self.get_modules(self.t_data)
                modules[module['type']] = module
            if self.module_type in modules:
                position = modules[self.module_type]['pos']
                freed_pos = b''.join(self.rttrpm_to_freed(x) for x in position)
                self.queue.append(freed_pos)
            else:
                return self.trackable, modules

    @staticmethod
    def rttrpm_to_freed(pos):
        # rttrpm = meters vs freed = 1/64th mm
        return (int(pos * 64000) & 0xffffff).to_bytes(3, 'big')

    def get_trackable(self, data):
        r = rttrp.RTTrP(data)
        if r.intHeader == 0x4154:
            self.int_sig = '!'
        else:
            self.int_sig = ''
        if r.fltHeader == 0x4334:
            self.flt_sig = '!'
        else:
            self.flt_sig = ''

        try:
            _type = r.data[0]
        except IndexError:
            return None

        size, name_len = struct.unpack(f"{self.int_sig}HB", r.data[1:4])
        num_chars = self.int_sig + "c" * name_len
        name = ''.join([x.decode() for x in struct.unpack(num_chars, r.data[4:name_len + 4])])
        timestamp = num_mods = None
        if _type == 1:
            num_mods = struct.unpack(f"{self.int_sig}B", r.data[name_len + 4:name_len + 5])[0]
            data = data[name_len + 5:]
        elif _type == 81:
            timestamp = struct.unpack(f"{self.int_sig}I", r.data[name_len + 4:name_len + 8])[0]
            num_mods = struct.unpack(f"{self.int_sig}B", r.data[name_len + 8:name_len + 9])[0]
            data = r.data[name_len + 9:]
        trackable = {
            'type': _type,
            'size': size,
            'name': name,
            'num_mods': num_mods
        }
        if timestamp:
            trackable['timestamp'] = timestamp
        # print('trackable', trackable)
        return trackable, data

    def get_modules(self, data):
        _type = _timestamp = _offset = None
        acceleration = False
        module = {}
        pos_bytes = f"{self.flt_sig}ddd"
        len_bytes = 3*8
        shift = 5
        module['size'], module['latency'] = struct.unpack(f"{self.int_sig}HH", data[1:5])
        if data[0] == 0x02:
            module['type'] = 'centroid'
            _offset = 29
        elif data[0] == 0x03:
            module['type'] = 'quaternion'
            pos_bytes = f"{self.flt_sig}dddd"
            len_bytes = 4*8
            _offset = 37
        elif data[0] == 0x04:
            module['type'] = 'euler'
            module['order'] = struct.unpack(f"{self.int_sig}H", data[6:8])[0]
            shift += 2
            _offset = 31
        elif data[0] == 0x06:
            module['type'] = 'LED'
            module['index'] = struct.unpack("B", data[29:30])[0]
            _offset = 30
        elif data[0] == 0x20:
            module['type'] = 'centroid_acceleration_velocity'
            module['latency'] = None
            acceleration = True
            shift += -3
            _offset = 51
        elif data[0] == 0x21:
            module['type'] = 'led accel vel'
            acceleration = True
            module['index'] = struct.unpack("B", data[51:52])[0]
            shift += -3
            _offset = 52
        x, y, z = struct.unpack(pos_bytes, data[shift:shift+len_bytes])
        if acceleration:
            ax, ay, az, vx, vy, vz = struct.unpack(f"{self.flt_sig}ffffff", data[27:51])
            module['acceleration'] = (ax, ay, az)
            module['velocity'] = (vx, vy, vz)
        module['pos'] = (x, y, z)
        return module, data[_offset:]

    def recv_loop(self, run):
        while run.is_set():
            self.recv()


def freed_to_float(data):
    # 24 bit to int
    r = ((data[0] << 16) | (data[1] << 8) | data[2]) - 0xffffff
    # int to signed
    if not r & 0x800000:
        return r & 0xffffff
    else:
        return r

if __name__ == '__main__':
    r = RTTrPMReceiver(24100)
    while True:
        try:
            r.recv()
            try:
                print(r.queue.pop())
            except IndexError:
                continue
        except KeyboardInterrupt:
            break