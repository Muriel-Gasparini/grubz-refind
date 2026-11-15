# Grubz rEFInd

A graphical rEFInd derivative with native inactive-icon dimming and a sliding
selection highlight. Based on **rEFInd 0.14.2**, preserving upstream Git history
and licenses. Runs before the operating system, with a custom dark theme,
native dimming and sliding selection. Despite its name, Grubz is based on rEFInd,
not GNU GRUB.

[Português (Brasil)](README.pt-BR.md) · [User guide](docs/USER-GUIDE.md) ·
[Configuration](docs/CONFIGURATION.md) · [Direct Debian boot](grubz/DIRECT-BOOT.md)

**Status:** working as the permanent boot selector on the maintainer’s Debian 12 /
Windows dual-boot PC. Direct Debian boot with Secure Boot was confirmed on physical
hardware; kernel-update integration was exercised in a real Debian VM. This is a
personal, experimental project, not a universal installer or a hardware certification.
Windows demo handoff was tested in VMs; the physical Windows entry is preserved,
but a physical Windows boot is not claimed by this validation report.

![Real QEMU/OVMF framebuffer recording](grubz/preview.gif)

## What Grubz adds

- Custom generated Obsidian artwork and metallic OS icons.
- Native inactive-icon dimming and a sliding selection highlight in C.
- A selector that waits for a deliberate choice (`timeout 0` in rEFInd).
- Optional signed Unified Kernel Images (UKIs) to boot Debian without an intermediate GRUB screen.
- Debian initramfs/kernel-removal hooks that publish a newly signed UKI, retaining the previous artifact.
- Separate preview, Secure Boot and shim/MOK VM tests, including rejection cases.

```ini
inactive_icon_brightness 32
selection_animation_ms 120
timeout 0
```

The 120 ms setting is a target, not a guaranteed measured duration on every firmware.
Keyboard arrows animate adjacent visible OS entries; pointer selection and scrolling
remain static. See [configuration and rendering limits](docs/CONFIGURATION.md).

## Choose your starting point

| Goal | Start here |
| --- | --- |
| See the real selector without touching host boot | Build + isolated preview below |
| Understand signatures and MOK enrollment | [Secure Boot](grubz/SECUREBOOT.md), then [shim/MOK](grubz/SHIM-MOK.md) |
| Use it on a real PC | [Staged installation and rollback](docs/USER-GUIDE.md) |
| Boot Debian without GRUB | [UKI updater setup](grubz/DIRECT-BOOT.md) |

## Build and tests (Debian/Ubuntu x86-64)

For Debian boot without chaining through GRUB, see
[Direct boot with signed UKIs](grubz/DIRECT-BOOT.md). The optional Linux-side
updater signs kernel, initramfs and command line together and refreshes the image
after kernel/initramfs changes. Installing it does not change firmware defaults.

Target: **x86-64 UEFI**, built on Debian/Ubuntu. Legacy BIOS and other architectures
are not validated for these changes. From a fresh clone:

```sh
git clone --branch grubz https://github.com/Muriel-Gasparini/grubz-refind.git
cd grubz-refind
sudo apt-get install build-essential gnu-efi python3
```

Then:

```sh
bash grubz/test.sh
bash grubz/build.sh
```

Output: `refind/refind_x64.efi`. `GNU_EFI_ROOT=/path/to/extracted/package` can point
to an extracted GNU-EFI `.deb`, avoiding a system-wide development-library install.
The build does **not** install a boot manager. This binary is unsigned.

## Isolated VM preview

Additional dependencies: `qemu-system-x86 qemu-system-gui ovmf grub-efi-amd64-bin
mtools dosfstools gdisk imagemagick`.

```sh
sudo apt-get install qemu-system-x86 qemu-system-gui ovmf grub-efi-amd64-bin \
  mtools dosfstools gdisk imagemagick
bash grubz/build-vm.sh
bash grubz/run-vm.sh
```

The VM has only a regular-file virtual disk, its own OVMF variables, and no network,
host disks, shared folders, or passthrough devices. No host ESP, GRUB configuration,
or firmware boot order is modified. `timeout 0` keeps rEFInd waiting for input.
Both menu entries launch clearly labeled **demo EFI loaders**, not Windows/Linux
installations. Use `Return to rEFInd` to return. Close QEMU to stop the VM.
Rebuild only after stopping it; rebuilding replaces the disposable VM files.

This verifies the real menu renderer and EFI handoff to demo loaders. It does not
validate physical firmware, Secure Boot, BitLocker, or installed operating systems.

### Separate Secure Boot VM

Secure Boot enforcement is tested separately with disposable keys and a signed
EFI probe. See [the procedure and observed results](grubz/SECUREBOOT.md).
The first test uses direct firmware `db` trust. A separate
[Debian shim/MOK validation](grubz/SHIM-MOK.md) covers MOK-only trust,
negative cases, and interactive enrollment through MokManager in the VM.

## Upstream maintenance

Upstream: https://git.code.sf.net/p/refind/code

Base tag: `v.0.14.2`, commit `6c66e90b3d36c1b4c7b0067203be2ba99a0380fb`.
The `grubz` branch contains our changes. Keep upstream history and merge future
releases on a separate update branch, then run tests and the VM before merging:

```sh
git remote add upstream https://git.code.sf.net/p/refind/code # once per clone
git fetch upstream --tags
git switch -c update/upstream-next
# git merge <reviewed-upstream-tag>
```

GitHub Actions builds the unsigned EFI binary and runs the automated tests on pushes/PRs.
It does not run the interactive VM or physical boot tests. Updates are deliberate; no automation
installs or deploys this to firmware.

## Artwork and licensing

Obsidian background and metallic OS emblems were generated specifically for this
project with OpenAI image generation; theme PNGs include layout/text composition.
Development was assisted by OpenAI Codex.
The Debian and Windows names/marks identify the boot choices; no affiliation or
endorsement is implied. Original upstream copyright and licensing notices are
preserved in `LICENSE.txt` and source files. New Grubz code is GPL-3.0-or-later.

## Feedback and contributions

Open an issue with your firmware/GPU, supported UEFI graphics modes, distro,
Secure Boot state, Grubz commit and reproduction steps. Do not upload private keys,
firmware dumps or personal disk identifiers. Distinguish a VM result from a hardware
result. Send focused PRs with relevant tests; preserve upstream history and licenses.

For recovery, first use your original firmware boot entry; see the user guide before
changing the boot order. No provided build/VM script installs Grubz on your host.
