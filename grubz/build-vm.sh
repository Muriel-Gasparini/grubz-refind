#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -S vm/monitor.sock ]]; then echo 'Stop the VM before rebuilding.' >&2; exit 1; fi
test -f ../refind/refind_x64.efi
mkdir -p vm/esp/EFI/{BOOT/theme,DEBIAN,WINDOWS} vm/evidence
cp ../refind/refind_x64.efi vm/esp/EFI/BOOT/BOOTX64.EFI
cp refind.conf vm/esp/EFI/BOOT/refind.conf
cp theme/*.png vm/esp/EFI/BOOT/theme/
for os in DEBIAN WINDOWS; do
  cat > "vm/$os.cfg" <<EOF
set timeout=-1
set default=0
terminal_output console
menuentry '$os - VM test loader reached (NOT an installed OS)' { true; }
menuentry 'Return to rEFInd' { exit; }
EOF
  grub-script-check "vm/$os.cfg"
  grub-mkstandalone -O x86_64-efi --locales='' --fonts='' \
    -o "vm/esp/EFI/$os/test.efi" "boot/grub/grub.cfg=$PWD/vm/$os.cfg"
done
truncate -s 128M vm/esp.img
mkfs.vfat -F 32 -n GRUBZ_VM vm/esp.img
mcopy -s -i vm/esp.img vm/esp/EFI ::/
truncate -s 132M vm/disk.img
sgdisk --clear --new=1:2048:+128M --typecode=1:ef00 --change-name=1:GRUBZ_VM vm/disk.img
dd if=vm/esp.img of=vm/disk.img bs=1M seek=1 conv=notrunc status=none
cp "${OVMF_VARS_TEMPLATE:-/usr/share/OVMF/OVMF_VARS_4M.fd}" vm/OVMF_VARS.fd
sha256sum ../refind/refind_x64.efi vm/esp/EFI/BOOT/BOOTX64.EFI
