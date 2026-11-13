/* Grubz selection rendering helpers. GPL-3.0-or-later. */
#ifndef GRUBZ_SELECTION_FX_H
#define GRUBZ_SELECTION_FX_H

/* RGB brightness only: alpha and the caller's original asset stay intact. */
static void GrubzDimImage(EG_IMAGE *Image, unsigned Percent) {
    UINTN i;
    if (Percent > 100) Percent = 100;
    for (i = 0; i < Image->Width * Image->Height; i++) {
        Image->PixelData[i].r = (Image->PixelData[i].r * Percent + 50) / 100;
        Image->PixelData[i].g = (Image->PixelData[i].g * Percent + 50) / 100;
        Image->PixelData[i].b = (Image->PixelData[i].b * Percent + 50) / 100;
    }
}

/* Smoothstep, fixed point 0..1024; no floating point in firmware. */
static unsigned GrubzEase(unsigned T) {
    if (T >= 1024) return 1024;
    return (T * T * (3072 - 2 * T) + 524288) / 1048576;
}

/* Weighted endpoints avoid unsigned underflow when sliding right-to-left. */
static UINTN GrubzPosition(UINTN From, UINTN To, unsigned Progress) {
    if (Progress > 1024) Progress = 1024;
    return (From * (1024 - Progress) + To * Progress + 512) / 1024;
}
#endif
