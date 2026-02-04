/*
MX-26101
*/

#include <iostream>
#include <cstdint>
#include <vector>
#include <deque>
#include <fstream>
#include <chrono>
#include <conio.h>
#include <windows.h>

#define DISK "disk.bin"
#define VRAM_START 0x8000
#define VRAM_END 0x87CF

#pragma pack(push, 1)
struct SharedData {
    uint8_t vram[2000];
    double ips;
    uint8_t key;
    uint8_t mouse_x;
    uint8_t mouse_y;
    uint8_t mouse_btn;
};
#pragma pack(pop)

/*
===============================================================================
Memory Map
===============================================================================
0x0000 - 0x01FF : BIOS (512 Bytes)                 - Hardkodiertes ROM-Programm
0x0200 - 0x03FF : Boot Sektor (512 Bytes)          - Sektor 0 der Disk
0x0400 - 0x7FFF : Freier RAM (31 KiB)              - Kernel & Programme
0x8000 - 0x87CF : VRAM (2000 Bytes)                - Grafikspeicher
0x87D0 - 0xABFF : Low-RAM (9264 Bytes / ~9.05 KiB)
0xAC00 - 0xAFFF : Stack (1 KiB)                    - Platz für 512 Words
0xB000 - 0xFFFB : High-RAM (20475 Bytes / ~20 KiB)
0xFFFC          : Mausknopf MMIO Port (1 Byte)
0xFFFD          : Maus-Y MMIO Port (1 Byte)
0xFFFE          : Maus-X MMIO Port (1 Byte)
0xFFFF          : Tastatur MMIO Port (1 Byte)
===============================================================================
*/

class VM {
private:
    std::vector<uint16_t> regs;
    std::vector<uint8_t> memory;
    std::vector<uint8_t> disk_content;
    std::deque<uint8_t> key_buffer;
    bool running = true;
    bool vram_changed = false;

    SharedData* shared_memory = nullptr;
    HANDLE hMapFile = NULL;

    void handleInput() {
        if (shared_memory && shared_memory->key != 0) {
            key_buffer.push_back(shared_memory->key);
            shared_memory->key = 0;
        }

        if (memory[0xFFFF] == 0 && !key_buffer.empty()) {
            memory[0xFFFF] = key_buffer.front();
            key_buffer.pop_front();
        }

        if (shared_memory) {
            memory[0xFFFE] = shared_memory->mouse_x; 
            memory[0xFFFD] = shared_memory->mouse_y;
            memory[0xFFFC] = shared_memory->mouse_btn;
        }
    }

    void setupSharedMemory() {
        hMapFile = CreateFileMappingA(
            INVALID_HANDLE_VALUE,
            NULL,
            PAGE_READWRITE,
            0,
            sizeof(SharedData),
            "Local\\VM_SharedMemory"
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

public:
    VM() : regs(16, 0), memory(65536, 0) {
        setupSharedMemory();

        std::vector<uint8_t> bios_rom = {
            0x2E, 0xAF, 0xFF,
            0x20, 0x00, 0x00,
            0x21, 0x02, 0x00,
            0xC0, 0x10, 0x00,
            0x2F, 0x02, 0x00
        };
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

        regs[15] = 0x0000;
    }

    ~VM() {
        UnmapViewOfFile(shared_memory);
        CloseHandle(hMapFile);
    }

    void updateSharedMemory(double current_ips) {
        if (shared_memory) {
            memcpy(shared_memory->vram, &memory[VRAM_START], 2000);
            shared_memory->ips = current_ips;
        }
    }

    void step() {
        uint16_t pc_val = regs[15];
        uint8_t b1 = memory[pc_val];
        uint8_t b2 = memory[pc_val + 1];
        uint8_t b3 = memory[pc_val + 2];

        uint8_t opcode = (b1 >> 4) & 0x0F;
        uint8_t reg_a = b1 & 0x0F;
        uint8_t reg_b = (b2 >> 4) & 0x0F;
        uint8_t reg_c = b2 & 0x0F;
        uint16_t imm = (b2 << 8) | b3;

        bool jumped = false;
        bool nop = false;

        switch (opcode) {
            case 0x0: { // NOP
                nop = true;
                break;
            }

            case 0x1: { // mov
                regs[reg_a] = regs[reg_b];
                if (reg_a == 15) {
                    jumped = true;
                }
                break;
            }

            case 0x2: { // movi
                regs[reg_a] = imm;
                if (reg_a == 15) {
                    jumped = true;
                }
                break;
            }

            case 0x3: { // add
                regs[reg_a] += regs[reg_b];
                break;
            }

            case 0x4: { // sub
                regs[reg_a] -= regs[reg_b];
                break;
            }

            case 0x5: { // mul
                regs[reg_a] *= regs[reg_b];
                break;
            }

            case 0x6: { // div
                if (regs[reg_b] != 0) {
                    regs[reg_a] /= regs[reg_b];
                } else {
                    std::cout << "Zero Division. Shutting down." << std::endl;
                    dump();
                    running = false;
                }
                break;
            }

            case 0x7: { // out
                uint16_t port = regs[reg_a];
                uint16_t data = regs[reg_b];

                if (port == 0x1) {
                    std::cout << (char)data << std::flush;
                } else if (port == 0x2) {
                    std::cout << (int)data << " / 0x" << std::hex << (int)data << std::dec << std::flush;
                }
                break;
            }

            case 0x8: { // je
                if (regs[reg_a] == regs[reg_b]) {
                    regs[15] = regs[reg_c];
                    jumped = true;
                }
                break;
            }

            case 0x9: { // jne
                if (regs[reg_a] != regs[reg_b]) {
                    regs[15] = regs[reg_c];
                    jumped = true;
                }
                break;
            }

            case 0xA: { // peek
                uint16_t addr = regs[reg_b];
                uint16_t mode = regs[reg_c];

                if (mode == 1) {
                    regs[reg_a] = memory[addr];
                } else {
                    uint8_t high_byte = memory[addr];
                    uint8_t low_byte = memory[addr + 1];
                    regs[reg_a] = (high_byte << 8) | low_byte;
                }
                break;
            }

            case 0xB: { // poke
                uint16_t val = regs[reg_a];
                uint16_t addr = regs[reg_b];
                uint16_t mode = regs[reg_c];

                if (addr >= VRAM_START && addr <= VRAM_END) {
                    vram_changed = true;
                }

                if (mode == 1) {
                    memory[addr] = val & 0xFF;
                } else {
                    memory[addr] = (val >> 8) & 0xFF;
                    memory[addr + 1] = (val & 0xFF);
                    if (addr + 1 >= VRAM_START && addr + 1 <= VRAM_END) {
                        vram_changed = true;
                    }
                }
                break;
            }

            case 0xC: { // load
                uint16_t sector = regs[reg_a];
                uint16_t start_addr = regs[reg_b];

                uint16_t disk_start = sector * 512;

                std::copy(disk_content.begin() + disk_start,
                        disk_content.begin() + disk_start + 512, 
                        memory.begin() + start_addr);
                break;
            }

            case 0xD: { // save
                uint32_t start_addr = regs[reg_b];
                uint32_t disk_start = regs[reg_a] * 512;

                if (start_addr + 512 <= 65536) {
                    std::copy(memory.begin() + start_addr, 
                            memory.begin() + start_addr + 512, 
                            disk_content.begin() + disk_start);
                } else {
                    uint32_t first_part_size = 65536 - start_addr;
                    uint32_t second_part_size = 512 - first_part_size;

                    std::copy(memory.begin() + start_addr, 
                            memory.end(), 
                            disk_content.begin() + disk_start);

                    std::copy(memory.begin(), 
                            memory.begin() + second_part_size, 
                            disk_content.begin() + disk_start + first_part_size);
                }

                std::ofstream outfile(DISK, std::ios::binary);
                if (outfile.is_open()) {
                    outfile.write((char*)disk_content.data(), disk_content.size());
                    outfile.close();
                }
                break;
            }

            case 0xE: { // pop
                uint8_t high_byte = memory[regs[14]];
                uint8_t low_byte = memory[regs[14] + 1];
                regs[reg_a] = (high_byte << 8) | low_byte;
                regs[14] += 2;
                if (reg_a == 15) {
                    jumped = true;
                }
                break;
            }

            case 0xF: { // push
                uint8_t high_byte = (regs[reg_a] >> 8) & 0xFF;
                uint8_t low_byte = regs[reg_a] & 0xFF;
                regs[14] -= 2;
                memory[regs[14]] = high_byte;
                memory[regs[14] + 1] = low_byte;
                break;
            }
        }

        if (!jumped && !nop) {
            regs[15] += 3;
        } else if (nop) {
            regs[15] += 1;
        }
    }

    void run() {
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
                    memcpy(shared_memory->vram, &memory[VRAM_START], 2000);
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

    void dump() {
        for (int i = 0; i < 16; i++) {
            std::cout << "r" << i << ": " << regs[i] << std::endl;
        }
        std::cout << "0xFFFF: " << (int)memory[65535];
    }
};

int main() {
    VM vm = VM();
    vm.run();
    vm.dump();
    return 0;
}