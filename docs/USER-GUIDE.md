# User guide: preview, deployment and recovery

[Home](../README.md) · [Português](../README.pt-BR.md)

## 1. Know what you are running

Grubz is an rEFInd derivative. Its C renderer runs as an EFI application before
Linux/Windows. The optional Python updater runs inside Debian when boot images
change; it is not part of the firmware UI.

Two supported approaches are documented:

- **Original-loader handoff:** Grubz starts your existing Debian shim/GRUB or Windows
  Boot Manager. This preserves their behavior, including any second menu.
- **Direct Debian:** Grubz starts a signed UKI containing the Debian kernel, initramfs
  and command line. The existing GRUB remains installed for recovery.

The maintainer uses direct Debian boot on a physical Debian 12/Windows dual-boot
machine and has confirmed the permanent selector works. VM coverage includes real
Debian boots, kernel package updates and rejection of a tampered UKI. This is not
validation of every Windows installation, firmware, disk layout or future kernel.

## 2. Build and preview first

Follow the build and QEMU instructions in [README](../README.md). Run commands from
the repository root. Build output is unsigned; it is not ready for a Secure Boot
machine simply because the build succeeds. The default preview's OS labels lead
to **demo EFI applications**, not installed operating systems.

Controls: Left/Right choose a system; Enter starts it. F2 or Insert opens a submenu
when one is configured. `timeout 0` in rEFInd waits indefinitely. In GNU GRUB,
`timeout=0` instead starts the default immediately; do not interchange the settings.

The example uses 1920×1080. Firmware graphics modes may differ from desktop modes.
An unsupported resolution can fall back to a small mode, crop artwork and force
scrolling instead of animated adjacent selection. Use a mode your firmware reports.
See [UI settings and limitations](CONFIGURATION.md).

## 3. Understand Secure Boot before hardware deployment

The tested trust chain is:

```text
UEFI Secure Boot -> Microsoft-signed Debian shim -> signed Grubz
                                                   |-> signed Debian UKI -> Linux
                                                   |-> original OS loader
```

A MOK-enrolled key is trusted by shim; it is not automatically a firmware-db key.
Pointing the firmware straight at a MOK-signed Grubz binary can therefore fail.
Keep the matching Debian MokManager with shim. Grubz is named `grubx64.efi` beside
shim so shim can locate its next stage; this filename does not make it GNU GRUB.
Do not replace your distribution's existing `grubx64.efi`.

Use [the direct-db VM test](../grubz/SECUREBOOT.md), then the
[Debian shim/MOK VM test](../grubz/SHIM-MOK.md). Test keys in those scripts are
throwaway VM keys. Create a separate production key, keep it root-only, enroll only
its public certificate, and check its fingerprint on the enrollment screen.
Do not disable Secure Boot validation to make a failed test pass.

## 4. Deploy to a separate EFI directory

There is intentionally no universal `sudo install.sh`. Disk numbers, partition
identifiers, recovery access and trust state must be established on your machine.

Before changing anything, record your state with read-only commands:

```sh
findmnt /boot/efi
lsblk -o NAME,FSTYPE,UUID,PARTUUID,MOUNTPOINTS
sudo efibootmgr -v
mokutil --sb-state
cat /proc/cmdline
```

Save the original BootOrder and copies of the relevant EFI directories somewhere
outside the ESP as well. Confirm how to select the original Debian/Windows entries
from your firmware. Have a recovery medium available before making unfamiliar boot
changes. Encrypted systems may require recovery keys when boot measurements change.

Stage the files in a dedicated directory such as `EFI/grubz`:

```text
EFI/grubz/
  shimx64.efi   # original distribution-signed shim
  mmx64.efi     # matching distribution MokManager
  grubx64.efi   # YOUR signed Grubz build
  refind.conf  # YOUR loader paths and partition identifiers
  theme/       # project theme PNGs
```

Sign your build with your own production certificate, then verify it. Example
placeholders below are intentionally not a deployment command:

```sh
sbsign --key /path/to/private.key --cert /path/to/public.pem \
  --output /path/to/staging/grubx64.efi refind/refind_x64.efi
sbverify --cert /path/to/public.pem /path/to/staging/grubx64.efi
```

Copy a verified staging tree to your separate EFI directory. Adapt `icons_dir`,
`banner`, selection-artwork paths, and manual entries. The sample `grubz/refind.conf`
is **VM-only** and its loaders do not exist on your real machine.

Example of the shape of real manual entries (replace every placeholder):

```ini
menuentry "Debian" {
    icon /EFI/grubz/theme/debian.png
    volume YOUR_DEBIAN_ESP_PARTUUID
    loader /EFI/debian/shimx64.efi
}
menuentry "Windows" {
    icon /EFI/grubz/theme/windows.png
    volume YOUR_WINDOWS_ESP_PARTUUID
    loader /EFI/Microsoft/Boot/bootmgfw.efi
}
```

Put `icon` before `volume` when icons reside on Grubz's ESP but the target loader
resides on a different ESP. Verify actual Debian paths; distributions and customized
installations do not always use `EFI/debian`.

## 5. One-time test before permanent default

Create a firmware entry pointing to the **new shim**, preserving all original entries
and the original BootOrder. `efibootmgr --create-only` avoids inserting an entry into
BootOrder; firmware support differs. On the maintainer's ASUS board, an entry outside
BootOrder was hidden from the boot menu and ignored for BootNext. Appending it at the
end made it available while preserving the original default.

After identifying the new entry's actual four-digit number, `efibootmgr -n NUMBER`
requests it once. Read `efibootmgr -v` again to verify BootNext and unchanged BootOrder.
Neither setting triggers a reboot. Enroll the public key if required and confirm
Secure Boot acceptance. Test each OS you intend to use, the UI and your recovery path.
Only then move Grubz first with `efibootmgr -o COMMA_SEPARATED_ORDER`, keeping every
original entry. Re-read and compare the resulting order and entry paths.

The numbers are machine-specific. Never paste the maintainer's BootOrder into your PC.

## 6. Optional direct Debian boot

Follow [UKI setup](../grubz/DIRECT-BOOT.md). Preserve your working kernel command line,
including root, encryption and storage parameters. Do not use another machine's root
UUID. The initial UKI must build and verify before replacing the Grubz Debian entry.

```ini
menuentry "Debian" {
    icon /EFI/grubz/theme/debian.png
    volume YOUR_DEBIAN_ESP_PARTUUID
    loader /EFI/grubz-linux/current.efi
    graphics on
    submenuentry "Original Debian loader (GRUB)" {
        loader /EFI/debian/shimx64.efi
        graphics off
    }
}
```

F2 on Debian opens this submenu. It starts the original loader with its existing
configuration; it does not override a GRUB menu that you separately configured as
hidden. Keep your original GRUB recovery access working. Direct boot removes the
intermediate GRUB screen, not every possible firmware/driver display transition.

## 7. Recovery and rollback

- If Grubz fails before selection, choose the original Debian or Windows entry in
  the firmware. BootNext is one-time, not a guaranteed automatic recovery after a hang.
- If direct Debian fails but Grubz works, try its original-loader submenu.
- Restore the saved original BootOrder to stop using Grubz by default. This does
  not require deleting any EFI files.
- To undo direct boot, restore the Debian Grubz entry to the original shim and
  remove both updater hooks. Leave the original bootloaders and kernel packages intact.
- Keep a known-good kernel package: `previous.efi` alone does not preserve its modules.
- If an update hook fails, read its error and fix it before relying on a new kernel.
  The last published UKI may still be the old version.

## Common symptoms

| Symptom | Check |
| --- | --- |
| Security Policy Violation | Correct shim chain, enrolled certificate, signature, firmware/dbx/SBAT policy |
| Menu cropped or no slide | Supported firmware resolution; adjacent visible entries; animation not set to 0 |
| About square at bottom | `showtools about` is enabled in diagnostic shim VMs; normal sample uses empty `showtools` |
| Old GRUB still appears | Debian entry still points at shim/GRUB rather than the UKI |
| HDMI/VGA overlay | Often the monitor's own input notification; not a Grubz UI element |
| Kernel updated but boot uses old version | Hook error, wrong ESP, missing initramfs, or menu pointing at a different image |

Upstream reference: [rEFInd Secure Boot documentation](https://www.rodsbooks.com/refind/secureboot.html).
