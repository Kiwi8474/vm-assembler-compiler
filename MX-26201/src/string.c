#ifndef STRING_H
#define STRING_H

#export strcmp

def uint16 strcmp_string_addr_1;
def uint16 strcmp_string_addr_2;
def uint16 strcmp_result;
void strcmp(strcmp_string_addr_1, strcmp_string_addr_2) { // erwartet zwei string-adressen auf dem stack

    strcmp_loop:
    if uint8 $$strcmp_string_addr_1 != uint8 $$strcmp_string_addr_2 {
        uint16 strcmp_result = 1;
        return uint16 $strcmp_result;
    }

    if uint8 $$strcmp_string_addr_1 == 0 {
        uint16 strcmp_result = 0;
        return uint16 $strcmp_result;
    }

    if uint8 $$strcmp_string_addr_2 == 0 {
        uint16 strcmp_result = 0;
        return uint16 $strcmp_result;
    }

    uint16 strcmp_string_addr_1 = uint16 $strcmp_string_addr_1 + 1;
    uint16 strcmp_string_addr_2 = uint16 $strcmp_string_addr_2 + 1;
    goto strcmp_loop;
}

#endif