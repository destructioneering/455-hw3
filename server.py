#!/usr/bin/env python

import os
import socket
import json
from threading import Thread

# TODO: Add a lock to make sure there are no conflicts.
threads = []
sockets = []

def broadcast(sockets, buf):
    for s in sockets:
        buf_len = len(buf)
        s.send(bytes([(buf_len & 0xFF000000) >> 24, (buf_len & 0xFF0000) >> 16, (buf_len & 0xFF00) >> 8, buf_len & 0xFF]))
        s.send(buf)

def connection_handler(conn, addr):
    global sockets
    print(f'Handling connection from {addr}')

    while True:
        data = conn.recv(4)
        if len(data) < 4: break
        length = data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3]
        line = conn.recv(length)
        while len(line) != length:
            line += conn.recv(length - len(line))
        data = json.loads(line.decode())
        print(json.dumps(data))

        if data['method'] == 'message':
            print(f'<{data["nick"]}> {data["message"]}')

        broadcast(sockets, line)

    sockets = list(filter(lambda x: x != conn, sockets))
    conn.close()

s = socket.socket()
host = 'localhost'
port = 8080
print(f'Listening at {host}:{port}')
s.bind((host, port))
s.listen(1)

while True:
    conn, addr = s.accept()
    thread = Thread(target=connection_handler, args=(conn, addr))
    thread.start()
    threads.append(thread)
    sockets.append(conn)

for thread in threads:
    thread.join()
