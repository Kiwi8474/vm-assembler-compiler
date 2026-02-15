#include "vm.hpp"
#include "shared_struct.hpp"
#include <iostream>
#include <algorithm>
#include <fstream>
#include <windows.h>
#include <cstdlib>
#include <cmath>
#include <limits>
#include <chrono>
#include <thread>
#include <random>
#include <iomanip>

uint32_t VM::read_mem8(uint32_t addr, bool is_signed) {
    uint8_t val = memory[addr];
    if (is_signed) return (uint32_t)(int32_t)(int8_t)val;
    return (uint32_t)val;
}

uint32_t VM::read_mem16(uint32_t addr, bool is_signed) {
    uint16_t val = ((uint16_t)memory[addr] << 8) | (uint16_t)memory[addr + 1];
    if (is_signed) return (uint32_t)(int32_t)(int16_t)val;
    return (uint32_t)val;
}

uint32_t VM::read_mem32(uint32_t addr, bool is_signed) {
    return ((uint32_t)memory[addr] << 24) |
           ((uint32_t)memory[addr + 1] << 16) |
           ((uint32_t)memory[addr + 2] << 8) |
           ((uint32_t)memory[addr + 3]);
}

void VM::write_mem8(uint32_t addr, uint8_t val) {
    memory[addr] = val;
    if (addr >= VRAM_START && addr < VRAM_END) vram_changed = true;
}

void VM::write_mem16(uint32_t addr, uint16_t val) {
    memory[addr] = (val >> 8) & 0xFF;
    memory[addr + 1] = val & 0xFF;
    if (addr >= VRAM_START && addr < VRAM_END) vram_changed = true;
}

void VM::write_mem32(uint32_t addr, uint32_t val) {
    memory[addr] = (val >> 24) & 0xFF;
    memory[addr + 1] = (val >> 16) & 0xFF;
    memory[addr + 2] = (val >> 8) & 0xFF;
    memory[addr + 3] = val & 0xFF;
    if (addr >= VRAM_START && addr < VRAM_END) vram_changed = true;
}

void VM::compile_block(uint32_t addr) {
    size_t start_offset = jit_ptr;
    uint32_t current_pc = addr;
    bool block_ended = false;
    bool instructions_compiled = false;

    while (!block_ended) {
        if (current_pc + 8 > memory.size()) {
            block_ended = true;
            break;
        }

        uint8_t opcode = memory[current_pc];
        uint8_t reg_a = (memory[current_pc + 1] >> 4) & 0x0F;
        uint8_t mode = memory[current_pc + 3];
        bool use_imm = mode & 0x01;
        uint32_t imm = ((uint32_t)memory[current_pc + 4] << 24) | ((uint32_t)memory[current_pc + 5] << 16) |
                       ((uint32_t)memory[current_pc + 6] << 8) | ((uint32_t)memory[current_pc + 7]);

        if (opcode == 0x10) { // MOV
            if (use_imm) { // MOV rA, imm
                jit_buffer[jit_ptr++] = 0xC7; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
                *(uint32_t*)(jit_buffer + jit_ptr) = imm; jit_ptr += 4;
            } else if (!(mode & 0x06)) { // MOV rA, rB (kein Load/Store)
                uint8_t reg_b = memory[current_pc + 1] & 0x0F;
                // Native x86: mov eax, [rcx + reg_b*4] -> mov [rcx + reg_a*4], eax
                jit_buffer[jit_ptr++] = 0x8B; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_b * 4;
                jit_buffer[jit_ptr++] = 0x89; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
            } else {
                block_ended = true; // LOAD/STORE -> JIT-Exit
                break; 
            }
            current_pc += 8;
            instructions_compiled = true;
        } 
        else if (opcode == 0x20) { // ADD
            if (use_imm) {
                jit_buffer[jit_ptr++] = 0x81; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
                *(uint32_t*)(jit_buffer + jit_ptr) = imm; jit_ptr += 4;
            } else {
                uint8_t reg_b = memory[current_pc + 1] & 0x0F;
                jit_buffer[jit_ptr++] = 0x8B; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_b * 4;
                jit_buffer[jit_ptr++] = 0x01; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
            }
            current_pc += 8;
            instructions_compiled = true;
        }
        else if (opcode == 0x21) { // SUB
            if (use_imm) {
                // sub [rcx + reg_a*4], imm
                jit_buffer[jit_ptr++] = 0x81; jit_buffer[jit_ptr++] = 0x69; jit_buffer[jit_ptr++] = reg_a * 4;
                *(uint32_t*)(jit_buffer + jit_ptr) = imm; jit_ptr += 4;
            } else {
                uint8_t reg_b = memory[current_pc + 1] & 0x0F;
                // mov eax, [rcx + reg_b*4] -> sub [rcx + reg_a*4], eax
                jit_buffer[jit_ptr++] = 0x8B; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_b * 4;
                jit_buffer[jit_ptr++] = 0x29; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
            }
            current_pc += 8;
            instructions_compiled = true;
        } 
        else if (opcode == 0x22) { // MUL
            if (use_imm) {
                // mov eax, [rcx + reg_a*4] -> imul eax, imm -> mov [rcx + reg_a*4], eax
                jit_buffer[jit_ptr++] = 0x8B; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
                jit_buffer[jit_ptr++] = 0x69; jit_buffer[jit_ptr++] = 0xC0; // imul eax, eax, ...
                *(uint32_t*)(jit_buffer + jit_ptr) = imm; jit_ptr += 4;
                jit_buffer[jit_ptr++] = 0x89; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
            } else {
                uint8_t reg_b = memory[current_pc + 1] & 0x0F;
                // mov eax, [rcx + reg_a*4] -> imul eax, [rcx + reg_b*4] -> mov [rcx + reg_a*4], eax
                jit_buffer[jit_ptr++] = 0x8B; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
                jit_buffer[jit_ptr++] = 0x0F; jit_buffer[jit_ptr++] = 0xAF; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_b * 4;
                jit_buffer[jit_ptr++] = 0x89; jit_buffer[jit_ptr++] = 0x41; jit_buffer[jit_ptr++] = reg_a * 4;
            }
            current_pc += 8;
            instructions_compiled = true;
        }
        else {
            block_ended = true;
            break;
        }

        if (current_pc - addr > 512) block_ended = true;
    }

    if (!instructions_compiled) {
        jit_ptr = start_offset;
        hot_spots[addr] = -100;
        return;
    }

    jit_buffer[jit_ptr++] = 0xC7;
    jit_buffer[jit_ptr++] = 0x41;
    jit_buffer[jit_ptr++] = 60;
    *(uint32_t*)(jit_buffer + jit_ptr) = current_pc;
    jit_ptr += 4;

    jit_buffer[jit_ptr++] = 0xC3; // RET

    jit_cache[addr] = (JitBlockFunc)(jit_buffer + start_offset);

    hot_spots[addr] = 0;
}

void VM::execute_32_bit() {
    if (jit_cache.count(regs[15])) {
        uint32_t current_pc = regs[15];
        jit_cache[current_pc](regs.data(), memory.data());
        return;
    }

    uint32_t pc_val = regs[15];
    hot_spots[pc_val]++;

    if (hot_spots[pc_val] > 50) {
        compile_block(pc_val);
        return; 
    }
    
    if (pc_val % 8 != 0) {
        std::cerr << "[ERROR] PC Alignment Fehler: 0x" << std::hex << pc_val << std::endl;
        running = false;
        return;
    }

    uint8_t opcode = memory[pc_val];
    uint8_t reg_a = (memory[pc_val + 1] >> 4) & 0x0F;
    uint8_t reg_b = memory[pc_val + 1] & 0x0F;
    uint8_t reg_c = (memory[pc_val + 2] >> 4) & 0x0F;
    uint8_t mode = memory[pc_val + 3];
    bool use_imm = mode & 0x01;
    bool use_indirect_src = mode & 0x02;
    bool use_indirect_dest = mode & 0x04;
    bool is_signed = mode & 0x08;
    uint8_t size = (mode >> 4) & 0x03;
    uint32_t imm = ((uint32_t)memory[pc_val + 4] << 24) |
                    ((uint32_t)memory[pc_val + 5] << 16) |
                    ((uint32_t)memory[pc_val + 6] << 8) |
                    ((uint32_t)memory[pc_val + 7]);

    bool jumped = false;

    switch (opcode) {
                case 0x00: // nop
                    break;

                case 0x01: // halt
                    running = false;
                    jumped = true;
                    break;

                case 0x02: // jmp
                    if (use_imm) regs[15] = imm;
                    else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                    else regs[15] = regs[reg_c];
                    jumped = true;
                    break;
                
                case 0x03: // je
                    if (regs[reg_a] == regs[reg_b]) {
                        if (use_imm) regs[15] = imm;
                        else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                        else regs[15] = regs[reg_c];
                        jumped = true;
                    }
                    break;
                
                case 0x04: // jne
                    if (regs[reg_a] != regs[reg_b]) {
                        if (use_imm) regs[15] = imm;
                        else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                        else regs[15] = regs[reg_c];
                        jumped = true;
                    }
                    break;
                
                case 0x05: // jg
                    if (regs[reg_a] > regs[reg_b]) {
                        if (use_imm) regs[15] = imm;
                        else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                        else regs[15] = regs[reg_c];
                        jumped = true;
                    }
                    break;
                
                case 0x06: // jge
                    if (regs[reg_a] >= regs[reg_b]) {
                        if (use_imm) regs[15] = imm;
                        else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                        else regs[15] = regs[reg_c];
                        jumped = true;
                    }
                    break;
                
                case 0x07: // jl
                    if (regs[reg_a] < regs[reg_b]) {
                        if (use_imm) regs[15] = imm;
                        else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                        else regs[15] = regs[reg_c];
                        jumped = true;
                    }
                    break;
                
                case 0x08: // jle
                    if (regs[reg_a] <= regs[reg_b]) {
                        if (use_imm) regs[15] = imm;
                        else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_c]);
                        else regs[15] = regs[reg_c];
                        jumped = true;
                    }
                    break;
                
                case 0x09: // call
                    regs[14] -= 4;
                    write_mem32(regs[14], regs[15] + 8);
                    if (use_imm) regs[15] = imm;
                    else if (use_indirect_dest) regs[15] = read_mem32(regs[reg_a]);
                    else regs[15] = regs[reg_a];
                    jumped = true;
                    break;
                
                case 0x0A: // ret
                    regs[15] = read_mem32(regs[14]);
                    regs[14] += 4;
                    jumped = true;
                    break;
                
                case 0x0B: // int
                    regs[14] -= 4;
                    write_mem32(regs[14], regs[15] + 8);
                    regs[15] = read_mem32(regs[reg_a] * 4);
                    jumped = true;
                    break;
                
                case 0x0C: // iret
                    regs[15] = read_mem32(regs[14]);
                    regs[14] += 4;
                    jumped = true;
                    break;

                case 0x10: // mov
                    if (use_imm) {
                        regs[reg_a] = imm;
                        if (reg_a == 15) jumped = true;
                    }
                    else if (use_indirect_dest && use_indirect_src) {
                        if (size == 0) write_mem8(regs[reg_a], read_mem8(regs[reg_b], is_signed));
                        else if (size == 1) write_mem16(regs[reg_a], read_mem16(regs[reg_b], is_signed));
                        else if (size == 2) write_mem32(regs[reg_a], read_mem32(regs[reg_b]));
                    }
                    else if (use_indirect_dest) {
                        if (size == 0) write_mem8(regs[reg_a], regs[reg_b] & 0xFF);
                        else if (size == 1) write_mem16(regs[reg_a], regs[reg_b] & 0xFFFF);
                        else write_mem32(regs[reg_a], regs[reg_b]);
                    }
                    else if (use_indirect_src) {
                        if (size == 0) regs[reg_a] = read_mem8(regs[reg_b], is_signed);
                        else if (size == 1) regs[reg_a] = read_mem16(regs[reg_b], is_signed);
                        else regs[reg_a] = read_mem32(regs[reg_b]);
                        if (reg_a == 15) jumped = true;
                    }
                    else {
                        regs[reg_a] = regs[reg_b];
                        if (reg_a == 15) jumped = true;
                    }
                    break;

                case 0x11: // push
                    regs[14] -= 4;
                    if (use_imm) write_mem32(regs[14], imm);
                    else if (use_indirect_src) write_mem32(regs[14], read_mem32(regs[reg_a], is_signed));
                    else write_mem32(regs[14], regs[reg_a]);
                    break;
                
                case 0x12: // pop
                    regs[reg_a] = read_mem32(regs[14], is_signed);
                    if (reg_a == 15) jumped = true;
                    regs[14] += 4;
                    break;

                case 0x20: { // add
                    uint32_t val_b = use_imm ? imm : regs[reg_b];

                    if (is_signed) {
                        if (size == 0)      regs[reg_a] = (int32_t)((int8_t)regs[reg_a] + (int8_t)val_b);
                        else if (size == 1) regs[reg_a] = (int32_t)((int16_t)regs[reg_a] + (int16_t)val_b);
                        else                regs[reg_a] = (int32_t)regs[reg_a] + (int32_t)val_b;
                    } else {
                        if (size == 0)      regs[reg_a] = ((regs[reg_a] & 0xFF) + (val_b & 0xFF)) & 0xFF;
                        else if (size == 1) regs[reg_a] = ((regs[reg_a] & 0xFFFF) + (val_b & 0xFFFF)) & 0xFFFF;
                        else                regs[reg_a] = regs[reg_a] + val_b;
                    }

                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x21: { // sub
                    uint32_t val_b = use_imm ? imm : regs[reg_b];

                    if (is_signed) {
                        if (size == 0)      regs[reg_a] = (int32_t)((int8_t)regs[reg_a] - (int8_t)val_b);
                        else if (size == 1) regs[reg_a] = (int32_t)((int16_t)regs[reg_a] - (int16_t)val_b);
                        else                regs[reg_a] = (int32_t)regs[reg_a] - (int32_t)val_b;
                    } else {
                        if (size == 0)      regs[reg_a] = ((regs[reg_a] & 0xFF) - (val_b & 0xFF)) & 0xFF;
                        else if (size == 1) regs[reg_a] = ((regs[reg_a] & 0xFFFF) - (val_b & 0xFFFF)) & 0xFFFF;
                        else                regs[reg_a] = regs[reg_a] - val_b;
                    }

                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x22: { // mul
                    uint32_t val_b = use_imm ? imm : regs[reg_b];

                    if (is_signed) {
                        if (size == 0)      regs[reg_a] = (int32_t)((int8_t)regs[reg_a] * (int8_t)val_b);
                        else if (size == 1) regs[reg_a] = (int32_t)((int16_t)regs[reg_a] * (int16_t)val_b);
                        else                regs[reg_a] = (int32_t)regs[reg_a] * (int32_t)val_b;
                    } else {
                        if (size == 0)      regs[reg_a] = ((regs[reg_a] & 0xFF) * (val_b & 0xFF)) & 0xFF;
                        else if (size == 1) regs[reg_a] = ((regs[reg_a] & 0xFFFF) * (val_b & 0xFFFF)) & 0xFFFF;
                        else                regs[reg_a] = regs[reg_a] * val_b;
                    }

                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x23: { // div
                    uint32_t val_b = use_imm ? imm : regs[reg_b];
                    if (val_b == 0) {
                        std::cerr << "Division by Zero" << std::endl;
                        running = false;
                        break;
                    }

                    if (is_signed) {
                        if (size == 0)      regs[reg_a] = (int32_t)((int8_t)regs[reg_a] / (int8_t)val_b);
                        else if (size == 1) regs[reg_a] = (int32_t)((int16_t)regs[reg_a] / (int16_t)val_b);
                        else                regs[reg_a] = (int32_t)regs[reg_a] / (int32_t)val_b;
                    } else {
                        if (size == 0)      regs[reg_a] = ((regs[reg_a] & 0xFF) / (val_b & 0xFF)) & 0xFF;
                        else if (size == 1) regs[reg_a] = ((regs[reg_a] & 0xFFFF) / (val_b & 0xFFFF)) & 0xFFFF;
                        else                regs[reg_a] = regs[reg_a] / val_b;
                    }

                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x24: { // mod
                    uint32_t val_b = use_imm ? imm : regs[reg_b];

                    if (val_b == 0) {
                        std::cerr << "Modulo by Zero" << std::endl;
                        running = false;
                        break;
                    }

                    if (is_signed) {
                        if (size == 0)      regs[reg_a] = (int32_t)((int8_t)regs[reg_a] % (int8_t)val_b);
                        else if (size == 1) regs[reg_a] = (int32_t)((int16_t)regs[reg_a] % (int16_t)val_b);
                        else                regs[reg_a] = (int32_t)regs[reg_a] % (int32_t)val_b;
                    } else {
                        if (size == 0)      regs[reg_a] = ((regs[reg_a] & 0xFF) % (val_b & 0xFF)) & 0xFF;
                        else if (size == 1) regs[reg_a] = ((regs[reg_a] & 0xFFFF) % (val_b & 0xFFFF)) & 0xFFFF;
                        else                regs[reg_a] = regs[reg_a] % val_b;
                    }

                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x30: { // and
                    uint32_t val_b = use_imm ? imm : regs[reg_b];
                    
                    if (size == 0)      regs[reg_a] = (regs[reg_a] & val_b) & 0xFF;
                    else if (size == 1) regs[reg_a] = (regs[reg_a] & val_b) & 0xFFFF;
                    else                regs[reg_a] = (regs[reg_a] & val_b);
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x31: { // or
                    uint32_t val_b = use_imm ? imm : regs[reg_b];
                    
                    if (size == 0)      regs[reg_a] = (regs[reg_a] | val_b) & 0xFF;
                    else if (size == 1) regs[reg_a] = (regs[reg_a] | val_b) & 0xFFFF;
                    else                regs[reg_a] = (regs[reg_a] | val_b);
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x32: { // xor
                    uint32_t val_b = use_imm ? imm : regs[reg_b];
                    
                    if (size == 0)      regs[reg_a] = (regs[reg_a] ^ val_b) & 0xFF;
                    else if (size == 1) regs[reg_a] = (regs[reg_a] ^ val_b) & 0xFFFF;
                    else                regs[reg_a] = (regs[reg_a] ^ val_b);
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x33: { // not
                    if (size == 0)      regs[reg_a] = (~regs[reg_a]) & 0xFF;
                    else if (size == 1) regs[reg_a] = (~regs[reg_a]) & 0xFFFF;
                    else                regs[reg_a] = (~regs[reg_a]);
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x40: { // shl
                    uint32_t count = use_imm ? imm : (regs[reg_b] & 0x1F);
                    
                    if (size == 0)      regs[reg_a] = (regs[reg_a] << count) & 0xFF;
                    else if (size == 1) regs[reg_a] = (regs[reg_a] << count) & 0xFFFF;
                    else                regs[reg_a] = (regs[reg_a] << count);
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x41: { // shr
                    uint32_t count = use_imm ? imm : (regs[reg_b] & 0x1F);

                    if (size == 0)      regs[reg_a] = (regs[reg_a] & 0xFF) >> count;
                    else if (size == 1) regs[reg_a] = (regs[reg_a] & 0xFFFF) >> count;
                    else                regs[reg_a] = (regs[reg_a] >> count);
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x42: { // sar
                    uint32_t count = use_imm ? imm : (regs[reg_b] & 0x1F);

                    if (size == 0)      regs[reg_a] = (int32_t)((int8_t)regs[reg_a] >> count);
                    else if (size == 1) regs[reg_a] = (int32_t)((int16_t)regs[reg_a] >> count);
                    else                regs[reg_a] = (int32_t)regs[reg_a] >> count;
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x43: { // rol
                    uint32_t count = (use_imm ? imm : regs[reg_b]) & 0x1F;
                    if (count == 0) break;

                    if (size == 0) {
                        uint8_t val = (uint8_t)regs[reg_a];
                        regs[reg_a] = ((val << (count % 8)) | (val >> (8 - (count % 8)))) & 0xFF;
                    }
                    else if (size == 1) {
                        uint16_t val = (uint16_t)regs[reg_a];
                        regs[reg_a] = ((val << (count % 16)) | (val >> (16 - (count % 16)))) & 0xFFFF;
                    }
                    else {
                        uint32_t val = regs[reg_a];
                        regs[reg_a] = (val << count) | (val >> (32 - count));
                    }
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x44: { // ror
                    uint32_t count = (use_imm ? imm : regs[reg_b]) & 0x1F;
                    if (count == 0) break;

                    if (size == 0) {
                        uint8_t val = (uint8_t)regs[reg_a];
                        regs[reg_a] = ((val >> (count % 8)) | (val << (8 - (count % 8)))) & 0xFF;
                    }
                    else if (size == 1) {
                        uint16_t val = (uint16_t)regs[reg_a];
                        regs[reg_a] = ((val >> (count % 16)) | (val << (16 - (count % 16)))) & 0xFFFF;
                    }
                    else {
                        uint32_t val = regs[reg_a];
                        regs[reg_a] = (val >> count) | (val << (32 - count));
                    }
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x50: { // fadd
                    float a = *(float*)&regs[reg_a];
                    float b = *(float*)&regs[reg_b];
                    float result = a + b;
                    regs[reg_a] = *(uint32_t*)&result;
            
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x51: { // fsub
                    float a = *(float*)&regs[reg_a];
                    float b = *(float*)&regs[reg_b];
                    float result = a - b;
                    regs[reg_a] = *(uint32_t*)&result;
            
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x52: { // fmul
                    float a = *(float*)&regs[reg_a];
                    float b = *(float*)&regs[reg_b];
                    float result = a * b;
                    regs[reg_a] = *(uint32_t*)&result;
            
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x53: { // fdiv
                    float a = *(float*)&regs[reg_a];
                    float b = *(float*)&regs[reg_b];

                    if (b == 0.0f) {
                        std::cerr << "Float Division by Zero" << std::endl;
                        running = false;
                        break;
                    }

                    float result = a / b;
                    regs[reg_a] = *(uint32_t*)&result;
            
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x54: { // fmod
                    float a = *(float*)&regs[reg_a];
                    float b = *(float*)&regs[reg_b];

                    if (b == 0.0f) {                
                        std::cerr << "Float Modulo by Zero" << std::endl;
                        running = false;
                        break;
                    }                

                    float result = std::fmod(a, b);
                    regs[reg_a] = *(uint32_t*)&result;
                    
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x60: { // fsqrt
                    float a = *(float*)&regs[reg_a];
                    if (a < 0.0f) {
                        float nan = std::numeric_limits<float>::quiet_NaN();
                        regs[reg_a] = *(uint32_t*)&nan;
                    } else {
                        float result = std::sqrt(a);
                        regs[reg_a] = *(uint32_t*)&result;
                    }
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x61: { // fsin
                    float input = *(float*)&regs[reg_b];
                    float result = std::sin(input);
                    regs[reg_a] = *(uint32_t*)&result;
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x62: { // fcos
                    float input = *(float*)&regs[reg_b];
                    float result = std::cos(input);
                    regs[reg_a] = *(uint32_t*)&result;
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x63: { // fabs
                    float a = *(float*)&regs[reg_a];
                    float result = std::fabs(a);
                    regs[reg_a] = *(uint32_t*)&result;
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x64: { // f2i
                    float f_val = *(float*)&regs[reg_a];
                    regs[reg_a] = (uint32_t)((int32_t)f_val);                
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x65: { // i2f
                    float f_res = (float)((int32_t)regs[reg_a]);
                    regs[reg_a] = *(uint32_t*)&f_res;                
                    if (reg_a == 15) jumped = true;
                    break;
                }

                case 0x70: { // gpuclear
                    uint32_t top_left = regs[reg_a];
                    uint32_t bottom_right = regs[reg_b];
                    uint8_t color = (uint8_t)(regs[reg_c] & 0xFF);

                    int x1 = (top_left >> 16);
                    int y1 = (top_left & 0xFFFF);
                    int x2 = (bottom_right >> 16);
                    int y2 = (bottom_right & 0xFFFF);

                    if (x1 > x2) std::swap(x1, x2);
                    if (y1 > y2) std::swap(y1, y2);

                    for (int y = y1; y < y2; ++y) {
                        if (y >= 0 && y < (int)SCREEN_HEIGHT) {
                            uint32_t line_start = VRAM_START + (y * SCREEN_WIDTH + x1);
                            int width = x2 - x1;

                            if (line_start + width <= memory.size()) {
                                std::fill(memory.begin() + line_start, memory.begin() + line_start + width, color);
                            }
                        }
                    }
                    vram_changed = true;
                    break;
                }

                case 0x71: { // gpublit
                    uint32_t src_start = regs[reg_a];
                    uint32_t dest_start = regs[reg_b];
                    uint32_t size_pack = regs[reg_c];
                    
                    int w = (size_pack >> 16);
                    int h = (size_pack & 0xFFFF);

                    for (int y = 0; y < h; ++y) {
                        uint32_t current_src = src_start + (y * SCREEN_WIDTH);
                        uint32_t current_dest = dest_start + (y * SCREEN_WIDTH);

                        if (current_src + w <= memory.size() && current_dest + w <= memory.size()) {
                            std::copy(memory.begin() + current_src, 
                                    memory.begin() + current_src + w, 
                                    memory.begin() + current_dest);
                        }
                    }
                    vram_changed = true;
                    break;
                }

                case 0x72: { // gpurect
                    uint32_t top_left = regs[reg_a];
                    uint32_t bottom_right = regs[reg_b];
                    uint8_t color = (uint8_t)(regs[reg_c] & 0xFF);

                    int x1 = (top_left >> 16);
                    int y1 = (top_left & 0xFFFF);
                    int x2 = (bottom_right >> 16);
                    int y2 = (bottom_right & 0xFFFF);

                    for (int x = x1; x <= x2; ++x) { 
                        memory[VRAM_START + (y1 * SCREEN_WIDTH + x)] = color;
                        memory[VRAM_START + (y2 * SCREEN_WIDTH + x)] = color;
                    }
                    for (int y = y1; y <= y2; ++y) {
                        memory[VRAM_START + (y * SCREEN_WIDTH + x1)] = color;
                        memory[VRAM_START + (y * SCREEN_WIDTH + x2)] = color;
                    }
                    vram_changed = true;
                    break;
                }

                case 0x73: { // gpuline
                    uint32_t start_pos = regs[reg_a];
                    uint32_t end_pos = regs[reg_b];
                    uint8_t color = (uint8_t)(regs[reg_c] & 0xFF);

                    int x1 = (start_pos >> 16);
                    int y1 = (start_pos & 0xFFFF);
                    int x2 = (end_pos >> 16);
                    int y2 = (end_pos & 0xFFFF);

                    int dx = abs(x2 - x1);
                    int dy = abs(y2 - y1);
                    int sx = (x1 < x2) ? 1 : -1;
                    int sy = (y1 < y2) ? 1 : -1;
                    int err = dx - dy;

                    while (true) {
                        uint32_t vram_idx = VRAM_START + (y1 * SCREEN_WIDTH + x1);
                        
                        if (vram_idx >= VRAM_START && vram_idx < VRAM_END) {
                            memory[vram_idx] = color;
                        }
                        
                        if (x1 == x2 && y1 == y2) break;
                        int e2 = 2 * err;
                        if (e2 > -dy) { err -= dy; x1 += sx; }
                        if (e2 < dx) { err += dx; y1 += sy; }
                    }
                    vram_changed = true;
                    break;
                }

                case 0x74: { // gpurectfill
                    uint32_t top_left = regs[reg_a];
                    uint32_t bottom_right = regs[reg_b];
                    uint8_t color = (uint8_t)(regs[reg_c] & 0xFF); 

                    int x1 = (top_left >> 16);
                    int y1 = (top_left & 0xFFFF);
                    int x2 = (bottom_right >> 16);
                    int y2 = (bottom_right & 0xFFFF);

                    x1 = std::max(0, std::min(x1, (int)SCREEN_WIDTH));
                    x2 = std::max(0, std::min(x2, (int)SCREEN_WIDTH));
                    y1 = std::max(0, std::min(y1, (int)SCREEN_HEIGHT));
                    y2 = std::max(0, std::min(y2, (int)SCREEN_HEIGHT));

                    if (x1 > x2) std::swap(x1, x2);
                    if (y1 > y2) std::swap(y1, y2);

                    for (int y = y1; y < y2; ++y) {
                        uint32_t row_start = VRAM_START + (y * SCREEN_WIDTH + x1);
                        std::fill(memory.begin() + row_start, memory.begin() + row_start + (x2 - x1), color);
                    }
                    vram_changed = true;
                    break;
                }

                case 0x75: { // gpucirc
                    uint32_t center_pos = regs[reg_a];
                    uint32_t radius_reg = regs[reg_b];
                    uint8_t color = (uint8_t)(regs[reg_c] & 0xFF);

                    int cx = (center_pos >> 16);
                    int cy = (center_pos & 0xFFFF);
                    int r = (radius_reg & 0xFFFF);

                    int x = r;
                    int y = 0;
                    int err = 1 - r;

                    auto plot = [&](int px, int py) {
                        if (px >= 0 && px < (int)SCREEN_WIDTH && py >= 0 && py < (int)SCREEN_HEIGHT) {
                            memory[VRAM_START + (py * SCREEN_WIDTH + px)] = color;
                        }
                    };

                    while (x >= y) {
                        plot(cx + x, cy + y);
                        plot(cx - x, cy + y);
                        plot(cx + x, cy - y);
                        plot(cx - x, cy - y);
                        plot(cx + y, cy + x);
                        plot(cx - y, cy + x);
                        plot(cx + y, cy - x);
                        plot(cx - y, cy - x);

                        y++;
                        if (err < 0) {
                            err += 2 * y + 1;
                        } else {
                            x--;
                            err += 2 * (y - x) + 1;
                        }
                    }
                    vram_changed = true;
                    break;
                }

                case 0x76: { // gpucircfill
                    uint32_t center_pos = regs[reg_a];
                    uint32_t radius_reg = regs[reg_b];
                    uint8_t color = (uint8_t)(regs[reg_c] & 0xFF);

                    int cx = (center_pos >> 16);
                    int cy = (center_pos & 0xFFFF);
                    int r = (radius_reg & 0xFFFF);

                    int x = r;
                    int y = 0;
                    int err = 1 - r;

                    auto draw_line = [&](int x1, int x2, int py) {
                        if (py < 0 || py >= (int)SCREEN_HEIGHT) return;

                        int left = std::max(0, std::min(x1, (int)SCREEN_WIDTH - 1));
                        int right = std::max(0, std::min(x2, (int)SCREEN_WIDTH - 1));
                        
                        if (left > right) std::swap(left, right);

                        int width = right - left + 1;

                        if (width > 0) {
                            uint32_t addr = VRAM_START + (py * SCREEN_WIDTH + left);
                            if (addr + width <= memory.size()) {
                                std::fill(memory.begin() + addr, memory.begin() + addr + width, color);
                            }
                        }
                    };

                    while (x >= y) {
                        draw_line(cx - x, cx + x, cy + y);
                        draw_line(cx - x, cx + x, cy - y);
                        draw_line(cx - y, cx + y, cy + x);
                        draw_line(cx - y, cx + y, cy - x);

                        y++;
                        if (err < 0) {
                            err += 2 * y + 1;
                        } else {
                            x--;
                            err += 2 * (y - x) + 1;
                        }
                    }
                    vram_changed = true;
                    break;
                }

                case 0x80: { // time
                    auto now = std::chrono::steady_clock::now();
                    auto duration = now.time_since_epoch();
                    uint64_t ms = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
                    regs[reg_a] = (uint32_t)(ms & 0xFFFFFFFF);
                    break;
                }

                case 0x81: { // wait
                    uint32_t ms = regs[reg_a];
                    Sleep(ms);
                    break;
                }

                case 0x82: { // rand
                    static std::mt19937 rng(std::random_device{}());
                    std::uniform_int_distribution<uint32_t> dist(0, 0xFFFFFFFF);
                    regs[reg_a] = dist(rng);
                    break;
                }

                case 0xF0: { // out
                    uint32_t port = regs[reg_a];
                    uint32_t data = regs[reg_b];

                    switch(port) {
                        case 0x01: // Serial Port (Char)
                            std::cout << (char)data << std::flush;
                            break;
                        case 0x02: // Serial Port (uint)
                            std::cout << (uint32_t)data << std::flush;
                            break;
                        case 0x03: // Serial Port (int)
                            std::cout << (int32_t)data << std::flush;
                            break;
                        case 0x04: // Serial Port (hex)
                            std::cout << std::hex << (uint32_t)data << std::dec << std::flush;
                            break;
                        case 0x05: { // Serial Port (float)
                            float f = *reinterpret_cast<float*>(&data);                
                            std::cout << std::fixed << std::setprecision(4) << f << std::dec << std::flush;
                            break;
                        }

                        case 0x10: // Disk
                            disk_buffer_sector = data;
                            break;
                        case 0x11: // Disk
                            disk_buffer_addr = data;
                            break;
                        case 0x12: { // Disk (1=Load/2=Save)
                            uint32_t disk_start = disk_buffer_sector * 512;
                            if (data == 1) {
                                if (disk_start + 512 <= disk_content.size()) {
                                    std::copy(disk_content.begin() + disk_start, 
                                            disk_content.begin() + disk_start + 512, 
                                            memory.begin() + disk_buffer_addr);
                                }
                            } else if (data == 2) {
                                if (disk_buffer_addr + 512 <= 0xFFFFFFFF + 1) {
                                    std::copy(memory.begin() + disk_buffer_addr, 
                                            memory.begin() + disk_buffer_addr + 512, 
                                            disk_content.begin() + disk_start);
                                } else {
                                    uint32_t first_part = 0xFFFFFFFF + 1 - disk_buffer_addr;
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
                        
                        case 0x30: // Buzzer
                            buzzer_freq = data;
                            break;
                        case 0x31: // Buzzer
                            buzzer_duration = data;
                            break;
                        case 0x32: // Buzzer
                            Beep(buzzer_freq, buzzer_duration);
                            break;
                    }
                    break;
                }

                case 0xF1: { // in
                    uint32_t port = regs[reg_b];
                    uint32_t input_data = 0;

                    switch(port) {
                        case 0x01: // Keyboard
                            if (!key_buffer.empty()) {
                                input_data = key_buffer.front();
                                key_buffer.pop_front();
                            } else {
                                input_data = 0;
                            }
                            break;
                        case 0x02: // Mouse X
                            if (shared_memory) input_data = shared_memory->mouse_x;
                            break;
                        case 0x03: // Mouse Y
                            if (shared_memory) input_data = shared_memory->mouse_y;
                            break;
                        case 0x04: // Mouse Button
                            if (shared_memory) input_data = shared_memory->mouse_btn;
                            break;
                        case 0xFF: // System ID
                            input_data = 0x26301;
                            break;
                    }

                    regs[reg_a] = input_data;
                    break;
                }
        }

    if (!jumped) {
        regs[15] += 8;
    }
}