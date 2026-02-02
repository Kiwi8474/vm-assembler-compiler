#org 0x400
#sectors 2

#define KEY_IO 0xFFFF
#define VGA_END 0x87CF

#define running 0x87D0
#define text_cursor 0x87D2

uint8 running = 1;
uint16 text_cursor = 0x8000;

asm {
    movi r0, 1;
    movi r1, 65;
    out r0, r1;
}

void check_key_and_type() {
    if uint8 $KEY_IO != 0 {
        if uint8 $KEY_IO == 255 {
            uint8 running = 0;
        }

        uint8 $text_cursor = uint8 $KEY_IO;
        if uint16 $text_cursor != VGA_END {
            uint16 text_cursor = uint16 $text_cursor + 1;
        }

        uint8 KEY_IO = 0;
    }
    return;
}

mainloop:
if uint8 $running == 1 {
    check_key_and_type();
    goto mainloop;
}

out 0x1, 'D';
out 0x1, 'o';
out 0x1, 'n';
out 0x1, 'e';
out 0x1, 10;
done:
goto done;