#define text_cursor 0x87D2
uint16 text_cursor = 0x8000;

#export print
#export strcmp
#export scroll

void print(arg) { // erwartet string-adresse auf dem stack
    #define arg 0x87E0
    #define str_addr 0x87E2
    #define char 0x87E4

    uint16 str_addr = $$arg;

    print_loop:
    uint16 char = uint8 $$str_addr;

    if $char != 0 {
        if $char == 10 {
            uint16 text_cursor = uint16 $text_cursor - ((uint16 $text_cursor - 0x8000) % 80) + 80;
            if uint16 $text_cursor > 0x87CF {
                scroll();
            }
            goto next_char;
        }

        uint8 $text_cursor = $char;
        uint16 text_cursor = $text_cursor + 1;

        if uint16 $text_cursor > 0x87CF {
            scroll();
        }

        next_char:
        uint16 str_addr = $str_addr + 1;
        goto print_loop;
    } else {
        goto print_end;
    }

    print_end:
    return;
}

void strcmp(str_1, str_2) { // erwartet zwei string-adressen auf dem stack
    #define str_1 0x87E0
    #define str_2 0x87E2

    strcmp_loop:
    if uint8 $$$str_1 != uint8 $$$str_2 {
        return 1;
    }

    if uint8 $$$str_1 == 0 {
        return 0;
    }

    if uint8 $$$str_2 == 0 {
        return 0;
    }

    uint16 $str_1 = uint16 $$str_1 + 1;
    uint16 $str_2 = uint16 $$str_2 + 1;
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
    uint16 text_cursor = 0x8780;
    return;
}