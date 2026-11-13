#include <assert.h>
#include <stdio.h>
typedef unsigned char UINT8;
typedef unsigned long UINTN;
typedef struct { UINT8 b,g,r,a; } EG_PIXEL;
typedef struct { UINTN Width,Height; int HasAlpha; EG_PIXEL *PixelData; } EG_IMAGE;
#include "../refind/selection_fx.h"
int main(void) {
    EG_PIXEL pixels[]={{255,100,50,128},{0,255,200,0}};
    EG_IMAGE image={2,1,1,pixels};
    GrubzDimImage(&image,32);
    assert(pixels[0].b==82 && pixels[0].g==32 && pixels[0].r==16);
    assert(pixels[0].a==128 && pixels[1].a==0);
    GrubzDimImage(&image,0);
    assert(pixels[0].b==0 && pixels[1].r==0 && pixels[0].a==128);
    EG_PIXEL unchanged[]={{12,200,255,77}};
    EG_IMAGE original={1,1,1,unchanged};
    GrubzDimImage(&original,100);
    assert(unchanged[0].r==255 && unchanged[0].g==200 && unchanged[0].a==77);
    GrubzDimImage(&original,999);
    assert(unchanged[0].r==255 && unchanged[0].g==200 && unchanged[0].a==77);
    assert(GrubzPosition(0,440,0)==0);
    assert(GrubzPosition(0,440,1024)==440);
    assert(GrubzPosition(440,0,512)==220);
    assert(GrubzPosition(440,0,1024)==0);
    assert(GrubzPosition(100,32,512)==66);
    assert(GrubzEase(0)==0 && GrubzEase(1024)==1024 && GrubzEase(512)==512);
    unsigned last=0;
    for(unsigned i=0;i<=1024;i++){unsigned next=GrubzEase(i);assert(next>=last && next<=1024);last=next;}
    puts("selection rendering tests passed");
}
