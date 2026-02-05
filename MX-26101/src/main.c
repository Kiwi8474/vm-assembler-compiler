#org 0x1000
#sector 10
#sectors 4

#define text_cursor 0x87D2
uint16 text_cursor = 0x8000;

#define KEY_IO 0xFFFF
#define VGA_END 0x87CF

#define running 0x87D0

uint8 running = 1;

void check_key_and_type() {
    if uint8 $KEY_IO != 0 {
        if uint8 $KEY_IO == 'q' {
            uint8 running = 0;
        }

        if uint8 $KEY_IO == 8 {
            if uint16 $text_cursor != 0x8000 {
                uint16 text_cursor = $text_cursor - 1;
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

uint16 0x87F0 = "Hallo, Welt!";
print(0x87F0);

uint16 0x87F2 = "\nNewline!";
print(0x87F2);

if strcmp(0x87F0, 0x87F2) == 0 {
    uint16 0x87F0 = "\nStrings sind gleich!\n";
} else {
    uint16 0x87F0 = "\nStrings sind nicht gleich!\n";
}
print(0x87F0);

while uint8 $running == 1 {
    check_key_and_type();
}

while 1 == 1 {}