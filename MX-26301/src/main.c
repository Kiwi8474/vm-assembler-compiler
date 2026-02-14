#org 0x300
#sectors 2
#sector 1

asm {
    mov r14, 0xFFFFFFFF; // Stack Pointer auf 32 bit Stack initialisieren
    mov r0, 0x20;
    mov r1, 2;
    out r0, r1; // Pixelmodus einschalten
}

def uint32 addr;
def uint32 color;
void draw(addr, color) {
    asm {
        mov r2, color;
        mov.d r0, [r2];
        mov r3, addr;
        mov.d r1, [r3];
        mov.b [r1], r0;
    }
    return;
}

def uint8 x = 10;
def uint8 y = 5;
uint8 y = uint8 $y + 1;
out 2, uint8 $y;

while 1 == 1 {}