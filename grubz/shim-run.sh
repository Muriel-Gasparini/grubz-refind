#!/usr/bin/env bash
set -euo pipefail
variant="${1:-trusted}"
case "$variant" in trusted|unsigned|untrusted|tampered|no-mok|enroll) ;; *) exit 2;; esac
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/shim-local/$variant"
if [[ -S monitor.sock ]]; then echo 'Test VM already running.' >&2; exit 1; fi
exec qemu-system-x86_64 -name "GRUBZ - Debian shim MOK - $variant" \
 -machine q35,smm=on -accel tcg -m 512 -smp 2 \
 -global driver=cfi.pflash01,property=secure,value=on \
 -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
 -drive if=pflash,format=raw,unit=1,file="$PWD/OVMF_VARS.fd" \
 -drive if=virtio,format=raw,snapshot=on,file="$PWD/disk.img" \
 -vga std -nic none -no-reboot -display "${GRUBZ_VM_DISPLAY:-gtk,zoom-to-fit=on}" \
 -serial file:"$PWD/serial.log" \
 -qmp unix:"$PWD/monitor.sock",server=on,wait=off
