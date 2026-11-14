#!/usr/bin/env python3
"""Exercise the actual firmware scaler on a bounded-color 1600→1920 image."""
import os
import subprocess
import tempfile
from pathlib import Path

source = Path('libeg/image.c').read_text()
function = source[source.index('EG_IMAGE * egScaleImage('):source.index('VOID egFreeImage(')]
multiplier = next(line for line in source.splitlines() if line.startswith('#define FP_MULTIPLIER'))
prefix = r'''
#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
typedef size_t UINTN;
typedef struct { unsigned char b,g,r,a; } EG_PIXEL;
typedef struct { UINTN Width,Height; int HasAlpha; EG_PIXEL *PixelData; } EG_IMAGE;
#define IN
#define LOG(...) ((void)0)
static EG_IMAGE *egCreateImage(UINTN w, UINTN h, int alpha) {
 EG_IMAGE *p=calloc(1,sizeof(*p)); assert(p);
 p->Width=w; p->Height=h; p->HasAlpha=alpha;
 p->PixelData=calloc(w*h,sizeof(EG_PIXEL)); assert(p->PixelData); return p;
}
static EG_IMAGE *egCopyImage(EG_IMAGE *p) {
 EG_IMAGE *q=egCreateImage(p->Width,p->Height,p->HasAlpha);
 memcpy(q->PixelData,p->PixelData,p->Width*p->Height*sizeof(EG_PIXEL)); return q;
}
'''
suffix = r'''
int main(void) {
 EG_IMAGE *p=egCreateImage(1600,900,1);
 for (size_t i=0;i<1600*900;i++) p->PixelData[i]=(EG_PIXEL){i%2,(i/2)%2,(i/3)%2,255};
 EG_IMAGE *q=egScaleImage(p,1920,1080);
 for (size_t i=0;i<1920*1080;i++) {
  EG_PIXEL v=q->PixelData[i];
  assert(v.r<=1 && v.g<=1 && v.b<=1 && v.a==255);
 }
 free(p->PixelData);free(p);free(q->PixelData);free(q);
 puts("Image scaling tests passed: bounded colors and alpha at 1920x1080");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp)/'scale.c'
    c.write_text(prefix+'\n'+multiplier+'\n'+function+suffix)
    binary = Path(tmp)/'scale'
    subprocess.run([os.environ.get('CC','cc'),'-std=c99','-Wall','-Wextra','-Werror',
                    '-fsanitize=undefined',str(c),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
