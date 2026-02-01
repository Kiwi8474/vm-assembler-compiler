import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import sys
import time

DISK = "disk.bin"
BIOS = bytes([
    0x20, 0x00, 0x01,
    0x2C, 0x10, 0x00,
    0xC1, 0x00, 0x00,
    0x10, 0xF0, 0x00
])
VGA_START = 0x8000
VGA_END = 0x87CF

regs = [0] * 16

memory = bytearray(65536)

# ===============================================================================
# Memory Map
# ===============================================================================
# 0x0000 - 0x01FF : BIOS (512 Bytes)                 - Hardkodiertes ROM-Programm
# 0x0200 - 0x03FF : Boot Sektor (512 Bytes)          - Sektor 0 der Disk
# 0x0400 - 0x7FFF : Freier RAM (31 KiB)              - Kernel & Programme
# 0x8000 - 0x87CF : VRAM (2000 Bytes)                - Grafikspeicher
# 0x87D0 - 0xABFF : Low-RAM (9264 Bytes / ~9.05 KiB)
# 0xAC00 - 0xAFFF : Stack (1 KiB)                    - Platz für 512 Words
# 0xB000 - 0xFFFE : High-RAM (20478 Bytes / ~20 KiB)
# 0xFFFF          : MMIO Port (1 Byte)               - Tastaturport
# ===============================================================================

with open(DISK, "rb") as f:
    disk_content = bytearray(f.read())

def dump():
    for i, reg in enumerate(regs):
        print(f"R{i}: {hex(reg)}")
    print(f"0xFFFF: {hex(memory[0xFFFF])}")

def mov(reg_a, reg_b, reg_c):
    regs[reg_a] = regs[reg_b]
    if reg_a == 15:
        return True
    return False

def movi(reg_a, imm):
    regs[reg_a] = imm

    if reg_a == 15:
        return True
    return False

def add(reg_a, reg_b, reg_c):
    regs[reg_a] += regs[reg_b]

def sub(reg_a, reg_b, reg_c):
    regs[reg_a] -= regs[reg_b]

def mul(reg_a, reg_b, reg_c):
    regs[reg_a] *= regs[reg_b]

def div(reg_a, reg_b, reg_c):
    if regs[reg_b] != 0:
        regs[reg_a] //= regs[reg_b]
    else:
        print("Zero Division. Shutting down.")
        dump()
        sys.exit(1)

def out(reg_a, reg_b, reg_c):
    port = regs[reg_a]
    data = regs[reg_b]

    if port == 0x1:
        print(chr(data), end='', flush=True)
    elif port == 0x2:
        print(f"{data}/{hex(data)}", end='', flush=True)

def je(reg_a, reg_b, reg_c):
    if regs[reg_a] == regs[reg_b]:
        regs[15] = regs[reg_c]
        return True
    return False

def jne(reg_a, reg_b, reg_c):
    if regs[reg_a] != regs[reg_b]:
        regs[15] = regs[reg_c]
        return True
    return False

def peek(reg_a, reg_b, reg_c):
    addr = regs[reg_b]
    mode = regs[reg_c]

    if mode == 1:
        regs[reg_a] = memory[addr]
    else:
        high_byte = memory[addr]
        low_byte = memory[addr + 1]
        regs[reg_a] = (high_byte << 8) | low_byte

def poke(reg_a, reg_b, reg_c):
    val = regs[reg_a]
    addr = regs[reg_b]
    mode = regs[reg_c]

    if mode == 1:
        memory[addr] = val & 0xFF
    else:
        memory[addr] = (val >> 8) & 0xFF
        memory[addr + 1] = val & 0xFF

def load(reg_a, reg_b, reg_c):
    sector = regs[reg_a]
    start_addr = regs[reg_b]

    disk_start = sector * 512
    chunk = disk_content[disk_start : disk_start + 512]

    if len(chunk) < 512:
        chunk += b'\x00' * (512 - len(chunk))

    memory[start_addr : start_addr + 512] = chunk

def save(reg_a, reg_b, reg_c):
    start_addr = regs[reg_b]
    disk_start = reg_a * 512

    if start_addr + 512 <= 65536:
        disk_content[disk_start : disk_start + 512] = memory[start_addr : start_addr + 512]
    else:
        first_part_size = 65536 - start_addr
        second_part_size = 512 - first_part_size
        disk_content[disk_start : disk_start + first_part_size] = memory[start_addr:]
        disk_content[disk_start + first_part_size : disk_start + 512] = memory[:second_part_size]

def pop(reg_a, reg_b, reg_c):
    high_byte = memory[regs[14]]
    low_byte = memory[regs[14] + 1]
    regs[reg_a] = (high_byte << 8) | low_byte
    regs[14] += 2
    return reg_a == 15

def push(reg_a, reg_b, reg_c):
    high_byte = (regs[reg_a] >> 8) & 0xFF
    low_byte = regs[reg_a] & 0xFF

    regs[14] -= 2
    memory[regs[14]] = high_byte
    memory[regs[14] + 1] = low_byte
    return False

isa = {
    0x1: mov,
    0x2: movi,
    0x3: add,
    0x4: sub,
    0x5: mul,
    0x6: div,
    0x7: out,
    0x8: je,
    0x9: jne,
    0xA: peek,
    0xB: poke,
    0xC: load,
    0xD: save,
    0xE: pop,
    0xF: push
}

last_vram_state = bytearray(2000)
char_cache = {}

def update_screen(screen, memory, vga_font):
    global last_vram_state
    vram_data = memory[VGA_START:VGA_END+1]
    
    for i in range(2000):
        char_code = vram_data[i]

        if char_code != last_vram_state[i]:
            last_vram_state[i] = char_code
            
            x = (i % 80) * 10
            y = (i // 80) * 16

            pygame.draw.rect(screen, (0, 0, 0), (x, y, 10, 16))
            
            if char_code in char_cache:
                screen.blit(char_cache[char_code], (x, y))

def fetch():
    pc_val = regs[15]
    b1 = memory[pc_val]
    b2 = memory[pc_val + 1]
    b3 = memory[pc_val + 2]

    return b1, b2, b3

def decode(b1, b2, b3):
    opcode = (b1 >> 4) & 0x0F
    reg_a  = b1 & 0x0F
    reg_b  = (b2 >> 4) & 0x0F
    reg_c  = b2 & 0x0F
    imm    = (b2 << 8) | b3

    return opcode, reg_a, reg_b, reg_c, imm

def execute(opcode, reg_a, reg_b, reg_c, imm):
    if opcode == 0:
        regs[15] += 1
        return

    if opcode not in isa:
        dump()
        print(f"Unknown opcode {hex(opcode)}. Shutting down.")
        sys.exit(1)

    jumped = False
    if opcode in [0x2]:
        jumped = isa[opcode](reg_a, imm)
    else:
        jumped = isa[opcode](reg_a, reg_b, reg_c)

    if not jumped: regs[15] += 3

def cycle():
    execute(*decode(*fetch()))

def power(screen, clock, vga_font):
    for i, byte in enumerate(BIOS):
        memory[i] = byte

    for i in range(16):
        regs[i] = 0

    cycles = 0
    last_time = time.time()
    ips = 0
    running = True
    while running:
        current_time = time.time()
        if current_time - last_time >= 1.0:
            ips = cycles
            cycles = 0
            last_time = current_time
            if ips / 1000 >= 1000:
                pygame.display.set_caption(f"VM | {ips / 1000000:.2f} MHz")
            elif ips / 1000 >= 1:
                pygame.display.set_caption(f"VM | {ips / 1000:.2f} kHz")
            else:
                pygame.display.set_caption(f"VM | {ips} Hz")

        if cycles % 5000 == 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    dump()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if len(event.unicode) > 0:
                        memory[0xFFFF] = ord(event.unicode)
                
                if event.type == pygame.KEYUP:
                    memory[0xFFFF] = 0

            update_screen(screen, memory, vga_font)
            pygame.display.flip()

        if regs[15] <= 0xFFFF - 3:
            cycle()
            cycles += 1
        else:
                return False, "PC out of bounds. Shutting Down."

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    clock = pygame.time.Clock()
    vga_font = pygame.font.SysFont("Courier New", 16)
    for i in range(32, 127):
        char_cache[i] = vga_font.render(chr(i), True, (0, 255, 0))

    try:
        reboot, msg = power(screen, clock, vga_font)
        if reboot:
            dump()
            power(screen, clock, vga_font)
        print(msg)
    except KeyboardInterrupt:
        pass

    dump()