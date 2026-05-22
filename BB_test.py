import pygame
import random
import sys

pygame.init()

# ======================
# 설정
# ======================
WIDTH, HEIGHT = 400, 520
GRID_SIZE = 8
CELL_SIZE = 40
MARGIN = 5

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Blast Clone")

# 색상
BG_COLOR = (30, 30, 30)
GRID_COLOR = (60, 60, 60)
BLOCK_COLORS = [
    (0, 200, 255),
    (255, 100, 100),
    (100, 255, 100),
    (255, 200, 0)
]

# 보드
board = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]

# 블록 모양
blocks = [
    [[1,1],[1,1]],
    [[1,1,1]],
    [[1],[1],[1]],
    [[1,0],[1,1]],
    [[1,1,0],[0,1,1]]
]

# ======================
# 상태 변수
# ======================
current_blocks = []
block_colors = []
selected_block_index = None

# ======================
# 함수들
# ======================
def generate_blocks():
    return [random.choice(blocks) for _ in range(3)]

def generate_colors():
    return [random.choice(BLOCK_COLORS) for _ in range(3)]

def draw_board():
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            x = j * (CELL_SIZE + MARGIN)
            y = i * (CELL_SIZE + MARGIN)

            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

            if board[i][j]:
                pygame.draw.rect(screen, board[i][j], rect)
            else:
                pygame.draw.rect(screen, GRID_COLOR, rect)

def draw_blocks():
    for idx, block in enumerate(current_blocks):
        if block is None:
            continue

        offset_x = 20 + idx * 120
        offset_y = 360
        color = block_colors[idx]

        for i in range(len(block)):
            for j in range(len(block[0])):
                if block[i][j]:
                    rect = pygame.Rect(
                        offset_x + j*20,
                        offset_y + i*20,
                        20, 20
                    )
                    pygame.draw.rect(screen, color, rect)

def select_block(mx, my):
    global selected_block_index

    for idx in range(3):
        bx = 20 + idx * 120
        by = 360

        if bx <= mx <= bx+80 and by <= my <= by+80:
            if current_blocks[idx] is not None:
                selected_block_index = idx

def can_place(block, x, y):
    for i in range(len(block)):
        for j in range(len(block[0])):
            if block[i][j]:
                if x+i >= GRID_SIZE or y+j >= GRID_SIZE:
                    return False
                if board[x+i][y+j]:
                    return False
    return True

def place_block(block, color, x, y):
    for i in range(len(block)):
        for j in range(len(block[0])):
            if block[i][j]:
                board[x+i][y+j] = color

def clear_lines():
    global board

    # 가로
    for i in range(GRID_SIZE):
        if all(board[i][j] != 0 for j in range(GRID_SIZE)):
            for j in range(GRID_SIZE):
                board[i][j] = 0

    # 세로
    for j in range(GRID_SIZE):
        if all(board[i][j] != 0 for i in range(GRID_SIZE)):
            for i in range(GRID_SIZE):
                board[i][j] = 0

def has_valid_move():
    for block in current_blocks:
        if block is None:
            continue
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if can_place(block, i, j):
                    return True
    return False

# ======================
# 초기화
# ======================
current_blocks = generate_blocks()
block_colors = generate_colors()

# ======================
# 메인 루프
# ======================
while True:
    screen.fill(BG_COLOR)

    draw_board()
    draw_blocks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()

            # 아래 블록 선택
            if my > 350:
                select_block(mx, my)

            else:
                grid_x = my // (CELL_SIZE + MARGIN)
                grid_y = mx // (CELL_SIZE + MARGIN)

                if selected_block_index is not None:
                    block = current_blocks[selected_block_index]
                    color = block_colors[selected_block_index]

                    if can_place(block, grid_x, grid_y):
                        place_block(block, color, grid_x, grid_y)
                        clear_lines()

                        current_blocks[selected_block_index] = None
                        selected_block_index = None

                        # 3개 다 쓰면 새로 생성
                        if all(b is None for b in current_blocks):
                            current_blocks = generate_blocks()
                            block_colors = generate_colors()

                        # 게임오버 체크
                        if not has_valid_move():
                            print("게임 오버!")
                            pygame.quit()
                            sys.exit()

    pygame.display.flip()