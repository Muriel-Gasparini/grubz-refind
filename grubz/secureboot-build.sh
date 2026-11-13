#!/usr/bin/env bash
# Build disposable VM-only Secure Boot artifacts. Never enroll keys on the host.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
root="$PWD/secureboot-local"
mkdir -p "$root"
chmod 700 "$root"
if [[ -S "$root/monitor.sock" ]]; then echo 'Stop the Secure Boot VM first.' >&2; exit 1; fi
export PATH="$root/tools/usr/bin:$PATH"
export PYTHONPATH="$root/tools/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
efi_root="${GNU_EFI_ROOT:-}"
efi_inc="$efi_root/usr/include/efi"
efi_lib="$efi_root/usr/lib"
umask 077
mkdir -p "$root/keys" "$root/esp/EFI/BOOT/theme" "$root/esp/EFI/DEBIAN" "$root/esp/EFI/WINDOWS"
for name in trusted untrusted; do
  if [[ ! -f "$root/keys/$name.key" ]]; then
    openssl req -new -x509 -newkey rsa:2048 -sha256 -nodes -days 3650 \
      -subj "/CN=Grubz VM TEST ONLY $name/" \
      -keyout "$root/keys/$name.key" -out "$root/keys/$name.pem" 2>"$root/keygen-$name.log"
  fi
done
sign() { sbsign --key "$root/keys/$1.key" --cert "$root/keys/$1.pem" --output "$3" "$2"; }
cc -I"$efi_inc" -I"$efi_inc/x86_64" -fpic -fshort-wchar -fno-stack-protector \
  -mno-red-zone -DEFI_FUNCTION_WRAPPER -Wall -Wextra -Werror \
  -c secureboot-probe.c -o "$root/probe.o"
ld -nostdlib -znocombreloc -T "$efi_lib/elf_x86_64_efi.lds" -shared -Bsymbolic \
  "$efi_lib/crt0-efi-x86_64.o" "$root/probe.o" -L"$efi_lib" -lefi -lgnuefi -o "$root/probe.so"
objcopy -j .text -j .sdata -j .data -j .dynamic -j .dynsym -j .rel -j .rela -j .reloc \
  --target=efi-app-x86_64 "$root/probe.so" "$root/probe.efi"
boot="$root/esp/EFI/BOOT"
sign trusted "$root/probe.efi" "$boot/BOOTX64.EFI"
cp ../refind/refind_x64.efi "$boot/unsigned.efi"
sign trusted ../refind/refind_x64.efi "$boot/refind-signed.efi"
sign untrusted ../refind/refind_x64.efi "$boot/untrusted.efi"
# Change a byte in the signed .text section, retaining a well-formed PE image.
/usr/bin/python3 - "$boot/refind-signed.efi" "$boot/tampered.efi" <<'PY'
import struct, sys
from pathlib import Path
b = bytearray(Path(sys.argv[1]).read_bytes())
pe = struct.unpack_from('<I', b, 0x3c)[0]
count = struct.unpack_from('<H', b, pe + 6)[0]
section = pe + 24 + struct.unpack_from('<H', b, pe + 20)[0]
for n in range(count):
    offset = section + n * 40
    if b[offset:offset+8].rstrip(b'\0') == b'.text':
        raw = struct.unpack_from('<I', b, offset + 20)[0]
        b[raw + 64] ^= 1
        break
else:
    raise SystemExit('Missing .text')
Path(sys.argv[2]).write_bytes(b)
PY
sbverify --cert "$root/keys/trusted.pem" "$boot/refind-signed.efi"
if sbverify --cert "$root/keys/trusted.pem" "$boot/tampered.efi"; then exit 1; fi
cp refind.conf "$boot/refind.conf"
cp theme/*.png "$boot/theme/"
for os in DEBIAN WINDOWS; do
  cat > "$root/$os.cfg" <<EOF
set timeout=-1
terminal_output console
menuentry '$os - SIGNED VM demo loader (not an installed OS)' { true; }
menuentry 'Return to rEFInd' { exit; }
EOF
  grub-mkstandalone -O x86_64-efi --locales='' --fonts='' \
    -o "$root/$os.efi" "boot/grub/grub.cfg=$root/$os.cfg"
  sign trusted "$root/$os.efi" "$root/esp/EFI/$os/test.efi"
done
/usr/bin/python3 "$(command -v virt-fw-vars)" \
  -i /usr/share/OVMF/OVMF_VARS_4M.fd -o "$root/OVMF_VARS.fd" \
  --enroll-cert "$root/keys/trusted.pem" --no-microsoft --sb \
  --add-db 40f4b499-170b-4ff9-a42a-f942d77e87af "$root/keys/trusted.pem"
truncate -s 128M "$root/esp.img"
mkfs.vfat -F 32 -n GRUBZ_SB "$root/esp.img"
mcopy -s -i "$root/esp.img" "$root/esp/EFI" ::/
truncate -s 132M "$root/disk.img"
sgdisk --clear --new=1:2048:+128M --typecode=1:ef00 "$root/disk.img"
dd if="$root/esp.img" of="$root/disk.img" bs=1M seek=1 conv=notrunc status=none
sha256sum ../refind/refind_x64.efi "$boot/refind-signed.efi" > "$root/binaries.sha256"
echo 'Built VM-only artifacts. Test private keys stay in ignored secureboot-local/.'
