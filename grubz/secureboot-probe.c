/* SPDX-License-Identifier: GPL-3.0-or-later
 * VM-only x86-64 probe. Logs to QEMU's debug port, never writes EFI variables.
 */
#include <efi.h>
#include <efilib.h>

static void log_text(const char *s) {
    while (*s) { __asm__ volatile ("outb %0, %1" : : "a"(*s++), "Nd"((unsigned short)0xe9)); }
}

static void log_status(EFI_STATUS status) {
    char hex[19] = "0x0000000000000000";
    unsigned i;
    for (i = 0; i < 16; i++) hex[17-i] = "0123456789abcdef"[(status >> (i*4)) & 15];
    log_text(hex); log_text("\n");
}

static EFI_STATUS load(EFI_HANDLE self, EFI_HANDLE device, CHAR16 *path, EFI_HANDLE *child) {
    EFI_DEVICE_PATH *dp = FileDevicePath(device, path);
    EFI_STATUS status;
    if (!dp) return EFI_OUT_OF_RESOURCES;
    status = uefi_call_wrapper(BS->LoadImage, 6, FALSE, self, dp, NULL, 0, child);
    FreePool(dp);
    return status;
}

EFI_STATUS efi_main(EFI_HANDLE self, EFI_SYSTEM_TABLE *system) {
    EFI_GUID global = EFI_GLOBAL_VARIABLE;
    EFI_LOADED_IMAGE *image;
    EFI_HANDLE child = NULL;
    EFI_STATUS status;
    UINT8 secure = 0, setup = 1;
    UINTN size = 1, i;
    CHAR16 *bad[] = {L"\\EFI\\BOOT\\unsigned.efi", L"\\EFI\\BOOT\\untrusted.efi", L"\\EFI\\BOOT\\tampered.efi"};
    const char *ok[] = {"PASS unsigned rejected\n", "PASS untrusted signer rejected\n", "PASS tampered image rejected\n"};
    InitializeLib(self, system);
    status = uefi_call_wrapper(RT->GetVariable, 5, L"SecureBoot", &global, NULL, &size, &secure);
    if (EFI_ERROR(status) || secure != 1) { log_text("FAIL SecureBoot != 1\n"); return EFI_SECURITY_VIOLATION; }
    size = 1;
    status = uefi_call_wrapper(RT->GetVariable, 5, L"SetupMode", &global, NULL, &size, &setup);
    if (EFI_ERROR(status) || setup != 0) { log_text("FAIL SetupMode != 0\n"); return EFI_SECURITY_VIOLATION; }
    log_text("PASS SecureBoot=1 SetupMode=0\n");
    status = uefi_call_wrapper(BS->HandleProtocol, 3, self, &LoadedImageProtocol, (VOID **)&image);
    if (EFI_ERROR(status)) return status;
    for (i = 0; i < 3; i++) {
        child = NULL;
        status = load(self, image->DeviceHandle, bad[i], &child);
        log_text("Negative LoadImage status: "); log_status(status);
        if (child) uefi_call_wrapper(BS->UnloadImage, 1, child);
        /* OVMF's deny policy returns ACCESS_DENIED rather than deferring an
         * image with SECURITY_VIOLATION. Neither permits execution. */
        if (status != EFI_SECURITY_VIOLATION && status != EFI_ACCESS_DENIED) {
            log_text("FAIL expected security rejection\n"); return EFI_SECURITY_VIOLATION;
        }
        log_text(ok[i]);
    }
    child = NULL;
    status = load(self, image->DeviceHandle, L"\\EFI\\BOOT\\refind-signed.efi", &child);
    if (EFI_ERROR(status)) { log_text("FAIL signed rEFInd rejected\n"); return status; }
    log_text("PASS signed rEFInd accepted; starting\n");
    return uefi_call_wrapper(BS->StartImage, 3, child, NULL, NULL);
}
