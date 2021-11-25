import struct
from RTTrPM import rttrp
import socket
from collections import deque


def filter_packet(data, int_sig, float_sig):
    trackable = centroid = quaternon = euler = centroid_acc_vel = None
    timestamp = num_mods = None
    big = ''
    led = led_acc_vel = []
    pkt_type = data[0]
    # trackable
    if hex(int_sig) == '0x4154':
        # big endian
        big = '!'
    size, name_len = struct.unpack(f"{big}HB", data[1:4])
    num_chars = big + ''.join([f"c" for x in range(name_len)])
    name = ''.join([x.decode() for x in struct.unpack(num_chars, data[4:name_len+4])])
    timestamp = None
    if pkt_type == 1:
        num_mods = struct.unpack(f"{big}B", data[name_len+4:name_len+5])[0]
        data = data[name_len + 5:]
    elif pkt_type == 81:
        timestamp = struct.unpack(f"{big}I", data[name_len+4:name_len+8])[0]
        num_mods = struct.unpack(f"{big}B", data[name_len + 8:name_len+9])[0]
        data = data[name_len+9:]
    trackable = {
        'pkt_type': pkt_type,
        'size': size,
        'name': name,
        'num_mods': num_mods
    }
    if timestamp:
        trackable['timestamp'] = timestamp
    # print('trackable', trackable)

    # centroid
    i_big = f_big = ""
    if data[0] != 2:
        raise ValueError(data[0])
    if int_sig == "0x4154":
        i_big = "!"
    c_size, c_latency = struct.unpack(f"{i_big}HH", data[1:5])
    if float_sig == "0x4334":
        f_big = "!"
    x, y, z = struct.unpack(f"{f_big}ddd", data[5:c_size])
    # x, y, z = [data[5+i:5+i+8] for i in range(0, 24, 8)]
    centroid = {
        'pkt_type': data[0],
        # 'data': data[:30],
        'size': c_size,
        'latency': c_latency,
        'x': x,
        'y': y,
        'z': z
    }
    return x, y, z
    # data = data[size:]
    # print('centroid', centroid)


def rttrpm_to_freed(pos):
    # rttrpm = meters vs freed = 1/64th mm
    arr = [0]*3
    r = int(pos * 1000 * 64)
    arr[0] = r & 0x00ff
    arr[1] = r >> 8 & 0x00ff
    arr[2] = r >> 16 & 0x00ff
    return b''.join([x.to_bytes(1, 'big') for x in arr])


queue = deque([], maxlen=1)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', 24100))


def recv():
    try:
        data = sock.recv(65535)
    except KeyboardInterrupt:
        sock.close()
    else:
        r = rttrp.RTTrP(data)
        position = filter_packet(r.data, r.intHeader, r.fltHeader)
        freed_pos = b''.join(rttrpm_to_freed(x) for x in position)
        queue.append(freed_pos)


def recv_loop(run):
    while run.is_set():
        recv()


if __name__ == '__main__':
    while True:
        recv()
        print(queue.pop())
