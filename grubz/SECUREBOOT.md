# Isolated Secure Boot validation

This is a VM-only test, not a host installation procedure. It does not enroll
host keys, mount an ESP, modify host boot entries, or connect physical disks.
The existing unsigned preview VM is independent of this test.

## Run

In addition to the normal build/VM dependencies, use `openssl`, `sbsigntool`,
and `python3-virt-firmware` (Debian bookworm-backports provides the latter).
The packages can be extracted with `dpkg-deb -x` into
`grubz/secureboot-local/tools` instead of installed. Python cryptography is required.

From the repository root:

```sh
bash grubz/build.sh
bash grubz/secureboot-build.sh
bash grubz/secureboot-run.sh
```

Set `GNU_EFI_ROOT` for the first two commands if GNU-EFI is extracted locally.
Stop the Secure Boot VM before rebuilding. Rebuilding replaces its disposable
disk and firmware variable store; existing local test keys are reused.

Generated keys, signed binaries, disks, and firmware variables stay in the ignored
`grubz/secureboot-local/` directory. Private keys have mode 0600, and the directory
has mode 0700. These unencrypted disposable keys are **not production signing keys**.
Do not enroll them on a real machine or upload the directory to GitHub.

## What is tested

The VM uses Q35 with SMM, OVMF's Secure Boot firmware, and protected pflash.
The test certificate is explicitly added to the virtual firmware's `db`. The
test also uses it for its disposable PK/KEK; this is not a production key hierarchy.
The generated dbx is a dummy test entry, not the host's current revocation database.

A small signed EFI probe at the fallback boot path reads runtime variables and
calls firmware `LoadImage` on four versions of the same rEFInd binary. It never
starts a negative-test image. It starts the trusted signed image only after all
checks pass. Diagnostic output goes to QEMU's debug port and is saved in
`grubz/secureboot-local/probe.log`.

Observed on 2026-11-13 with Debian OVMF/QEMU:

| Check | Observed result |
|---|---|
| Runtime variables | `SecureBoot=1`, `SetupMode=0` |
| Unsigned rEFInd | Rejected: `EFI_ACCESS_DENIED` |
| rEFInd signed with an unenrolled key | Rejected: `EFI_ACCESS_DENIED` |
| Trusted signed rEFInd with an altered `.text` byte | Rejected: `EFI_ACCESS_DENIED` |
| Trusted signed rEFInd | Accepted; graphical selector displayed |
| Signed Debian demo loader | Menu reached through rEFInd |
| Signed Windows demo loader | Menu reached through rEFInd |

`sbverify` also accepted the trusted signature and rejected the tampered file.
The runtime probe permits only the documented security rejection statuses
`EFI_ACCESS_DENIED` or `EFI_SECURITY_VIOLATION`; missing files or other errors fail.
It fails if Secure Boot is off or firmware is in Setup Mode.

The signed rEFInd SHA-256 for this run was
`d5c3bc38ee388e79f42baa9e3a4822323406e07c758e89c98fd27d5c2d669992`.
Fresh signatures/builds can produce different hashes; local values are recorded
in `secureboot-local/binaries.sha256`.

## Limits and next validation

This direct-db test proves signature enforcement and EFI demo handoff for this virtual firmware
with its own trust database. It does **not** prove that the physical firmware or
Debian shim will trust the certificate. The subsequent [shim/MOK test](SHIM-MOK.md)
separately validates that chain and interactive VM enrollment with the documented
versions and virtual trust stores. Neither demo is an actual Debian/Windows
installation. Physical firmware and its revocation policy still require a
reversible one-time boot test before host deployment.

References: [QEMU variable protection](https://www.qemu.org/docs/master/devel/uefi-vars.html),
[virt-firmware](https://gitlab.com/kraxel/virt-firmware),
[EDK2 verification policies](https://github.com/tianocore/edk2/blob/master/SecurityPkg/SecurityPkg.dec).
