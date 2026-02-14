#include "vm.hpp"
#include <iostream>
#include <algorithm>
#include <fstream>
#include <windows.h>
#include <cstdlib>

void VM::execute_16_bit() {
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

        case 0x6: { // jgt
            if (regs[reg_a] > regs[reg_b]) {
                regs[15] = regs[reg_c];
                jumped = true;
            }
            break;
        }

        case 0x7: { // out
            uint16_t port = regs[reg_a];
            uint16_t data = regs[reg_b];

            switch(port) {
                case 0x1: // Serieller Port (Char)
                    std::cout << (char)data << std::flush;
                    break;
                case 0x2: // Serieller Port (Int/Hex)
                    std::cout << (int)data << " / 0x" << std::hex << (int)data << std::dec << std::flush;
                    break;
                case 0x10: // Disk-Port (Sektor setzen)
                    disk_buffer_sector = data;
                    break;
                case 0x11: // Disk-Port (Adresse setzen)
                    disk_buffer_addr = data;
                    break;
                case 0x12: { // Disk-Port (Command, 1=Load/2=Save)
                    uint32_t disk_start = disk_buffer_sector * 512;
                    if (data == 1) {
                        if (disk_start + 512 <= disk_content.size()) {
                            std::copy(disk_content.begin() + disk_start, 
                                    disk_content.begin() + disk_start + 512, 
                                    memory.begin() + disk_buffer_addr);
                        }
                    } else if (data == 2) {
                        if (disk_buffer_addr + 512 <= 65536) {
                            std::copy(memory.begin() + disk_buffer_addr, 
                                    memory.begin() + disk_buffer_addr + 512, 
                                    disk_content.begin() + disk_start);
                        } else {
                            uint32_t first_part = 65536 - disk_buffer_addr;
                            std::copy(memory.begin() + disk_buffer_addr, memory.end(), disk_content.begin() + disk_start);
                            std::copy(memory.begin(), memory.begin() + (512 - first_part), disk_content.begin() + disk_start + first_part);
                        }

                        std::ofstream outfile(DISK, std::ios::binary);
                        if (outfile.is_open()) {
                            outfile.write((char*)disk_content.data(), disk_content.size());
                            outfile.close();
                        }
                    }
                    break;
                }
                case 0x20: // VGA Control
                    if (shared_memory) {
                        shared_memory->video_mode = (uint8_t)data;
                    }
                    break;
                case 0x30: // Buzzer-Port (Frequenz setzen)
                    buzzer_freq = data;
                    break;
                case 0x31: // Buzzer-Port (Länge setzen)
                    buzzer_duration = data;
                    break;
                case 0x32: // Buzzer-Port (Control)
                    Beep(buzzer_freq, buzzer_duration);
                    break;
                case 0x40: // Wait-Port
                    Sleep(data);
                    break;
                case 0xFF: // Bitwidth-Port
                    cpu_bit_width = data;
                    if (data == 1) {
                        regs[15] = 0x300;
                        jumped = true;
                    }
                    break;
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

            if (addr == 0xFFF2) {
                memory[0xFFF2] = rand() % 256;
            }

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

        case 0xC: { // jlt
            if (regs[reg_a] < regs[reg_b]) {
                regs[15] = regs[reg_c];
                jumped = true;
            }
            break;
        }

        case 0xD: { // jge
            if (regs[reg_a] >= regs[reg_b]) {
                regs[15] = regs[reg_c];
                jumped = true;
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