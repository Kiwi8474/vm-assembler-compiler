#org 0x300
#sectors 2
#sector 1

asm {
    mov r14, 0xFFFFFFFF;
    mov r0, 0x20;
    mov r1, 2;
    out r0, r1; 
}

def uint32 index;
def uint32 vga;

while uint32 $index < 307200 {
    uint32 vga = uint32 $index + 0x100000;
    
    asm {
        mov r0, index;
        mul r0, 3;
        add r0, 50;
        sub r0, index;
        mov r1, r0;
    }
    
    asm {
        mov r2, vga;
        mov.d r3, [r2];
        mov.b [r3], r1;
    }

    uint32 index = uint32 $index + 1;
}

while 1 == 1 {}