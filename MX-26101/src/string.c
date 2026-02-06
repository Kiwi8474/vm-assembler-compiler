#ifndef STRING_H
#define STRING_H

#export strcmp
#export memcpy

def uint16 strcmp_string_addr_1 = 0;
def uint16 strcmp_string_addr_2 = 0;
def uint16 strcmp_result = 0;
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

def uint16 memcpy_source = 0;
def uint16 memcpy_target = 0;
def uint16 memcpy_size = 0;
def uint16 memcpy_index = 0;
void memcpy(memcpy_source, memcpy_target, memcpy_size) {
    uint16 memcpy_index = 0;

    while uint16 $memcpy_index < uint16 $memcpy_size {
        uint8 $(uint16 $memcpy_target + uint16 $memcpy_index) = uint8 $(uint16 $memcpy_source + uint16 $memcpy_index);
        uint16 memcpy_index = uint16 $memcpy_index + 1;
    }
    return;
}

#endif