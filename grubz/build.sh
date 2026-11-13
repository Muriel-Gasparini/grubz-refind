#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ -n ${GNU_EFI_ROOT:-} ]]; then
  make gnuefi REFIND_SBAT_CSV=refind-sbat-grubz.csv EFIINC="$GNU_EFI_ROOT/usr/include/efi" \
    GNUEFILIB="$GNU_EFI_ROOT/usr/lib" EFILIB="$GNU_EFI_ROOT/usr/lib" \
    EFICRT0="$GNU_EFI_ROOT/usr/lib"
else
  make gnuefi REFIND_SBAT_CSV=refind-sbat-grubz.csv
fi
printf '\nBuilt: %s/refind/refind_x64.efi\n' "$PWD"
