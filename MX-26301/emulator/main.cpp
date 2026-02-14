/*
MX-26301
*/

#include <iostream>
#include <cstdint>
#include <vector>
#include <deque>
#include <fstream>
#include <chrono>
#include <conio.h>
#include <windows.h>
#include <csignal>

#include "vm.hpp"
#include "shared_struct.hpp"

/*
===============================================================================
Memory Map
===============================================================================
0x00000000 - 0x000001FF : BIOS (512 Bytes)                 - Hardkodiertes ROM-Programm
0x00000200 - 0x000003FF : Boot Sektor (512 Bytes)          - Sektor 0 der Disk
0x00000400 - 0x000FFFFF : Low RAM (767 KiB)                - Kernel & Programme
0x00100000 - 0x0014B000 : VRAM (300 KiB)                   - Grafikspeicher
0x0014B001 - 0xFFFFBFFF : General RAM (~3.9989 GiB)        - Hauptspeicher für alle Berechnungen, Daten & Assets
0xFFFFA000 - 0xFFFFFFFF : Stack (16 KiB)                   - Platz für 2048 dwords
===============================================================================
*/

VM* g_vm_ptr = nullptr;
void handle_ctrl_c(int signum);

void VM::handleInput() {
    if (shared_memory && shared_memory->key != 0) {
        key_buffer.push_back(shared_memory->key);
        shared_memory->key = 0;
    }
}

void VM::setupSharedMemory() {
    hMapFile = CreateFileMappingA(
        INVALID_HANDLE_VALUE,
        NULL,
        PAGE_READWRITE,
        0,
        sizeof(SharedData),
        "Local\\MX-26301_VM_SharedMemory"
    );

    if (hMapFile == NULL) {
        std::cerr << "Couldn't create shared memory." << std::endl;
        return;
    }

    shared_memory = (SharedData*)MapViewOfFile(
        hMapFile,
        FILE_MAP_ALL_ACCESS,
        0, 0, sizeof(SharedData)
    );
}

VM::VM() : regs(16, 0), memory(4294967296, 0) {
    setupSharedMemory();

    // BIOS (bleibt 16 bit für legacy-support)
    std::vector<uint8_t> bios_rom = {
        0x20, 0x00, 0x10, // movi r0, 0x10
        0x21, 0x00, 0x00, // movi r1, 0
        0x70, 0x10, 0x00, // out r0, r1 (sektor setzen)
        0x20, 0x00, 0x11, // movi r0, 0x11
        0x21, 0x02, 0x00, // movi r1, 0x200
        0x70, 0x10, 0x00, // out r0, r1 (ladeadresse setzen)
        0x20, 0x00, 0x12, // movi r0, 0x12
        0x21, 0x00, 0x01, // movi r1, 1
        0x70, 0x10, 0x00, // out r0, r1 (sektor 0 an 0x200 laden)
        0x2e, 0xaf, 0xff, // movi r14, 0xafff (stack pointer)
        0x2f, 0x02, 0x00  // movi r15, 0x200 (programmstart)
    };
    bios_rom.resize(512, 0);
    
    bios_rom[0x101] = 3; // Grafiktyp (uint16 0x0100)
    bios_rom[0x103] = 1; // Disk-Ports (uint16 0x0102)
    bios_rom[0x105] = 1; // Buzzer-Ports (uint16 0x0104)
    bios_rom[0x107] = 2; // Wait-Port (uint16 0x0106)

    std::copy(bios_rom.begin(), bios_rom.end(), memory.begin());

    std::ifstream file(DISK, std::ios::binary | std::ios::ate);
    if (file.is_open()) {
        std::streamsize size = file.tellg();
        file.seekg(0, std::ios::beg);
        disk_content.resize(size);
        file.read((char*)disk_content.data(), size);
    } else {
        disk_content.resize(1440 * 1024, 0);
    }

    jit_buffer = (uint8_t*)VirtualAlloc(NULL, JIT_MAX_SIZE, MEM_COMMIT, PAGE_EXECUTE_READWRITE);

    regs[15] = 0x00000000;
}

VM::~VM() {
    UnmapViewOfFile(shared_memory);
    CloseHandle(hMapFile);
}

void VM::updateSharedMemory(double current_ips) {
    if (shared_memory) {
        memcpy(shared_memory->vram, &memory[VRAM_START], 307200);
        shared_memory->ips = current_ips;
    }
}

void VM::step() {
    if (cpu_bit_width == 0) {
        execute_16_bit();
    } else if (cpu_bit_width == 1) {
        execute_32_bit();
    }
}

void VM::stop() { running = false; }

void VM::run() {
    auto last_ips_time = std::chrono::high_resolution_clock::now();
    long cycles_since_last_ips = 0;
    double current_ips = 0;

    int timing_counter = 1000000; 

    while (running) {
        step();
        cycles_since_last_ips++;
        timing_counter--;

        if (!(cycles_since_last_ips & 8191)) {
            handleInput();
            if (vram_changed && shared_memory) {
                memcpy(shared_memory->vram, &memory[VRAM_START], 307200);
                shared_memory->ips = current_ips;
                vram_changed = false;
            }
        }

        if (timing_counter <= 0) {
            auto now = std::chrono::high_resolution_clock::now();
            std::chrono::duration<double> elapsed = now - last_ips_time;
            
            if (elapsed.count() >= 0.5) {
                current_ips = cycles_since_last_ips / elapsed.count();

                if (shared_memory) {
                    shared_memory->ips = current_ips;
                }

                cycles_since_last_ips = 0;
                last_ips_time = now;
            }
            timing_counter = 1000000;
        }
    }
}

void VM::dump() {
    for (int i = 0; i < 16; i++) {
        std::cout << "r" << i << ": " << regs[i] << " / 0x" << std::hex << regs[i] << std::dec << std::endl;
    }
    std::cout << "0xFFFF: " << (int)memory[65535] << " / 0x" << std::hex << int(memory[65535]) << std::dec;
}

void handle_ctrl_c(int signum) {
    if (g_vm_ptr) {
        g_vm_ptr->stop(); 
    }
}

int main() {
    VM vm = VM();
    g_vm_ptr = &vm;
    std::signal(SIGINT, handle_ctrl_c);
    vm.run();
    vm.dump();
    system("pause");
    return 0;
}