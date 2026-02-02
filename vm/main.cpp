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
};
#pragma pack(pop)

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

        regs[14] = 0xAFFF;

        std::ifstream file(DISK, std::ios::binary | std::ios::ate);

        if (file.is_open()) {
            std::streamsize size = file.tellg();
            file.seekg(0, std::ios::beg);

            disk_content.resize(size);

            if (file.read((char*)disk_content.data(), size)) {
                std::cout << "Disk geladen: " << size << " Bytes." << std::endl;
            }
        } else {
            std::cerr << "FEHLER: Konnte " << DISK << " nicht finden." << std::endl;
            disk_content.resize(1440 * 1024, 0);
        }

        if (disk_content.size() >= 512) {
            std::copy(disk_content.begin(), disk_content.begin() + 512, memory.begin() + 0x200);
            regs[15] = 0x200; 
            regs[14] = 0xFFFF;
        }
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
        handleInput();

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

        switch (opcode) {
            case 0x0: { // NOP
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
                    std::cout << (int)data << std::hex << (int)data << std::dec << std::flush;
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
                break;
            }

            case 0xE: { // pop
                uint8_t high_byte = memory[regs[14]];
                uint8_t low_byte = memory[regs[14] + 1];
                regs[reg_a] = (high_byte << 8) | low_byte;
                regs[14] += 2;
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

        if (!jumped) {
            regs[15] += 3;
        }
    }

    void run() {
        auto last_ips_time = std::chrono::high_resolution_clock::now();
        long cycles_since_last_ips = 0;
        double current_ips = 0;

        while (running) {
            step();
            cycles_since_last_ips++;

            if (cycles_since_last_ips % 64 == 0) {
                handleInput();
            }

            if (!(cycles_since_last_ips & 8191)) {
                if (vram_changed && shared_memory) {
                    memcpy(shared_memory->vram, &memory[VRAM_START], 2000);
                    shared_memory->ips = current_ips;
                    vram_changed = false;
                }
            }

            if (!(cycles_since_last_ips & 1048576)) {
                auto now = std::chrono::high_resolution_clock::now();
                std::chrono::duration<double> elapsed = now - last_ips_time;
                if (elapsed.count() >= 0.5) {
                    current_ips = cycles_since_last_ips / elapsed.count();
                    cycles_since_last_ips = 0;
                    last_ips_time = now;
                    Sleep(1); 
                }
            }
        }
    }

    void dump() {
        for (int i = 0; i < 16; i++) {
            std::cout << "r" << i << ": " << regs[i] << std::endl;
        }
        std::cout << "0xFFFF: " << (int)memory[65535];
    }

    void dumpVRAMtoFile() {
        std::ofstream file("vram.bin", std::ios::binary | std::ios::trunc);
        if (file.is_open()) {
            file.write(reinterpret_cast<const char*>(memory.data() + VRAM_START), 2000);
            file.close();

            if (memory[VRAM_START] != 0) {
                // std::cout << "VRAM Dump: Erstes Zeichen ist: " << (int)memory[VRAM_START] << std::endl;
            }
        } else {
            std::cerr << "WARNUNG: vram.bin blockiert!" << std::endl;
        }
    }
};

int main() {
    VM vm = VM();
    vm.run();
    vm.dump();
    return 0;
}