import pygame
import sys

# Konfiguration
GRID_SIZE = 8
PIXEL_SIZE = 50  # Größe eines Pixels in Pixeln
WIDTH = GRID_SIZE * PIXEL_SIZE
HEIGHT = GRID_SIZE * PIXEL_SIZE
BACKGROUND_COLOR = (30, 30, 30)
GRID_COLOR = (50, 50, 50)
COLOR_ON = (255, 255, 255)  # Weiß für AN
COLOR_OFF = (0, 0, 0)       # Schwarz für AUS

# Initialisierung
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Kiwi Font Editor - Drücke 'P' zum Ausgeben")
clock = pygame.time.Clock()

# Internes Grid (False = Aus, True = An)
grid = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

def print_font_array():
    """Generiert das font_array im geforderten Format."""
    values = []
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if grid[y][x]:
                values.append("0xff")
            else:
                values.append("0x00")
    
    # Formatierung: Kommas und Leerzeichen
    output = ", ".join(values)
    print("\n--- Font Array für deinen Assembler ---")
    print(output)
    print("----------------------------------------\n")

# Main Loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Pixel anklicken
            x, y = pygame.mouse.get_pos()
            grid_x = x // PIXEL_SIZE
            grid_y = y // PIXEL_SIZE
            grid[grid_y][grid_x] = not grid[grid_y][grid_x]
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                print_font_array()

    # Zeichnen
    screen.fill(BACKGROUND_COLOR)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            rect = pygame.Rect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE)
            color = COLOR_ON if grid[y][x] else COLOR_OFF
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1) # Grid-Linien

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()