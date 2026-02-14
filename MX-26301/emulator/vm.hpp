#ifndef VM_HPP
#define VM_HPP

#include <vector>
#include <deque>
#include <windows.h>
#include "shared_struct.hpp"

#define VRAM_START 0x00100000
#define VRAM_END 0x0014B000
#define SCREEN_WIDTH 640
#define SCREEN_HEIGHT 480
#define DISK "disk.bin"

class VM {
private:
    std::vector<uint32_t> regs;
    std::vector<uint8_t> memory;
    std::deque<uint8_t> key_buffer;
    std::vector<uint8_t> disk_content;
    
    bool running = true;
    bool vram_changed = false;
    uint32_t disk_buffer_sector = 0;
    uint32_t disk_buffer_addr = 0;
    uint32_t buzzer_freq = 0;
    uint32_t buzzer_duration = 0;
    uint32_t cpu_bit_width = 0;

    SharedData* shared_memory = nullptr;
    HANDLE hMapFile = NULL;

    void handleInput();
    void setupSharedMemory();

public:
    VM();
    ~VM();
    
    void step();
    void run();
    void stop();
    void dump();
    void updateSharedMemory(double current_ips);

    void execute_16_bit();
    void execute_32_bit();

    uint32_t read_mem8(uint32_t addr, bool is_signed = false);
    uint32_t read_mem16(uint32_t addr, bool is_signed = false);
    uint32_t read_mem32(uint32_t addr, bool is_signed = false);

    void write_mem8(uint32_t addr, uint8_t val);
    void write_mem16(uint32_t addr, uint16_t val);
    void write_mem32(uint32_t addr, uint32_t val);
};

#endif