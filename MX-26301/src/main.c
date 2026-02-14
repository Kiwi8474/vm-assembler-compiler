#org 0x300
#sectors 6
#sector 1

asm {
    mov r14, 0xFFFFFFFF;
    mov r0, 0x20;
    mov r1, 2;
    out r0, r1; 
}

def uint32 triangle_coords;
void triangle(triangle_coords) {
    asm {
        mov r5, triangle_coords;
        mov r5, [r5];

        mov.d r0, [r5];
        shl r0, 16;
        mov r6, r5;
        add r6, 4;
        mov.d r4, [r6];
        or r0, r4;

        mov r6, r5;
        add r6, 8;
        mov.d r1, [r6];
        shl r1, 16;

        mov r6, r5;
        add r6, 12;
        mov.d r4, [r6];
        or r1, r4;

        mov r6, r5;
        add r6, 16;
        mov.d r2, [r6];
        shl r2, 16;

        mov r6, r5;
        add r6, 20;
        mov.d r4, [r6];
        or r2, r4;

        mov r3, 0xff;

        gpuline r0, r1, r3;
        gpuline r1, r2, r3;
        gpuline r0, r2, r3;
    }
    return;
}

void set_tri_arrays() {
    uint32 quad_tri1[0] = uint32 $Ax;
    uint32 quad_tri1[1] = uint32 $Ay;
    uint32 quad_tri1[2] = uint32 $Bx;
    uint32 quad_tri1[3] = uint32 $By;
    uint32 quad_tri1[4] = uint32 $Cx;
    uint32 quad_tri1[5] = uint32 $Cy;

    uint32 quad_tri2[0] = uint32 $Ax;
    uint32 quad_tri2[1] = uint32 $Ay;
    uint32 quad_tri2[2] = uint32 $Cx;
    uint32 quad_tri2[3] = uint32 $Cy;
    uint32 quad_tri2[4] = uint32 $Dx;
    uint32 quad_tri2[5] = uint32 $Dy;

    return;
}

def uint32 quad_tri1[6];
def uint32 quad_tri2[6];

def uint32 Ax; def uint32 Ay; // Oben links
def uint32 Bx; def uint32 By; // Oben rechts
def uint32 Cx; def uint32 Cy; // Unten rechts
def uint32 Dx; def uint32 Dy; // Unten links

// Front
uint32 Ax = 100; uint32 Ay = 100;
uint32 Bx = 300; uint32 By = 100;
uint32 Cx = 300; uint32 Cy = 300;
uint32 Dx = 100; uint32 Dy = 300;
set_tri_arrays();
triangle(uint32 quad_tri1);
triangle(uint32 quad_tri2);

// Hinten
uint32 Ax = 150; uint32 Ay = 50;
uint32 Bx = 350; uint32 By = 50;
uint32 Cx = 350; uint32 Cy = 250;
uint32 Dx = 150; uint32 Dy = 250;
set_tri_arrays();
triangle(uint32 quad_tri1);
triangle(uint32 quad_tri2);

// Rechts
uint32 Ax = 300; uint32 Ay = 100;
uint32 Bx = 350; uint32 By = 50;
uint32 Cx = 350; uint32 Cy = 250;
uint32 Dx = 300; uint32 Dy = 300;
set_tri_arrays();
triangle(uint32 quad_tri1);
triangle(uint32 quad_tri2);

// Links
uint32 Ax = 150; uint32 Ay = 50;
uint32 Bx = 100; uint32 By = 100;
uint32 Cx = 100; uint32 Cy = 300;
uint32 Dx = 150; uint32 Dy = 250;
set_tri_arrays();
triangle(uint32 quad_tri1);
triangle(uint32 quad_tri2);

// Oben
uint32 Ax = 150; uint32 Ay = 50;
uint32 Bx = 350; uint32 By = 50;
uint32 Cx = 300; uint32 Cy = 100;
uint32 Dx = 100; uint32 Dy = 100;
set_tri_arrays();
triangle(uint32 quad_tri1);
triangle(uint32 quad_tri2);

// Unten
uint32 Ax = 100; uint32 Ay = 300;
uint32 Bx = 300; uint32 By = 300;
uint32 Cx = 350; uint32 Cy = 250;
uint32 Dx = 150; uint32 Dy = 250;
set_tri_arrays();
triangle(uint32 quad_tri1);
triangle(uint32 quad_tri2);

while 1 == 1 {}