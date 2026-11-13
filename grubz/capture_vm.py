#!/usr/bin/env python3
"""Record real QEMU framebuffer transitions via its local QMP API.
Usage: capture_vm.py SOCKET OUTPUT_DIRECTORY
Starts with Debian selected. Only sends arrow keys to the VM.
"""
import json
import socket
import sys
import time
from pathlib import Path

out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
with socket.socket(socket.AF_UNIX) as connection:
    connection.settimeout(10)
    connection.connect(sys.argv[1])
    stream = connection.makefile('rwb', buffering=0)
    json.loads(stream.readline())

    def command(name, arguments=None):
        message = {'execute': name, 'arguments': arguments or {}}
        stream.write((json.dumps(message) + '\n').encode())
        while True:
            result = json.loads(stream.readline())
            if 'error' in result:
                raise RuntimeError(result['error'])
            if 'return' in result:
                return result['return']

    command('qmp_capabilities')
    schedule = ([(0.4, 'right'), (0.43, 'ret')] if '--interrupt' in sys.argv else
                [(0.4, 'right'), (1.4, 'left'), (2.4, 'right'), (3.4, 'left')])
    frames = []
    start = time.monotonic()
    while time.monotonic() - start < 4.4:
        elapsed = time.monotonic() - start
        if schedule and elapsed >= schedule[0][0]:
            _, key = schedule.pop(0)
            command('send-key', {'keys': [{'type': 'qcode', 'data': key}], 'hold-time': 20})
        path = out / f'frame-{len(frames):04d}.ppm'
        command('screendump', {'filename': str(path)})
        frames.append({'file': path.name, 'seconds': time.monotonic() - start})
        time.sleep(0.015)
    (out / 'frames.json').write_text(json.dumps(frames, indent=2))
    print(f'{len(frames)} real framebuffer samples in {frames[-1]["seconds"]:.2f}s')
