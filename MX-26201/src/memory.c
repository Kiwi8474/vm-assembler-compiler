#ifndef MEMORY_H
#define MEMORY_H

#export memcpy
#export memset
#export memset16
#export load
#export draw_asset

def uint16 memcpy_source;
def uint16 memcpy_target;
def uint16 memcpy_size;
def uint16 memcpy_index;
void memcpy(memcpy_source, memcpy_target, memcpy_size) {
    uint16 memcpy_index = 0;

    while uint16 $memcpy_index < uint16 $memcpy_size {
        uint8 $(uint16 $memcpy_target + uint16 $memcpy_index) = uint8 $(uint16 $memcpy_source + uint16 $memcpy_index);
        uint16 memcpy_index = uint16 $memcpy_index + 1;
    }
    return;
}

def uint16 memset_target;
def uint16 memset_val;
def uint16 memset_size;
def uint16 memset_index;
void memset(memset_target, memset_val, memset_size) {
    uint16 memset_index = 0;
    while uint16 $memset_index < uint16 $memset_size {
        uint8 $(uint16 $memset_target + uint16 $memset_index) = uint8 $memset_val;
        uint16 memset_index = uint16 $memset_index + 1;
    }
    return;
}

def uint16 memset16_target;
def uint16 memset16_val;
def uint16 memset16_size;
def uint16 memset16_index;
void memset16(memset16_target, memset16_val, memset16_size) {
    uint16 memset16_index = 0;
    while uint16 $memset16_index < uint16 $memset16_size {
        uint16 $(uint16 $memset16_target + uint16 $memset16_index) = uint16 $memset16_val;
        uint16 memset16_index = uint16 $memset16_index + 1;
    }
    return;
}

def uint16 load_sector;
def uint16 load_addr;
void load(load_sector, load_addr) {
    out 0x10, uint16 $load_sector;
    out 0x11, uint16 $load_addr;
    out 0x12, 1;
    return;
}

def uint16 draw_asset_source;
def uint16 draw_asset_target;
def uint16 draw_asset_width;
def uint16 draw_asset_height;
def uint16 draw_asset_index;
def uint16 draw_asset_current_source;
def uint16 draw_asset_current_target;
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