#ifndef STDIO_H
#define STDIO_H

def uint16 text_cursor = 0x8000;

#export text_cursor

#export print
#export strcmp
#export scroll

def uint16 print_string_addr = 0;
def uint16 print_string_ptr = 0;
def uint16 print_string_char = 0;
void print(print_string_addr) { // erwartet string-adresse auf dem stack
    uint16 print_string_ptr = uint16 $print_string_addr;

    print_loop:
    uint16 print_string_char = uint8 $$print_string_ptr;

    if uint16 $print_string_char != 0 {
        if uint16 $print_string_char == 10 {
            uint16 text_cursor = uint16 $text_cursor - ((uint16 $text_cursor - 0x8000) % 80) + 80;
            if uint16 $text_cursor > 0x87CF {
                scroll();
            }
            goto next_char;
        }

        uint8 $text_cursor = uint16 $print_string_char;
        uint16 text_cursor = uint16 $text_cursor + 1;

        if uint16 $text_cursor > 0x87CF {
            scroll();
        }

        next_char:
        uint16 print_string_ptr = uint16 $print_string_ptr + 1;
        goto print_loop;
    } else {
        goto print_end;
    }

    print_end:
    return;
}

def uint16 strcmp_string_addr_1 = 0;
def uint16 strcmp_string_addr_2 = 0;
void strcmp(strcmp_string_addr_1, strcmp_string_addr_2) { // erwartet zwei string-adressen auf dem stack

    strcmp_loop:
    if uint8 $$strcmp_string_addr_1 != uint8 $$strcmp_string_addr_2 {
        return 1;
    }

    if uint8 $$strcmp_string_addr_1 == 0 {
        return 0;
    }

    if uint8 $$strcmp_string_addr_2 == 0 {
        return 0;
    }

    uint16 strcmp_string_addr_1 = uint16 $strcmp_string_addr_1 + 1;
    uint16 strcmp_string_addr_2 = uint16 $strcmp_string_addr_2 + 1;
    goto strcmp_loop;
}

def uint16 scroll_current = 0;
def uint16 scroll_target = 0;
void scroll() {
    uint16 scroll_current = 0x8000;
    uint16 scroll_target = 0x8050;

    while uint16 $scroll_target < 0x87D0 {
        uint16 $scroll_current = uint16 $$scroll_target;

        uint16 scroll_current = uint16 $scroll_current + 2;
        uint16 scroll_target = uint16 $scroll_target + 2;
    }

    uint16 scroll_current = 0x8780; 
    while uint16 $scroll_current < 0x87D0 {
        uint16 $scroll_current = 0x2020; 
        uint16 scroll_current = uint16 $scroll_current + 2;
    }

    uint16 text_cursor = 0x8780; 
    
    return;
}

#endif