#org 0x400
#sectors 16
#sector 1

asm {
    mov r14, 0xFFFFFFFF;
    mov r0, 0x20;
    mov r1, 2;
    out r0, r1; 
}

def uint32 sub_x;
def uint32 sub_y;
def uint32 sub_res;
void sub(sub_x, sub_y) {
    out 0x2, uint32 $sub_x;
    out 0x1, 32;
    out 0x2, uint32 $sub_y;
    out 0x1, 32;

    asm {
        mov r0, sub_x;
        mov r0, [r0];

        mov r1, sub_y;
        mov r1, [r1];

        sub r0, r1;
        mov r1, sub_res;
        mov [r1], r0;
    }

    out 0x2, uint32 $sub_res;
    out 0x1, 10;

    return uint32 $sub_res;
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

def uint32 x1; def uint32 y1;
def uint32 x2; def uint32 y2;
def uint32 x3; def uint32 y3;
def uint32 x4; def uint32 y4;
void set_tri_specific(x1, y1, x2, y2, x3, y3, x4, y4) {
    uint32 quad_tri1[0] = uint32 $x1;
    uint32 quad_tri1[1] = uint32 $y1;
    uint32 quad_tri1[2] = uint32 $x2;
    uint32 quad_tri1[3] = uint32 $y2;
    uint32 quad_tri1[4] = uint32 $x3;
    uint32 quad_tri1[5] = uint32 $y3;

    uint32 quad_tri2[0] = uint32 $x1;
    uint32 quad_tri2[1] = uint32 $y1;
    uint32 quad_tri2[2] = uint32 $x3;
    uint32 quad_tri2[3] = uint32 $y3;
    uint32 quad_tri2[4] = uint32 $x4;
    uint32 quad_tri2[5] = uint32 $y4;
    return;
}

def uint32 quad_tri1[6];
def uint32 quad_tri2[6];

def uint32 V1x; def uint32 V1y; // Vorne Oben Links
def uint32 V2x; def uint32 V2y; // Vorne Oben Rechts
def uint32 V3x; def uint32 V3y; // Vorne Unten Rechts
def uint32 V4x; def uint32 V4y; // Vorne Unten Links
def uint32 V5x; def uint32 V5y; // Hinten Oben Links
def uint32 V6x; def uint32 V6y; // Hinten Oben Rechts
def uint32 V7x; def uint32 V7y; // Hinten Unten Rechts
def uint32 V8x; def uint32 V8y; // Hinten Unten Links

def uint32 cube_x;
def uint32 cube_y;
def uint32 cube_size;
def uint32 cube_depth;
void cube(cube_x, cube_y, cube_size, cube_depth) {
    // 1. Koordinaten berechnen
    uint32 V1x = uint32 $cube_x; 
    uint32 V1y = uint32 $cube_y;
    uint32 V2x = uint32 $cube_x + uint32 $cube_size; 
    uint32 V2y = uint32 $cube_y;
    uint32 V3x = uint32 $cube_x + uint32 $cube_size; 
    uint32 V3y = uint32 $cube_y + uint32 $cube_size;
    uint32 V4x = uint32 $cube_x; 
    uint32 V4y = uint32 $cube_y + uint32 $cube_size;

    uint32 V5x = uint32 $cube_x + uint32 $cube_depth; 
    uint32 V5y = uint32 $cube_y - uint32 $cube_depth;
    uint32 V6x = (uint32 $cube_x + uint32 $cube_size) + uint32 $cube_depth; 
    uint32 V6y = uint32 $cube_y - uint32 $cube_depth;
    uint32 V7x = (uint32 $cube_x + uint32 $cube_size) + uint32 $cube_depth;
    uint32 V7y = (uint32 $cube_y + uint32 $cube_size) - uint32 $cube_depth;
    uint32 V8x = uint32 $cube_x + uint32 $cube_depth;
    uint32 V8y = (uint32 $cube_y + uint32 $cube_size) - uint32 $cube_depth;

    // 2. Zeichnen
    // Vorne
    set_tri_specific(uint32 $V1x, uint32 $V1y, uint32 $V2x, uint32 $V2y, uint32 $V3x, uint32 $V3y, uint32 $V4x, uint32 $V4y);
    triangle(uint32 quad_tri1); triangle(uint32 quad_tri2);
    // Hinten
    set_tri_specific(uint32 $V5x, uint32 $V5y, uint32 $V6x, uint32 $V6y, uint32 $V7x, uint32 $V7y, uint32 $V8x, uint32 $V8y);
    triangle(uint32 quad_tri1); triangle(uint32 quad_tri2);
    // Links
    set_tri_specific(uint32 $V1x, uint32 $V1y, uint32 $V5x, uint32 $V5y, uint32 $V8x, uint32 $V8y, uint32 $V4x, uint32 $V4y);
    triangle(uint32 quad_tri1); triangle(uint32 quad_tri2);
    // Rechts
    set_tri_specific(uint32 $V2x, uint32 $V2y, uint32 $V6x, uint32 $V6y, uint32 $V7x, uint32 $V7y, uint32 $V3x, uint32 $V3y);
    triangle(uint32 quad_tri1); triangle(uint32 quad_tri2);
    // Oben
    set_tri_specific(uint32 $V1x, uint32 $V1y, uint32 $V2x, uint32 $V2y, uint32 $V6x, uint32 $V6y, uint32 $V5x, uint32 $V5y);
    triangle(uint32 quad_tri1); triangle(uint32 quad_tri2);
    // Unten
    set_tri_specific(uint32 $V4x, uint32 $V4y, uint32 $V3x, uint32 $V3y, uint32 $V7x, uint32 $V7y, uint32 $V8x, uint32 $V8y);
    triangle(uint32 quad_tri1); triangle(uint32 quad_tri2);
    return;
}

cube(100, 100, 200, 50);

while 1 == 1 {}