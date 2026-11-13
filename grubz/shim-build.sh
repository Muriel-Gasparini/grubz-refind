#!/usr/bin/env bash
# VM only: pre-enroll MOK in a disposable OVMF file, never in host firmware.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
variant="${1:-trusted}"
case "$variant" in trusted|unsigned|untrusted|tampered|no-mok|enroll) ;; *) exit 2;; esac
source_root="$PWD/secureboot-local"
root="$PWD/shim-local/$variant"
umask 077
mkdir -p "$root"
chmod 700 "$PWD/shim-local" "$root"
if [[ -S "$root/monitor.sock" ]]; then echo 'Stop this test VM first.' >&2; exit 1; fi
export PATH="$source_root/tools/usr/bin:$PATH"
export PYTHONPATH="$source_root/tools/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
test -f "$source_root/esp/EFI/BOOT/refind-signed.efi"
mkdir -p "$root/esp"
cp -r "$source_root/esp/EFI" "$root/esp/"
boot="$root/esp/EFI/BOOT"
cp /usr/lib/shim/shimx64.efi.signed "$boot/BOOTX64.EFI"
cp /usr/lib/shim/mmx64.efi.signed "$boot/mmx64.efi"
case "$variant" in
 trusted|no-mok|enroll) cp "$boot/refind-signed.efi" "$boot/grubx64.efi";;
 *) cp "$boot/$variant.efi" "$boot/grubx64.efi";;
esac
# Expose the upstream About screen to verify "Secure Boot active (via Shim)".
sed 's/^showtools$/showtools about/' refind.conf > "$boot/refind.conf"
vars_args=()
if [[ "$variant" != no-mok && "$variant" != enroll ]]; then
 vars_args+=(--add-mok 40f4b499-170b-4ff9-a42a-f942d77e87af "$source_root/keys/trusted.pem")
fi
/usr/bin/python3 "$(command -v virt-fw-vars)" \
 -i /usr/share/OVMF/OVMF_VARS_4M.ms.fd -o "$root/OVMF_VARS.fd" \
 --sb "${vars_args[@]}" --output-json "$root/vars-before.json"
# Prevent an accidentally broadened trust store from invalidating the test.
/usr/bin/python3 - "$root/vars-before.json" "$source_root/keys/trusted.pem" "$variant" <<'PY'
import json, sys
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
v = {i['name']: bytes.fromhex(i['data']) for i in json.loads(Path(sys.argv[1]).read_text())['variables']}
c = x509.load_pem_x509_certificate(Path(sys.argv[2]).read_bytes()).public_bytes(Encoding.DER)
assert all(c not in v.get(n, b'') for n in ('PK', 'KEK', 'db', 'dbx'))
assert (c in v.get('MokList', b'')) == (sys.argv[3] not in ('no-mok', 'enroll'))
assert not v.get('MokSBState', b'')
print('PASS: test certificate trust is restricted to the intended MOK state')
PY
truncate -s 128M "$root/esp.img"
mkfs.vfat -F 32 -n GRUBZ_MOK "$root/esp.img"
mcopy -s -i "$root/esp.img" "$root/esp/EFI" ::/
if [[ "$variant" == enroll ]]; then
 openssl x509 -in "$source_root/keys/trusted.pem" -outform DER -out "$root/Grubz-VM-TEST.cer"
 mcopy -i "$root/esp.img" "$root/Grubz-VM-TEST.cer" ::/
fi
truncate -s 132M "$root/disk.img"
sgdisk --clear --new=1:2048:+128M --typecode=1:ef00 "$root/disk.img"
dd if="$root/esp.img" of="$root/disk.img" bs=1M seek=1 conv=notrunc status=none
sha256sum "$boot/BOOTX64.EFI" "$boot/grubx64.efi" "$boot/mmx64.efi" > "$root/binaries.sha256"
