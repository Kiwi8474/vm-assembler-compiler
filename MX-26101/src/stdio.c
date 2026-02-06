#ifndef STDIO_H
#define STDIO_H

def uint16 text_cursor = 0x8000;

#export text_cursor

#export print
#export scroll
#export cls

def uint16 temp_calc = 0;

def uint16 print_string_addr = 0;
def uint16 print_string_ptr = 0;
def uint16 print_string_char = 0;
void print(print_string_addr) { // erwartet string-adresse auf dem stack
    uint8 print_string_ptr = uint16 $print_string_addr;

    print_loop:
    uint8 print_string_char = uint8 $$print_string_ptr;

    if uint8 $print_string_char != 0 {
        if uint8 $print_string_char == 10 {
            uint16 temp_calc = uint16 $text_cursor - 0x8000;
            while uint16 $temp_calc > 79 {
                uint16 temp_calc = uint16 $temp_calc - 80;
            }
            uint16 text_cursor = uint16 $text_cursor - uint16 $temp_calc + 80;

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

def uint16 scroll_current = 0;
def uint16 scroll_target = 0;
void scroll() {
    uint16 scroll_current = 0x8050;
    uint16 scroll_target = 0x80A0;

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

def uint16 cls_current = 0x8000;
void cls() {
    uint16 cls_current = 0x8000;
    while uint16 $cls_current < 0x87CF {
        uint16 $cls_current = 0x2020;
        uint16 cls_current = uint16 $cls_current + 2;
    }
    uint16 text_cursor = 0x8000;
    return;
}

#endif