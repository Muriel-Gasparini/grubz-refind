#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/vm"
if [[ -S monitor.sock ]]; then echo 'VM already running.' >&2; exit 1; fi
test -f disk.img
test -f OVMF_VARS.fd
exec qemu-system-x86_64 -name 'GRUBZ - native rEFInd VM' \
  -machine q35 -accel tcg -m 512 -smp 2 \
  -drive if=pflash,format=raw,readonly=on,file="${OVMF_CODE:-/usr/share/OVMF/OVMF_CODE_4M.fd}" \
  -drive if=pflash,format=raw,file="$PWD/OVMF_VARS.fd" \
  -drive if=virtio,format=raw,snapshot=on,file="$PWD/disk.img" \
  -vga std -nic none -no-reboot -display gtk,zoom-to-fit=on \
  -qmp unix:"$PWD/monitor.sock",server=on,wait=off
