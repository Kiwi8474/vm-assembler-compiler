#org 0x1000
#sector 10
#sectors 4

#define KEY_IO 0xFFFF
#define VGA_END 0x87CF

void check_key_and_type() {
    if uint8 $KEY_IO != 0 {
        if uint8 $KEY_IO == 'q' {
            uint16 running = 0;
        }

        if uint8 $KEY_IO == 8 {
            if uint16 $text_cursor != 0x8000 {
                uint16 text_cursor = uint16 $text_cursor - 1;
                uint8 $text_cursor = 32;
            }
            goto end_of_check;
        }

        if uint8 $KEY_IO == 13 {
            uint16 text_cursor = uint16 $text_cursor - ((uint16 $text_cursor - 0x8000) % 80) + 80;
            if uint16 $text_cursor > 0x87CF {
                scroll();
            }
            goto end_of_check;
        }

        uint8 $text_cursor = uint8 $KEY_IO;
        uint16 text_cursor = uint16 $text_cursor + 1;

        if uint16 $text_cursor > 0x87CF {
            scroll();
        }

        end_of_check:
        uint8 KEY_IO = 0;
    }
    return;
}

print("Hallo!\n");
print("Was geht?\n");

def uint16 combined_word = 0xABCD;
def uint8 high = 0;
def uint8 low = 0;
uint8 high = uint8 $combined_word;
uint8 low = uint8 $(combined_word+1);

def uint8 my_byte_array = {69, 0, 1, 2, 3, 4, 5};
def uint16 my_word_array = {0, 1, 2, 3, 4, 5};

def uint16 running = 1;
while uint16 $running == 1 {
    check_key_and_type();
}

print("Halt.\n");

while 1 == 1 {}