import argparse
import random
import sys
import time

import pygame


CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
WINDOW_WIDTH = GRID_WIDTH * CELL_SIZE
WINDOW_HEIGHT = GRID_HEIGHT * CELL_SIZE
FPS = 12

BACKGROUND = (18, 18, 24)
SNAKE_HEAD = (88, 214, 141)
SNAKE_BODY = (52, 170, 110)
FOOD_COLOR = (246, 91, 105)
TEXT_COLOR = (235, 235, 235)
GRID_COLOR = (28, 28, 34)


def spawn_food(snake_cells):
    free_cells = [
        (x, y)
        for x in range(GRID_WIDTH)
        for y in range(GRID_HEIGHT)
        if (x, y) not in snake_cells
    ]
    if not free_cells:
        return None
    return random.choice(free_cells)


def draw_grid(surface):
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))


def draw_snake(surface, snake_cells):
    for index, (x, y) in enumerate(snake_cells):
        color = SNAKE_HEAD if index == 0 else SNAKE_BODY
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(surface, color, rect)


def draw_food(surface, food_cell):
    if food_cell is None:
        return
    x, y = food_cell
    rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(surface, FOOD_COLOR, rect)


def draw_text(surface, font, text, position):
    rendered = font.render(text, True, TEXT_COLOR)
    surface.blit(rendered, position)


def main():
    parser = argparse.ArgumentParser(description="Snake-style game using pygame.")
    parser.add_argument(
        "--agent-timeout",
        action="store_true",
        help="Exit automatically after 5 seconds (agent testing).",
    )
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_caption("Snake - WASD")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20)

    snake = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
    direction = (1, 0)
    pending_direction = direction
    food = spawn_food(snake)
    score = 0
    game_over = False

    start_time = time.perf_counter()

    while True:
        dt = clock.tick(FPS)
        _ = dt

        if args.agent_timeout and (time.perf_counter() - start_time) >= 5:
            pygame.quit()
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w:
                    pending_direction = (0, -1)
                elif event.key == pygame.K_s:
                    pending_direction = (0, 1)
                elif event.key == pygame.K_a:
                    pending_direction = (-1, 0)
                elif event.key == pygame.K_d:
                    pending_direction = (1, 0)
                elif event.key == pygame.K_r and game_over:
                    snake = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
                    direction = (1, 0)
                    pending_direction = direction
                    food = spawn_food(snake)
                    score = 0
                    game_over = False
                    start_time = time.perf_counter()

        if not game_over:
            if (pending_direction[0] + direction[0], pending_direction[1] + direction[1]) != (0, 0):
                direction = pending_direction

            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])

            if (
                new_head[0] < 0
                or new_head[0] >= GRID_WIDTH
                or new_head[1] < 0
                or new_head[1] >= GRID_HEIGHT
                or new_head in snake
            ):
                game_over = True
            else:
                snake.insert(0, new_head)
                if food and new_head == food:
                    score += 1
                    food = spawn_food(snake)
                else:
                    snake.pop()

        screen.fill(BACKGROUND)
        draw_grid(screen)
        draw_food(screen, food)
        draw_snake(screen, snake)
        draw_text(screen, font, f"Score: {score}", (10, 10))
        if game_over:
            draw_text(
                screen,
                font,
                "Game Over - Press R to Restart",
                (10, WINDOW_HEIGHT - 30),
            )
        pygame.display.flip()


if __name__ == "__main__":
    main()
