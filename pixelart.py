import pygame
import sys
import colorsys
import os
import copy
from collections import deque
from PIL import Image

# ============================
# 配置（画布大小）
# ============================
CANVAS_W = 16
CANVAS_H = 16
PALETTE_W = 300
BASE_PIXEL_SIZE = 16

pygame.init()

# ============================
# 启动窗口（可拉伸）
# ============================
WINDOW_W = CANVAS_W * BASE_PIXEL_SIZE + PALETTE_W
WINDOW_H = CANVAS_H * BASE_PIXEL_SIZE
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)

pygame.display.set_caption("Pixel Editor")
clock = pygame.time.Clock()

is_fullscreen = False
PIXEL_SIZE = BASE_PIXEL_SIZE

canvas_offset_x = 0
canvas_offset_y = 0
left_area_w = WINDOW_W - PALETTE_W

# 自动吸色开关
EYEDROPPER_AUTO_SWITCH = True
tool_changed_by_eyedropper = False

# ============================
# 自动编号文件名
# ============================
def get_unique_filename(base="pixel_art", ext="png", folder=None):
    if folder is None:
        folder = os.getcwd()

    i = 0
    while True:
        name = f"{base}{'' if i == 0 else f'({i})'}.{ext}"
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            return path
        i += 1

# ============================
# 自动布局
# ============================
def recalc_layout():
    global PIXEL_SIZE, WINDOW_W, WINDOW_H
    global canvas_offset_x, canvas_offset_y, left_area_w

    WINDOW_W, WINDOW_H = screen.get_size()
    left_area_w = max(60, WINDOW_W - PALETTE_W)

    PIXEL_SIZE = min(
        left_area_w // CANVAS_W,
        WINDOW_H // CANVAS_H
    )
    PIXEL_SIZE = max(8, PIXEL_SIZE)

    canvas_total_w = CANVAS_W * PIXEL_SIZE
    canvas_total_h = CANVAS_H * PIXEL_SIZE

    canvas_offset_x = (left_area_w - canvas_total_w) // 2
    canvas_offset_y = (WINDOW_H - canvas_total_h) // 2

recalc_layout()

# ============================
# 全屏切换
# ============================
def enter_fullscreen():
    global screen, is_fullscreen
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    is_fullscreen = True
    recalc_layout()
    print("enter fullscreen")

def exit_fullscreen():
    global screen, is_fullscreen
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
    is_fullscreen = False
    recalc_layout()
    print("exit fullscreen")

# ============================
# 画布数据
# ============================
canvas = [[None for _ in range(CANVAS_H)] for _ in range(CANVAS_W)]

# ============================
# Undo / Redo
# ============================
undo_stack = []
redo_stack = []

def get_downloads_folder():
    return os.path.join(os.path.expanduser("~"), "Downloads")

def push_undo():
    undo_stack.append(copy.deepcopy(canvas))
    redo_stack.clear()

def undo():
    global canvas
    if undo_stack:
        redo_stack.append(copy.deepcopy(canvas))
        canvas = undo_stack.pop()

def redo():
    global canvas
    if redo_stack:
        undo_stack.append(copy.deepcopy(canvas))
        canvas = redo_stack.pop()

# ============================
# 工具定义
# ============================
TOOL_BRUSH = 0
TOOL_ERASER = 1
TOOL_EYEDROPPER = 2
TOOL_FILL = 3
TOOL_AUTOSWITCH = 4  # 只是给 AS 按钮用

current_tool = TOOL_BRUSH
tool_buttons = []
button_size = 60
button_gap = 20

# ============================
# 当前颜色
# ============================
current_color = (255, 0, 0)
h, s, v = 0, 1, 1

# ============================
# 保存 PNG（到 Downloads）
# ============================
def save_png(scale=16):
    downloads = get_downloads_folder()
    os.makedirs(downloads, exist_ok=True)

    filename = get_unique_filename(
        base="pixel_art",
        ext="png",
        folder=downloads
    )

    img = Image.new("RGBA", (CANVAS_W * scale, CANVAS_H * scale))
    px = img.load()

    for x in range(CANVAS_W):
        for y in range(CANVAS_H):
            color = canvas[x][y] or (0, 0, 0, 0)
            for dx in range(scale):
                for dy in range(scale):
                    px[x * scale + dx, y * scale + dy] = color

    img.save(filename)
    print("Saved to Downloads:", filename)

# ============================
# HSV
# ============================
def hsv_to_rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

def rgb_to_hsv(r, g, b):
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

# ============================
# Flood Fill
# ============================
def flood_fill(x, y, target_color, new_color):
    if target_color == new_color:
        return

    q = deque([(x, y)])
    visited = set()

    while q:
        cx, cy = q.popleft()
        if (cx, cy) in visited:
            continue
        visited.add((cx, cy))

        if not (0 <= cx < CANVAS_W and 0 <= cy < CANVAS_H):
            continue

        if canvas[cx][cy] != target_color:
            continue

        canvas[cx][cy] = new_color

        q.append((cx + 1, cy))
        q.append((cx - 1, cy))
        q.append((cx, cy + 1))
        q.append((cx, cy - 1))

# ============================
# 工具按钮
# ============================
def draw_tool_buttons():
    global tool_buttons
    tool_buttons = []

    px = left_area_w + 20
    start_y = 340
    labels = ["B", "E", "I", "F", "AS"]

    for i, label in enumerate(labels):
        x = px
        y = start_y + i * (button_size + button_gap)
        rect = pygame.Rect(x, y, button_size, button_size)

        if label == "AS":
            color = (255, 170, 170) if EYEDROPPER_AUTO_SWITCH else (230, 230, 230)
        else:
            idx = [TOOL_BRUSH, TOOL_ERASER, TOOL_EYEDROPPER, TOOL_FILL][i]
            color = (255, 230, 140) if idx == current_tool else (230, 230, 230)

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 3)

        font = pygame.font.SysFont(None, 28 if label == "AS" else 40)
        tx = font.render(label, True, (0, 0, 0))
        screen.blit(tx, (x + 10, y + 12))

        tool_buttons.append((rect, label))

# ============================
# 调色盘
# ============================
def draw_color_picker():
    px = left_area_w + 20

    # Hue
    for y in range(200):
        pygame.draw.rect(screen, hsv_to_rgb(y / 200, 1, 1), (px, 20 + y, 50, 1))
    pygame.draw.rect(screen, (255, 255, 255), (px - 2, 20 + int(h * 200) - 2, 54, 4), 2)

    # SV
    sv_x = px + 70
    sv_y = 20
    for sx in range(200):
        for sy in range(200):
            screen.set_at((sv_x + sx, sv_y + sy), hsv_to_rgb(h, sx / 200, 1 - sy / 200))

    pygame.draw.circle(
        screen,
        (255, 255, 255),
        (sv_x + int(s * 200), sv_y + int((1 - v) * 200)),
        8,
        3
    )

    pygame.draw.rect(screen, current_color, (sv_x, 240, 200, 80))
    pygame.draw.rect(screen, (0, 0, 0), (sv_x, 240, 200, 80), 3)

def update_color_from_mouse(mx, my):
    global h, s, v, current_color

    px = left_area_w + 20
    sv_x = px + 70
    sv_y = 20

    if drag_hue:
        h = max(0, min(1, (my - 20) / 200))
        current_color = hsv_to_rgb(h, s, v)

    if drag_sv:
        s = max(0, min(1, (mx - sv_x) / 200))
        v = max(0, min(1, 1 - (my - sv_y) / 200))
        current_color = hsv_to_rgb(h, s, v)

# ============================
# 自定义画布尺寸（两个输入框 + ✖，点哪个激活哪个）
# ============================
canvas_input_active = False
canvas_input_w = ""
canvas_input_h = ""
canvas_input_focus = None  # "w" / "h" / None
font_small_ui = pygame.font.SysFont(None, 24)

def set_canvas_size(w, h):
    global CANVAS_W, CANVAS_H, canvas
    global undo_stack, redo_stack

    w = max(1, min(128, w))
    h = max(1, min(128, h))

    CANVAS_W = w
    CANVAS_H = h
    canvas = [[None for _ in range(CANVAS_H)] for _ in range(CANVAS_W)]

    undo_stack.clear()
    redo_stack.clear()
    recalc_layout()
    print(f"Canvas resized to {w}x{h}")

def get_custom_size_rects():
    _, wh = screen.get_size()
    btn = pygame.Rect(left_area_w + 20, wh - 90, 200, 36)   # 激活条
    box_y = btn.y - 44
    rect_w = pygame.Rect(btn.x, box_y, 64, 32)
    rect_h = pygame.Rect(btn.x + 64 + 12 + 20, box_y, 64, 32)
    return btn, rect_w, rect_h

def draw_custom_size_ui():
    btn, rect_w, rect_h = get_custom_size_rects()

    # 激活条
    pygame.draw.rect(screen, (200, 220, 255), btn)
    pygame.draw.rect(screen, (0, 0, 0), btn, 2)
    screen.blit(
        font_small_ui.render("Canvas Size", True, (0, 0, 0)),
        (btn.x + 38, btn.y + 8)
    )

    if not canvas_input_active:
        return

    # 左：宽
    pygame.draw.rect(
        screen,
        (255, 255, 255) if canvas_input_focus == "w" else (235, 235, 235),
        rect_w
    )
    pygame.draw.rect(screen, (0, 0, 0), rect_w, 2)

    # 中间 ✖
    cross = font_small_ui.render("✖", True, (0, 0, 0))
    screen.blit(cross, (rect_w.right + 12, rect_w.y + 4))

    # 右：高
    pygame.draw.rect(
        screen,
        (255, 255, 255) if canvas_input_focus == "h" else (235, 235, 235),
        rect_h
    )
    pygame.draw.rect(screen, (0, 0, 0), rect_h, 2)

    # 文本
    screen.blit(font_small_ui.render(canvas_input_w, True, (0, 0, 0)),
                (rect_w.x + 8, rect_w.y + 6))
    screen.blit(font_small_ui.render(canvas_input_h, True, (0, 0, 0)),
                (rect_h.x + 8, rect_h.y + 6))

# ============================
# 主循环
# ============================
drag_hue = False
drag_sv = False
drawing_left = False
drawing_right = False

while True:
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            recalc_layout()

        if event.type == pygame.KEYDOWN:
            # ===== Custom Size 键盘输入（优先）=====
            if canvas_input_active:
                if event.key == pygame.K_RETURN:
                    try:
                        if canvas_input_w and canvas_input_h:
                            w = int(canvas_input_w)
                            h2 = int(canvas_input_h)
                            set_canvas_size(w, h2)
                    except:
                        print("Invalid canvas size")
                    canvas_input_active = False
                    canvas_input_focus = None

                elif event.key == pygame.K_ESCAPE:
                    canvas_input_active = False
                    canvas_input_focus = None

                elif event.key == pygame.K_BACKSPACE:
                    if canvas_input_focus == "w":
                        canvas_input_w = canvas_input_w[:-1]
                    elif canvas_input_focus == "h":
                        canvas_input_h = canvas_input_h[:-1]

                else:
                    if event.unicode.isdigit():
                        if canvas_input_focus == "w" and len(canvas_input_w) < 3:
                            canvas_input_w += event.unicode
                        elif canvas_input_focus == "h" and len(canvas_input_h) < 3:
                            canvas_input_h += event.unicode

                continue

            # ===== 你的原快捷键 =====
            if event.key == pygame.K_F11:
                exit_fullscreen() if is_fullscreen else enter_fullscreen()
            if event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                undo()
            if event.key == pygame.K_y and pygame.key.get_mods() & pygame.KMOD_CTRL:
                redo()
            if event.key == pygame.K_s:
                save_png()

        # ============================
        # 鼠标按下
        # ============================
        if event.type == pygame.MOUSEBUTTONDOWN:

            # ===== Custom Size 鼠标交互（点左/右分别激活）=====
            if event.button == 1:
                btn, rect_w, rect_h = get_custom_size_rects()

                # 点激活条 → 进入输入模式
                if btn.collidepoint(mx, my):
                    canvas_input_active = True
                    canvas_input_w = str(CANVAS_W)
                    canvas_input_h = str(CANVAS_H)
                    canvas_input_focus = None
                    continue

                # 已激活时，点哪个框就编辑哪个
                if canvas_input_active:
                    if rect_w.collidepoint(mx, my):
                        canvas_input_focus = "w"
                        continue
                    if rect_h.collidepoint(mx, my):
                        canvas_input_focus = "h"
                        continue

            # 中键吸色（自动切回 brush 可开关）
            if event.button == 2:
                tool_changed_by_eyedropper = True
                if (canvas_offset_x <= mx < canvas_offset_x + CANVAS_W * PIXEL_SIZE and
                    canvas_offset_y <= my < canvas_offset_y + CANVAS_H * PIXEL_SIZE):
                    gx = (mx - canvas_offset_x) // PIXEL_SIZE
                    gy = (my - canvas_offset_y) // PIXEL_SIZE
                    px_color = canvas[gx][gy]
                    if px_color:
                        current_color = px_color
                        h, s, v = rgb_to_hsv(*px_color)
                        current_tool = TOOL_BRUSH if EYEDROPPER_AUTO_SWITCH else TOOL_EYEDROPPER

            # 工具按钮（不能覆盖中键）
            if not tool_changed_by_eyedropper:
                for rect, label in tool_buttons:
                    if rect.collidepoint(mx, my):
                        if label == "AS":
                            EYEDROPPER_AUTO_SWITCH = not EYEDROPPER_AUTO_SWITCH
                            break
                        if label == "B": current_tool = TOOL_BRUSH
                        if label == "E": current_tool = TOOL_ERASER
                        if label == "I": current_tool = TOOL_EYEDROPPER
                        if label == "F": current_tool = TOOL_FILL
                        break

            tool_changed_by_eyedropper = False

            # 左键绘图开始
            if event.button == 1:
                if (canvas_offset_x <= mx < canvas_offset_x + CANVAS_W * PIXEL_SIZE and
                    canvas_offset_y <= my < canvas_offset_y + CANVAS_H * PIXEL_SIZE):
                    drawing_left = True
                    push_undo()

            # 右键擦除开始
            if event.button == 3:
                if (canvas_offset_x <= mx < canvas_offset_x + CANVAS_W * PIXEL_SIZE and
                    canvas_offset_y <= my < canvas_offset_y + CANVAS_H * PIXEL_SIZE):
                    drawing_right = True
                    push_undo()

            # 调色盘拖拽
            px = left_area_w + 20
            sv_x = px + 70

            if event.button == 1:
                if px <= mx <= px + 50 and 20 <= my <= 220:
                    drag_hue = True
                elif sv_x <= mx <= sv_x + 200 and 20 <= my <= 220:
                    drag_sv = True

        # 松开按钮
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                drawing_left = False
                drag_hue = drag_sv = False
            if event.button == 3:
                drawing_right = False

    # 拖拽调色盘
    if drag_hue or drag_sv:
        update_color_from_mouse(mx, my)

    # ============================
    # 绘制画布
    # ============================
    screen.fill((40, 40, 40))

    for x in range(CANVAS_W):
        for y in range(CANVAS_H):
            col = (190, 190, 190) if (x + y) % 2 == 0 else (220, 220, 220)
            pygame.draw.rect(
                screen,
                col,
                (canvas_offset_x + x * PIXEL_SIZE,
                 canvas_offset_y + y * PIXEL_SIZE,
                 PIXEL_SIZE, PIXEL_SIZE)
            )

    # 左键绘制
    if drawing_left:
        if (canvas_offset_x <= mx < canvas_offset_x + CANVAS_W * PIXEL_SIZE and
            canvas_offset_y <= my < canvas_offset_y + CANVAS_H * PIXEL_SIZE):
            gx = (mx - canvas_offset_x) // PIXEL_SIZE
            gy = (my - canvas_offset_y) // PIXEL_SIZE

            if current_tool == TOOL_BRUSH:
                canvas[gx][gy] = current_color
            elif current_tool == TOOL_ERASER:
                canvas[gx][gy] = None
            elif current_tool == TOOL_EYEDROPPER:
                px_color = canvas[gx][gy]
                if px_color:
                    current_color = px_color
                    h, s, v = rgb_to_hsv(*px_color)
            elif current_tool == TOOL_FILL:
                # （避免一次点 fill 产生两次 undo：这里不再 push_undo）
                flood_fill(gx, gy, canvas[gx][gy], current_color)
                drawing_left = False

    # 右键擦除
    if drawing_right:
        if (canvas_offset_x <= mx < canvas_offset_x + CANVAS_W * PIXEL_SIZE and
            canvas_offset_y <= my < canvas_offset_y + CANVAS_H * PIXEL_SIZE):
            gx = (mx - canvas_offset_x) // PIXEL_SIZE
            gy = (my - canvas_offset_y) // PIXEL_SIZE
            canvas[gx][gy] = None

    # 绘制像素
    for x in range(CANVAS_W):
        for y in range(CANVAS_H):
            col = canvas[x][y]
            if col:
                pygame.draw.rect(
                    screen,
                    col,
                    (canvas_offset_x + x * PIXEL_SIZE,
                     canvas_offset_y + y * PIXEL_SIZE,
                     PIXEL_SIZE, PIXEL_SIZE)
                )

    # UI
    draw_color_picker()
    draw_tool_buttons()
    draw_custom_size_ui()

    pygame.display.flip()
    clock.tick(60)
