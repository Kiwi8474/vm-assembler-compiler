import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import mmap
import struct
import pygame
import numpy as np

SHM_SIZE = 307215
SHM_NAME = "Local\\MX-26301_VM_SharedMemory"

COLORS = [
    (0,0,0), (0,0,170), (0,170,0), (0,170,170),
    (170,0,0), (170,0,170), (170,85,0), (170,170,170),
    (85,85,85), (85,85,255), (85,255,85), (85,255,255),
    (255,85,85), (255,85,255), (255,255,85), (255,255,255)
]

WIDTH, HEIGHT = 640, 480

def start_monitor():
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    pixel_surface = pygame.Surface((WIDTH, HEIGHT), 0, 8)

    palette = []
    for i in range(256):
        r = (i >> 5) * 36
        g = ((i >> 2) & 0x07) * 36
        b = (i & 0x03) * 85
        palette.append((r, g, b))
    pixel_surface.set_palette(palette)

    vga_font = pygame.font.SysFont("Courier New", 16)
    char_cache = {}
    for c_idx, color in enumerate(COLORS):
        char_cache[c_idx] = {
            i: vga_font.render(chr(i), True, color) 
            for i in range(32, 127)
        }

    shm = None
    video_mode = 0
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.unicode and shm:
                    char_code = ord(event.unicode)
                    if char_code < 256:
                        # KEYBOARD BUFFER: 307209
                        shm.seek(307209)
                        if shm.read(1) == b'\x00': 
                            shm.seek(307209)
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

            vram_data = all_data[:307200]
            ips_data = all_data[307200:307208]
            video_mode = all_data[307208]

            mx, my = pygame.mouse.get_pos()
            mb = pygame.mouse.get_pressed()

            target_height = 400
            target_width = int(target_height * (WIDTH / HEIGHT))
            x_offset = (800 - target_width) // 2

            if video_mode == 2:
                rel_x = mx - x_offset
                m_grid_x = max(0, min(WIDTH - 1, int((rel_x / target_width) * WIDTH)))
                m_grid_y = max(0, min(HEIGHT - 1, int((my / target_height) * HEIGHT)))
            else:
                m_grid_x = max(0, min(79, mx // 10))
                m_grid_y = max(0, min(24, my // 16))
            
            m_click = 1 if mb[0] else 0

            shm.seek(307210)
            shm.write(struct.pack('HHB', m_grid_x, m_grid_y, m_click))

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
            elif video_mode == 2:
                frame = np.frombuffer(vram_data, dtype=np.uint8).reshape((HEIGHT, WIDTH)).T
                pygame.surfarray.blit_array(pixel_surface, frame)

                scaled_surface = pygame.transform.scale(pixel_surface, (target_width, target_height))
                screen.blit(scaled_surface, (x_offset, 0))

            pygame.display.flip()
        except Exception as e:
            print(f"Error: {e}")
            shm = None

        pygame.time.wait(16)

    if shm: shm.close()

if __name__ == "__main__":
    start_monitor()