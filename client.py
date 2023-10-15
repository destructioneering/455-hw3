#!/usr/bin/env python

import socket
import json
import time
import hashlib
import re
import base64
import os
import sys

from datetime import datetime
from threading import Thread
from curses import wrapper
from curses.textpad import Textbox
import curses

lines = []

def show_lines(stdscr):
    global lines

    if len(lines) > curses.LINES - 2:
        lines = lines[1:]

    y = 0
    my, mx = stdscr.getyx()

    for line in lines:
        stdscr.addstr(y, 0, ' ' * (curses.COLS - 1))
        a = datetime.utcfromtimestamp(line['time']).strftime('[%H:%M:%S] <')
        stdscr.addstr(y, 0, a)
        stdscr.addstr(y, len(a), line['nick'], curses.color_pair(int(hashlib.md5(bytes(line['nick'], 'utf-8')).hexdigest(), 16) % (256 - 7) + 7))
        stdscr.addstr(y, len(a) + len(line['nick']), f'> {line["message"]}')
        y += 1

    stdscr.move(my, mx)
    stdscr.refresh()

def connection_handler(s, stdscr):
    while True:
        data = s.recv(4)
        length = data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3]
        line = s.recv(length)
        while len(line) != length:
            line += s.recv(length - len(line))
        data = json.loads(line.decode())

        global lines

        if data['method'] == 'message':
            lines.append(data)
            show_lines(stdscr)
        elif data['method'] == 'file':
            lines.append({ 'nick': 'system', 'time': time.time(), 'message': f'Received file `{data["filename"]}`' })
            show_lines(stdscr)
            try:
                with open(data['filename'], 'xb') as f:
                    f.write(base64.b64decode(data['file']))
            except:
                pass

def main(stdscr):
    stdscr.clear()
    curses.use_default_colors()

    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)

    curses.curs_set(2)

    editwin = curses.newwin(1, curses.COLS - 1, curses.LINES - 1, 0)
    box = Textbox(editwin)
    box.edit()
    nick = box.gather()
    nick = nick[:-1]
    prefix = f'<{nick}> '
    editwin = curses.newwin(1, curses.COLS - 1 - len(prefix), curses.LINES - 1, len(prefix))
    box = Textbox(editwin)
    stdscr.addstr(curses.LINES - 1, 0, f'<{nick}> ')
    stdscr.addstr(curses.LINES - 2, 0, ' ' * (curses.COLS - 1), curses.A_REVERSE)

    stdscr.refresh()
    s = socket.socket()
    port = 8080
    s.connect(('localhost', port))

    thread = Thread(target=connection_handler, daemon=True, args=(s, stdscr))
    thread.start()

    while True:
        editwin.erase()
        box.edit()
        message = box.gather()
        stdscr.move(curses.LINES - 1, len(prefix))
        stdscr.refresh()

        data = { 'method': 'message', 'time': time.time(), 'nick': nick, 'message': message }

        match = re.match(r'^/exit\s*$', message)

        if match:
            sys.exit()

        match = re.match(r'^/send (.*?)\s*$', message)

        if match:
            filename = match.group(1)
            lines.append({ 'nick': 'system', 'time': time.time(), 'message': f'Uploading file `{filename}`' })
            show_lines(stdscr)
            with open(filename, 'rb') as f:
                encoded = base64.b64encode(f.read())
            data = { 'method': 'file', 'time': time.time(), 'nick': nick, 'filename': filename, 'file': encoded.decode('utf-8') }

        buf = bytes(json.dumps(data), 'utf-8')
        buf_len = len(buf)
        s.send(bytes([(buf_len & 0xFF000000) >> 24, (buf_len & 0xFF0000) >> 16, (buf_len & 0xFF00) >> 8, buf_len & 0xFF]) + buf)

    thread.join()

    s.close()

wrapper(main)
