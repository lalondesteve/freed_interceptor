#!/bin/env python3
import threading
from time import sleep
from freed import FreeDSender, FreeDReceiver, FreedInterceptor
import RTTrPM


def freed_forward(recv_port, destinations):
    run = threading.Event()
    receiver = FreeDReceiver(recv_port)
    run.set()
    recv_thread = threading.Thread(None, receiver.receive, None, (run,))
    sender = FreeDSender(destinations, receiver.queue)
    send_thread = threading.Thread(None, sender.send, None, (run,))
    recv_thread.start()
    send_thread.start()
    return run


def freed_intercept(recv_port, destinations):
    run = threading.Event()
    receiver = FreeDReceiver(recv_port)
    run.set()
    interceptor = FreedInterceptor(RTTrPM.queue)
    rttrpm_thread = threading.Thread(None, RTTrPM.recv_loop, None, (run,))
    recv_thread = threading.Thread(None, receiver.receive, None, (run,))
    sender = FreeDSender(destinations, receiver.queue, interceptor)
    send_thread = threading.Thread(None, sender.send, None, (run,))
    rttrpm_thread.start()
    recv_thread.start()
    send_thread.start()
    return run


if __name__ == '__main__':
    recv_port = 1113
    send_ip = '10.200.1.107'
    send_port = 12345
    # run = freed_forward(recv_port, [(send_ip, send_port)])
    run = freed_intercept(recv_port, [(send_ip, send_port)])
    while run.is_set():
        try:
            sleep(.25)
        except KeyboardInterrupt:
            run.clear()
            print('KeyboardInterrupt')
        except Exception as e:
            print(e)
            run.clear()
