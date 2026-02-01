#org 0x400

uint8 0x87D0 = 1;
uint16 0x87D2 = 0x8000;

mainloop:
if uint8 $0x87D0 == 1 {
    uint8 0x87D1 = uint8 $0xFFFF;

    if uint8 $0x87D1 != 0 {
        if uint8 $0x87D1 == 'q' {
            goto end_mainloop;
        }

        uint8 $0x87D2 = uint8 $0x87D1;
        if uint16 $0x87D2 != 0x87CF {
            uint16 0x87D2 = uint16 $0x87D2 + 1;
        }


    }

    goto mainloop;
}
end_mainloop:

out 0x1, 'D';
out 0x1, 'o';
out 0x1, 'n';
out 0x1, 'e';
out 0x1, 10;
done:
goto done;