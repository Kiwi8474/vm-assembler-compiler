import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import mmap
import struct
import pygame

SHM_SIZE = 4013
SHM_NAME = "Local\\MX-26201_VM_SharedMemory"

COLORS = [
    (0,0,0), (0,0,170), (0,170,0), (0,170,170),
    (170,0,0), (170,0,170), (170,85,0), (170,170,170),
    (85,85,85), (85,85,255), (85,255,85), (85,255,255),
    (255,85,85), (255,85,255), (255,255,85), (255,255,255)
]

def start_monitor():
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    vga_font = pygame.font.SysFont("Courier New", 16)
    char_cache = {}
    for c_idx, color in enumerate(COLORS):
        char_cache[c_idx] = {
            i: vga_font.render(chr(i), True, color) 
            for i in range(32, 127)
    }

    shm = None
    
    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        mb = pygame.mouse.get_pressed()

        m_grid_x = max(0, min(79, mx // 10))
        m_grid_y = max(0, min(24, my // 16))
        m_click = 1 if mb[0] else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.unicode:
                    char_code = ord(event.unicode)
                    if char_code < 256:
                        shm.seek(4008) 
                        if shm.read(1) == b'\x00': 
                            shm.seek(4008)
                            shm.write(struct.pack('B', char_code))

        if shm is None:
            try:
                shm = mmap.mmap(-1, SHM_SIZE, tagname=SHM_NAME, access=mmap.ACCESS_WRITE)
            except:
                pygame.display.set_caption("Waiting for VM...")
                pygame.time.wait(500)
                continue

        try:
            shm.seek(0)
            all_data = shm.read(SHM_SIZE)

            vram_data = all_data[:4000]
            ips_data = all_data[4000:4008]
            video_mode = all_data[4012]

            shm.seek(4009)
            shm.write(struct.pack('BBB', m_grid_x, m_grid_y, m_click))

            ips = struct.unpack('d', ips_data)[0]

            if ips >= 1000000:
                caption = f"VM | {ips / 1000000:.2f} MHz"
            elif ips >= 1000:
                caption = f"VM | {ips / 1000:.2f} kHz"
            else:
                caption = f"VM | {int(ips)} Hz"
            pygame.display.set_caption(caption)

            screen.fill((0, 0, 0))

            if video_mode == 0:
                for i in range(2000):
                    char_code = vram_data[i]
                    if 32 <= char_code <= 126:
                        x = (i % 80) * 10
                        y = (i // 80) * 16
                        screen.blit(char_cache[2][char_code], (x, y))
            elif video_mode == 1:
                for i in range(2000):
                    vram_idx = i * 2
                    char_code = vram_data[vram_idx]
                    attr_byte = vram_data[vram_idx + 1]
                    fg_idx = attr_byte & 0x0F
                    bg_idx = (attr_byte >> 4) & 0x0F
                    x = (i % 80) * 10
                    y = (i // 80) * 16
                    if bg_idx != 0:
                        pygame.draw.rect(screen, COLORS[bg_idx], (x, y, 10, 16))
                    if 32 <= char_code <= 126:
                        screen.blit(char_cache[fg_idx][char_code], (x, y))

            pygame.display.flip()
        except Exception as e:
            print(f"Error while reading: {e}")
            shm = None

        pygame.time.wait(16)

    if shm: shm.close()

if __name__ == "__main__":
    start_monitor()