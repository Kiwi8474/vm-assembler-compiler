#ifndef STDIO_H
#define STDIO_H

def uint16 text_cursor = 0x8000;

#export text_cursor

#export print
#export scroll
#export cls

def uint16 temp_calc;

def uint16 print_string_addr;
def uint16 print_string_ptr;
def uint16 print_string_char;
void print(print_string_addr) { // erwartet string-adresse auf dem stack
    uint16 print_string_ptr = uint16 $print_string_addr;

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

void scroll() {
    memcpy(0x80A0, 0x8050, 1920);
    memset(0x8780, 0x20, 80);
    uint16 text_cursor = 0x8780;
    return;
}

void cls() {
    memset(0x8000, 0x20, 2000);
    uint16 text_cursor = 0x8000;
    return;
}

#endif