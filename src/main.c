#org 0x400
#sectors 2

#define running 0x87D0
#define text_cursor 0x87D2

uint8 running = 1;
uint16 text_cursor = 0x8000;

mainloop:
if uint8 $running == 1 {
    if uint8 $0xFFFF != 0 {
        if uint8 $0xFFFF == 255 {
            uint8 running = 0;
        }

        uint8 $text_cursor = uint8 $0xFFFF;
        if uint16 $text_cursor != 0x87CF {
            uint16 text_cursor = uint16 $text_cursor + 1;
        }

        uint8 0xFFFF = 0;
    }

    goto mainloop;
}

out 0x1, 'D';
out 0x1, 'o';
out 0x1, 'n';
out 0x1, 'e';
out 0x1, 10;
done:
goto done;