#!/usr/bin/python3
"""Build and atomically publish a signed Debian UKI. Never changes NVRAM."""
import argparse
import fcntl
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


def run(*args):
    try:
        return subprocess.run([str(a) for a in args], check=True, text=True,
                              capture_output=True).stdout
    except subprocess.CalledProcessError as error:
        print(error.stderr, file=sys.stderr)
        raise


def latest_kernel(boot):
    versions = [p.name[8:] for p in Path(boot).glob('vmlinuz-*')
                if re.fullmatch(r'[0-9][A-Za-z0-9.+~-]*', p.name[8:])
                and p.stat().st_size and (Path(boot)/('initrd.img-'+p.name[8:])).is_file()]
    if not versions:
        raise RuntimeError('No complete kernel/initramfs pair')
    def compare(a, b):
        if a == b:
            return 0
        return -1 if subprocess.run(['dpkg','--compare-versions',a,'lt',b]).returncode == 0 else 1
    return sorted(versions, key=functools.cmp_to_key(compare))[-1]


def sections(path):
    data = Path(path).read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe+4] != b'PE\0\0':
        raise ValueError('Not PE/COFF')
    count = struct.unpack_from('<H', data, pe+6)[0]
    table = pe+24+struct.unpack_from('<H', data, pe+20)[0]
    result = {}
    for i in range(count):
        off = table+i*40
        name = data[off:off+8].rstrip(b'\0').decode()
        size, rva, rawsize, raw = struct.unpack_from('<IIII', data, off+8)
        if raw+rawsize > len(data) or name in result:
            raise ValueError('Invalid or duplicate PE section')
        result[name] = (rva, max(size, rawsize), data[raw:raw+min(size,rawsize)])
    return result


def build_uki(cfg, version, output):
    boot = Path(cfg['boot'])
    kernel = boot/('vmlinuz-'+version)
    initrd = boot/('initrd.img-'+version)
    stub = Path(cfg['stub'])
    key = Path(cfg['key'])
    if key.stat().st_mode & 0o077:
        raise RuntimeError('Private signing key must not be group/world accessible')
    cmdline = cfg['cmdline'].strip()
    if not cmdline or '\n' in cmdline or '\0' in cmdline or 'root=' not in cmdline:
        raise ValueError('Explicit single-line root command line required')
    # Bind the complete initramfs and command line into the signed artifact.
    with tempfile.TemporaryDirectory(dir=Path(output).parent) as tmp:
        tmp = Path(tmp)
        (tmp/'cmdline').write_bytes(cmdline.encode()+b'\0')
        (tmp/'uname').write_bytes(version.encode()+b'\0')
        payloads = {'.osrel':Path(cfg['os_release']), '.cmdline':tmp/'cmdline',
                    '.uname':tmp/'uname', '.linux':kernel, '.initrd':initrd}
        source = sections(stub)
        address = (max(rva+size for rva,size,_ in source.values())+4095)&~4095
        args = [cfg.get('objcopy','objcopy')]
        for name, path in payloads.items():
            if not path.stat().st_size:
                raise ValueError('Empty input: '+str(path))
            args += ['--add-section',f'{name}={path}', '--change-section-vma',f'{name}={address:#x}',
                     '--set-section-flags',f'{name}=contents,alloc,load,readonly,data']
            address = (address+path.stat().st_size+4095)&~4095
        unsigned = tmp/'unsigned.efi'
        run(*args, stub, unsigned)
        run(cfg.get('sbsign','sbsign'),'--key',key,'--cert',cfg['cert'],'--output',output,unsigned)
        run(cfg.get('sbverify','sbverify'),'--cert',cfg['cert'],output)
        built = sections(output)
        for name,path in payloads.items():
            if built[name][2] != path.read_bytes():
                raise RuntimeError('Embedded payload mismatch: '+name)


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def sync_file(path):
    with Path(path).open('rb') as f:
        os.fsync(f.fileno())


def publish(destination, builder, verifier):
    """All staging on destination filesystem; failure never replaces current."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.staging-',dir=destination) as tmp:
        candidate = Path(tmp)/'new.efi'
        builder(candidate)
        verifier(candidate)
        current = destination/'current.efi'
        if current.exists():
            verifier(current)
            if digest(current) == digest(candidate):
                return
            previous = Path(tmp)/'previous.efi'
            shutil.copyfile(current, previous)
            sync_file(previous)
            os.replace(previous, destination/'previous.efi')
        sync_file(candidate)
        os.replace(candidate, current)
        fd = os.open(destination,os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def update(cfg):
    esp = Path(cfg['esp']).resolve()
    mount = json.loads(run('findmnt','--json','--mountpoint',esp,'-o','TARGET,FSTYPE,UUID'))['filesystems'][0]
    if mount['target'] != str(esp) or mount['fstype'] != 'vfat' or mount['uuid'].lower() != cfg['esp_uuid'].lower():
        raise RuntimeError('Expected EFI partition is not mounted')
    boot = Path(cfg['boot'])
    version = latest_kernel(boot)
    needed = ((boot/('vmlinuz-'+version)).stat().st_size +
              (boot/('initrd.img-'+version)).stat().st_size + 2*1024*1024)
    # Candidate plus a rollback staging copy; do not remove a working image to fit.
    if shutil.disk_usage(esp).free < needed*2:
        raise RuntimeError('Insufficient EFI free space for safe staging')
    destination = esp/'EFI/grubz-linux'
    verifier = lambda p:run(cfg.get('sbverify','sbverify'),'--cert',cfg['cert'],p)
    publish(destination, lambda p:build_uki(cfg,version,p), verifier)
    print(json.dumps({'version':version,'path':str(destination/'current.efi'),
                      'sha256':digest(destination/'current.efi')}))


def main():
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='/etc/grubz-direct.json')
    parser.add_argument('--build-only',metavar='OUTPUT')
    parser.add_argument('--version')
    args = parser.parse_args()
    if os.geteuid() != 0 and not args.build_only:
        parser.error('Publishing requires root')
    config = Path(args.config)
    if not args.build_only and (config.stat().st_uid != 0 or config.stat().st_mode & 0o022):
        parser.error('Configuration must be root owned and not writable by others')
    cfg = json.loads(config.read_text())
    os.umask(0o077)
    if args.build_only:
        build_uki(cfg,args.version or latest_kernel(cfg['boot']),Path(args.build_only))
    else:
        with open('/run/lock/grubz-direct.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            update(cfg)

if __name__ == '__main__':
    main()
