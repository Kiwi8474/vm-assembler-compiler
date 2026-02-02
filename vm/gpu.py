import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import mmap
import struct
import pygame

SHM_SIZE = 2009
SHM_NAME = "Local\\VM_SharedMemory"

def start_monitor():
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    vga_font = pygame.font.SysFont("Courier New", 16)
    char_cache = {i: vga_font.render(chr(i), True, (0, 255, 0)) for i in range(32, 127)}

    shm = None
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.unicode:
                    char_code = ord(event.unicode)
                    if char_code < 256:
                        shm.seek(2008)
                        if shm.read(1) == b'\x00': 
                            shm.seek(2008)
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

            vram_data = all_data[:2000]
            ips_data = all_data[2000:2008]

            ips = struct.unpack('d', ips_data)[0]

            if ips >= 1000000:
                caption = f"VM | {ips / 1000000:.2f} MHz"
            elif ips >= 1000:
                caption = f"VM | {ips / 1000:.2f} kHz"
            else:
                caption = f"VM | {int(ips)} Hz"
            pygame.display.set_caption(caption)

            screen.fill((0, 0, 0))
            for i in range(2000):
                char_code = vram_data[i]
                if 32 <= char_code <= 126:
                    x = (i % 80) * 10
                    y = (i // 80) * 16
                    screen.blit(char_cache[char_code], (x, y))
            
            pygame.display.flip()
        except Exception as e:
            print(f"Error while reading: {e}")
            shm = None

        pygame.time.wait(16)

    if shm: shm.close()

if __name__ == "__main__":
    start_monitor()