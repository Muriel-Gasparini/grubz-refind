#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/secureboot-local"
if [[ -S monitor.sock ]]; then echo 'Secure Boot VM already running.' >&2; exit 1; fi
exec qemu-system-x86_64 -name 'GRUBZ - Secure Boot TEST ONLY' \
  -machine q35,smm=on -accel tcg -m 512 -smp 2 \
  -global driver=cfi.pflash01,property=secure,value=on \
  -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
  -drive if=pflash,format=raw,unit=1,file="$PWD/OVMF_VARS.fd" \
  -drive if=virtio,format=raw,snapshot=on,file="$PWD/disk.img" \
  -vga std -nic none -no-reboot -display gtk,zoom-to-fit=on \
  -debugcon file:"$PWD/probe.log" -global isa-debugcon.iobase=0xe9 \
  -qmp unix:"$PWD/monitor.sock",server=on,wait=off
