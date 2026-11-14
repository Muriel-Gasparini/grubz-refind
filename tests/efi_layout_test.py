#!/usr/bin/env python3
"""Validate the built PE/COFF SBAT layout used by shim memory protection."""
import struct
import sys
from pathlib import Path

b = Path(sys.argv[1]).read_bytes()
pe = struct.unpack_from('<I', b, 0x3c)[0]
assert b[pe:pe+4] == b'PE\0\0', 'Not a PE binary'
count = struct.unpack_from('<H', b, pe+6)[0]
table = pe+24+struct.unpack_from('<H', b, pe+20)[0]
sections = []
for i in range(count):
    off = table+i*40
    name = b[off:off+8].rstrip(b'\0')
    virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', b, off+8)
    sections.append((name, rva, max(virtual_size, raw_size), raw, raw_size))
sbat = [s for s in sections if s[0] == b'.sbat']
assert len(sbat) == 1, 'Expected one SBAT section'
_, rva, size, raw, raw_size = sbat[0]
assert rva % 4096 == 0, f'SBAT RVA {rva:#x} is not page aligned'
assert size > 0 and raw+raw_size <= len(b), 'Invalid SBAT contents'
assert b'sbat,1,' in b[raw:raw+raw_size] and b'refind.grubz,' in b[raw:raw+raw_size]
end = (rva+size+4095) & ~4095
for name, other, length, _, _ in sections:
    if name != b'.sbat':
        assert other+length <= rva or other >= end, f'SBAT protection overlaps {name!r}'
print(f'EFI layout passed: SBAT RVA {rva:#x}, isolated page-aligned section')
