#!/usr/bin/env python3
"""QMP control for this isolated VM: state, keys, screenshot, stop."""
import argparse
import json
import socket
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "vm"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['status', 'key', 'screenshot', 'quit'])
parser.add_argument('value', nargs='?')
args = parser.parse_args()
with socket.socket(socket.AF_UNIX) as connection:
    connection.settimeout(10)
    connection.connect(str(ROOT / 'monitor.sock'))
    stream = connection.makefile('rwb', buffering=0)
    json.loads(stream.readline())

    def command(name, arguments=None):
        message = {'execute': name}
        if arguments is not None:
            message['arguments'] = arguments
        stream.write((json.dumps(message) + '\n').encode())
        while True:
            response = json.loads(stream.readline())
            if 'error' in response:
                raise RuntimeError(response['error'])
            if 'return' in response:
                return response['return']

    command('qmp_capabilities')
    if args.action == 'status':
        print(json.dumps(command('query-status')))
        print(json.dumps(command('query-block')))
    elif args.action == 'key':
        if args.value not in ['left', 'right', 'up', 'down', 'ret', 'esc']:
            parser.error('key must be left/right/up/down/ret/esc')
        print(command('send-key', {'keys': [{'type': 'qcode', 'data': args.value}]}))
        # QMP acknowledges before the default 100 ms key hold/release finishes.
        time.sleep(0.25)
    elif args.action == 'screenshot':
        filename = args.value or 'screen'
        if not filename.replace('-', '').replace('_', '').isalnum():
            parser.error('screenshot name must contain letters, numbers, hyphens or underscores')
        path = ROOT / 'evidence' / (filename + '.ppm')
        command('screendump', {'filename': str(path)})
        print(path)
    else:
        command('quit')
