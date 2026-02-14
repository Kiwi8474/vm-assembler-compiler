#ifndef SHARED_STRUCT_HPP
#define SHARED_STRUCT_HPP

#include <cstdint>

#pragma pack(push, 1)
struct SharedData {
    uint8_t vram[307200];
    double ips;
    uint8_t video_mode;
    uint8_t key;
    uint16_t mouse_x;
    uint16_t mouse_y;
    uint8_t mouse_btn;
};
#pragma pack(pop)

#endif