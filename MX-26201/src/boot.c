#org 0x200
#sector 0
#sectors 1

def uint16 sector;
def uint16 addr;
void load(sector, addr) {
    out 0x10, uint16 $sector;
    out 0x11, uint16 $addr;
    out 0x12, 1;
    return;
}

load(1, 0x400);
load(2, 0x600);
load(3, 0x800);
load(4, 0xA00);
load(5, 0xC00);
load(6, 0xE00);
load(7, 0x1000);
load(8, 0x1200);
load(9, 0x1400);

load(10, 0x2000);
load(11, 0x2200);
load(12, 0x2400);
load(13, 0x2600);

goto 0x2000;