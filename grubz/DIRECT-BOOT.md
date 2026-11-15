# Direct Debian boot with Secure Boot

The direct entry loads a signed Unified Kernel Image (UKI): Debian systemd-stub,
kernel, initramfs, kernel version and command line in a single verified EFI image.
The path is firmware -> Debian shim -> Grubz -> UKI -> Linux. It does not run GRUB.
The original Debian and Windows loaders remain separate recovery paths.

`direct_boot.py` uses Debian's `objcopy`, `sbsign`, `sbverify`, `dpkg` and Python 3.11.
No runtime Python dependency is added to the EFI application. `--build-only` builds
an isolated artifact; publishing requires root and an explicitly identified mounted
FAT ESP. It never changes BootOrder, BootNext, keys or firmware settings.

Host configuration is root-owned `/etc/grubz-direct.json`, including `boot`, `esp`,
`esp_uuid`, `stub`, `key`, `cert`, `os_release` and `cmdline`. Optional absolute
`objcopy`, `sbsign`, `sbverify` paths support locally extracted Debian tools.
Signing keys must remain root-only. Do not commit host configuration or keys.

Install the updater as `/usr/local/sbin/grubz-direct-update` and `uki-update-hook`
as `/etc/initramfs/post-update.d/zz-grubz-direct` (both root-owned executable).
The initramfs hook runs after successful generation, including Debian kernel package
post-install triggers and `update-initramfs -u`. Install the same hook also as
`/etc/kernel/postrm.d/zz-grubz-direct`: Debian does not invoke the initramfs
post-update hook on deletion. The post-removal hook selects the newest remaining
pair; if none remains, it fails visibly without deleting the existing UKIs. It selects the newest complete
kernel/initramfs pair using Debian version comparisons, not lexical ordering.

Publishing stages and verifies the new image on the ESP before replacing
`EFI/grubz-linux/current.efi`. `previous.efi` retains the preceding published image;
it is not a promise that this image has booted successfully. It also requires
the matching installed kernel modules: removing that kernel package can invalidate
the previous-image fallback. Keep a known-good kernel package installed; the original
GRUB recovery path is retained independently. A signing/build failure
or insufficient space leaves current intact and returns an error to package tools.
Do not ignore that error: the installed kernel package may be newer than the UKI.
The updater locks concurrent invocations. Atomic rename reduces update exposure;
it is not a guarantee against firmware/filesystem damage from power loss.

The manual Grubz entry points at `/EFI/grubz-linux/current.efi` with `graphics on`.
The kernel command line is embedded and signed. After intentional changes to that
line, regenerate the UKI. Changes to `/etc/default/grub` do not automatically modify
this separate configuration. Keep a fallback entry to the original Debian shim,
and optionally a submenu to `previous.efi` once it exists.

To stop future automatic UKI updates, remove both the initramfs and kernel post-removal hooks. To return to the
original boot path, restore the Grubz Debian entry to its original shim. Do not
remove original loaders or change firmware defaults as part of this installation.

Validation must distinguish VM from physical hardware. Test a complete Debian boot
under shim/MOK Secure Boot, a real kernel package upgrade, an initramfs regeneration,
and a modified unsigned/untrusted image rejection. A passing test cannot guarantee
that arbitrary future kernels will work on every device.

## Configuration template and installation order

This is a host-specific administrative setup, after the VM and recovery checks in
[the user guide](../docs/USER-GUIDE.md). Install Debian's `systemd-boot-efi`,
`sbsigntool`, `binutils`, `python3` and the normal kernel/initramfs tools as needed.
Installing the stub package is not the same as running `bootctl install`; this
workflow does not require installing systemd-boot or changing the firmware defaults.

Create `/etc/grubz-direct.json` as root, mode 0600, replacing the placeholders:

```json
{
  "boot": "/boot",
  "esp": "/boot/efi",
  "esp_uuid": "YOUR_FAT_FILESYSTEM_UUID",
  "stub": "/usr/lib/systemd/boot/efi/linuxx64.efi.stub",
  "key": "/var/lib/grubz/signing/private.key",
  "cert": "/var/lib/grubz/signing/public.pem",
  "os_release": "/etc/os-release",
  "cmdline": "root=UUID=YOUR_ROOT_FILESYSTEM_UUID ro YOUR_EXISTING_KERNEL_OPTIONS"
}
```

`esp_uuid` is the FAT filesystem UUID, not its PARTUUID. Preserve relevant parameters
from your working boot, excluding GRUB's `BOOT_IMAGE=...` bookkeeping token. Root-only
unencrypted signing keys enable unattended updates; protect them as administrative
credentials. Do not use the disposable VM keys. If you use an extracted/pinned stub
instead of a distribution-managed package, plan its security updates separately.

From the repository root, after configuring the correct ESP, key and command line:

```sh
sudo install -o root -g root -m 0755 grubz/direct_boot.py /usr/local/sbin/grubz-direct-update
# Build + verify + publish first; stop if this fails.
sudo /usr/local/sbin/grubz-direct-update
# Register automatic updates only after successful publication.
sudo install -d -o root -g root -m 0755 /etc/initramfs/post-update.d /etc/kernel/postrm.d
sudo install -o root -g root -m 0755 grubz/uki-update-hook /etc/initramfs/post-update.d/zz-grubz-direct
sudo install -o root -g root -m 0755 grubz/uki-update-hook /etc/kernel/postrm.d/zz-grubz-direct
```

Review the printed version/path/hash. Verify with `sbverify --cert YOUR_PUBLIC_CERT
/boot/efi/EFI/grubz-linux/current.efi`, then change only the dedicated Grubz entry.
Keep hooks installed for subsequent kernel changes. Package replacement's intermediate
postrm phase is skipped; the new initramfs hook performs the publication.

To build an isolated artifact without publishing or changing hooks, use
`python3 grubz/direct_boot.py --config /path/to/config.json --build-only /path/to/output.efi`.
The builder still needs access to the configured key. The chosen kernel defaults to
the newest complete pair; `--version` selects a specific version for build-only tests.

## Verified integration (Debian 12, QEMU/OVMF)

The isolated guest uses Microsoft-trusting OVMF, Debian shim 16.1, Grubz .2,
and a disposable signing certificate enrolled **only in MOK**, not firmware db.
The Linux-side tools use Debian systemd-stub 252.39 and Debian kernels.

| Test | Observed result |
| --- | --- |
| Direct UKI boot, 6.1.0-53-amd64 | Debian userspace reached; SecureBoot=1, SetupMode=0, kernel lockdown integrity |
| Debian package installation, 6.1.0-54-amd64 | Initramfs hook published a signed UKI automatically |
| Boot through unchanged `current.efi` entry | Debian userspace reached on 6.1.0-54-amd64 with Secure Boot still active |
| Modify a byte in signed `.cmdline` | Security Policy Violation; Grubz rejected image and returned to selector |
| Regenerate initramfs for older kernel 53 | Published version remained kernel 54 |
| Remove kernel package 54 while running 53 | Actual postrm hook published kernel 53 |

Unit tests cover failed build/signature verification, insufficient ESP space,
wrong mount, numeric version ordering, incomplete pairs, kernel removal and
preserving the previous artifact on an identical-byte update. The maintainer subsequently confirmed direct Debian boot on physical hardware
and made Grubz the permanent selector. That report does not extend the VM update
tests to arbitrary future kernels or other physical devices.
