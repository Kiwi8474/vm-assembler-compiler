#org 0x400

0x7000 = 1;
0x87D0 = 2 + (3 * 4);
out 0x2, $0x87D0;

loop:
if $0x7000 == 1 {
    if $0xFFFF == 113 {
        0x7000 = 0;
    }
    goto loop;
}

goto 0xFFFF;

done:
goto done;