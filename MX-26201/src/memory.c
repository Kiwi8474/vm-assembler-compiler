#ifndef MEMORY_H
#define MEMORY_H

#export memcpy
#export memset
#export memset16
#export load
#export draw_asset

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

def uint16 memset_target = 0;
def uint16 memset_val = 0;
def uint16 memset_size = 0;
def uint16 memset_index = 0;
void memset(memset_target, memset_val, memset_size) {
    uint16 memset_index = 0;
    while uint16 $memset_index < uint16 $memset_size {
        uint8 $(uint16 $memset_target + uint16 $memset_index) = uint8 $memset_val;
        uint16 memset_index = uint16 $memset_index + 1;
    }
    return;
}

def uint16 memset16_target = 0;
def uint16 memset16_val = 0;
def uint16 memset16_size = 0;
def uint16 memset16_index = 0;
void memset16(memset16_target, memset16_val, memset16_size) {
    uint16 memset16_index = 0;
    while uint16 $memset16_index < uint16 $memset16_size {
        uint16 $(uint16 $memset16_target + uint16 $memset16_index) = uint16 $memset16_val;
        uint16 memset16_index = uint16 $memset16_index + 1;
    }
    return;
}

def uint16 load_sector = 0;
def uint16 load_addr = 0;
void load(load_sector, load_addr) {
    out 0x10, uint16 $load_sector;
    out 0x11, uint16 $load_addr;
    out 0x12, 1;
    return;
}

def uint16 draw_asset_source = 0;
def uint16 draw_asset_target = 0;
def uint16 draw_asset_width = 0;
def uint16 draw_asset_height = 0;
def uint16 draw_asset_index = 0;
def uint16 draw_asset_current_source = 0;
def uint16 draw_asset_current_target = 0;
void draw_asset(draw_asset_source, draw_asset_target, draw_asset_width, draw_asset_height) {
    uint16 draw_asset_index = 0;

    while uint16 $draw_asset_index < uint16 $draw_asset_height {
        uint16 draw_asset_current_source = uint16 $draw_asset_source + (uint16 $draw_asset_index * uint16 $draw_asset_width);
        uint16 draw_asset_current_target = uint16 $draw_asset_target + (uint16 $draw_asset_index * 80);

        memcpy(uint16 $draw_asset_current_source, uint16 $draw_asset_current_target, uint16 $draw_asset_width);

        uint16 draw_asset_index = uint16 $draw_asset_index + 1;
    }
    return;
}

#endif