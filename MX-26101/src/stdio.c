#ifndef STDIO_H
#define STDIO_H

uint16 0x87D2 = 0x8000;

#export print
#export strcmp
#export scroll

void print(0x87E0) { // erwartet string-adresse auf dem stack

    uint16 0x87E2 = $$0x87E0;

    print_loop:
    uint16 0x87E4 = uint8 $$0x87E2;

    if $0x87E4 != 0 {
        if $0x87E4 == 10 {
            uint16 0x87D2 = uint16 $0x87D2 - ((uint16 $0x87D2 - 0x8000) % 80) + 80;
            if uint16 $0x87D2 > 0x87CF {
                scroll();
            }
            goto next_char;
        }

        uint8 $0x87D2 = $0x87E4;
        uint16 0x87D2 = $0x87D2 + 1;

        if uint16 $0x87D2 > 0x87CF {
            scroll();
        }

        next_char:
        uint16 0x87E2 = $0x87E2 + 1;
        goto print_loop;
    } else {
        goto print_end;
    }

    print_end:
    return;
}

void strcmp(0x87E0, 0x87E2) { // erwartet zwei string-adressen auf dem stack

    strcmp_loop:
    if uint8 $$$0x87E0 != uint8 $$$0x87E2 {
        return 1;
    }

    if uint8 $$$0x87E0 == 0 {
        return 0;
    }

    if uint8 $$$0x87E2 == 0 {
        return 0;
    }

    uint16 $0x87E0 = uint16 $$0x87E0 + 1;
    uint16 $0x87E2 = uint16 $$0x87E2 + 1;
    goto strcmp_loop;
}

void scroll() {
    asm {
        movi r0, 0x8000; 
        movi r1, 0x8050; 
        movi r2, 0x87D0;
        movi r5, 1; 
        movi r6, 32; 
    }

    scroll_loop:
    asm {
        movi r7, end_scroll; 
        je r1, r2, r7;

        peek r4, r1, r5;
        poke r4, r0, r5;

        add r0, r5;
        add r1, r5;
        
        movi r15, scroll_loop;
    }

    end_scroll:
    asm {
        movi r0, 0x8780;
    }

    clear_loop:
    asm {
        movi r7, done_scroll;
        je r0, r2, r7;

        poke r6, r0, r5;
        add r0, r5;
        
        movi r15, clear_loop; 
    }

    done_scroll:
    uint16 0x87D2 = 0x8780;
    return;
}

#endif